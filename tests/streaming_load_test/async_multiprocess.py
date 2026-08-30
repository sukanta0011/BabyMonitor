import asyncio
import aiohttp
import time
import multiprocessing as mp
from tqdm import tqdm

URL = "http://localhost:8000/video"
DURATION = 10
NUM_PROCESSES = mp.cpu_count()


async def simulate_viewer(
        viewer_id: int, counter_slot: list, session: aiohttp.ClientSession):
    start = time.time()
    try:
        async with session.get(
            URL, timeout=aiohttp.ClientTimeout(
                total=DURATION + 5)) as response:
            async for chunk in response.content.iter_chunked(1024):
                if chunk.startswith(b'--frame') or \
                    b'Content-Type: image/jpeg' in chunk:
                        counter_slot[0] += 1
                if time.time() - start > DURATION:
                    break
    except Exception:
        pass


async def run_event_loop(
        viewers_for_this_process: int, result_queue: mp.Queue):
    counters = [[0] for _ in range(viewers_for_this_process)]
    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            asyncio.create_task(simulate_viewer(i, counters[i], session))
            for i in range(viewers_for_this_process)
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    result_queue.put(sum(c[0] for c in counters))


def worker(viewers_for_this_process: int, result_queue: mp.Queue):
    asyncio.run(run_event_loop(viewers_for_this_process, result_queue))


def start_load_test(total_viewers: int) -> float:
    per_process = total_viewers // NUM_PROCESSES
    remainder = total_viewers % NUM_PROCESSES
    splits = [
        per_process + (1 if i < remainder else 0)
        for i in range(NUM_PROCESSES)]

    result_queue:mp.Queue = mp.Queue()
    processes = [
        mp.Process(target=worker, args=(n, result_queue))
        for n in splits if n > 0
    ]

    start_time = time.time()
    for p in processes:
        p.start()

    with tqdm(total=DURATION, desc=f"{total_viewers} viewer(s),\
              {len(processes)} procs", unit="s") as bar:
        last_elapsed = 0.0
        while any(p.is_alive() for p in processes):
            elapsed = min(time.time() - start_time, DURATION + 2)
            bar.update(max(0, elapsed - last_elapsed))
            last_elapsed = elapsed
            time.sleep(0.2)

    for p in processes:
        p.join()

    total_chunks = 0
    while not result_queue.empty():
        total_chunks += result_queue.get()

    elapsed = time.time() - start_time
    avg_fps_per_viewer = (
        total_chunks / elapsed) / total_viewers if total_viewers > 0 else 0
    print(f"  {total_viewers} viewer(s) across {len(processes)} processes: "
          f"{total_chunks} total chunks over {elapsed:.1f}s "
          f"(~{avg_fps_per_viewer:.2f} chunks/s per viewer)\n")
    return avg_fps_per_viewer


if __name__ == "__main__":
    print(f"Using {NUM_PROCESSES} worker processes (CPU count)\n")
    for v in [1000, 2000, 5000, 10000]:
        print(f"----- LOAD TEST: {v} viewer(s) -----")
        start_load_test(v)
