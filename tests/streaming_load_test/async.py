import asyncio
import aiohttp
import time
from tqdm import tqdm

URL = "http://localhost:8000/video"
DURATION = 10


async def simulate_viewer(
        viewer_id: int, counters: list, session: aiohttp.ClientSession):
    start = time.time()
    try:
        async with session.get(
            URL, timeout=aiohttp.ClientTimeout(
                total=DURATION + 5)) as response:
            async for chunk in response.content.iter_chunked(1024):
                if chunk.startswith(b'--frame') or \
                        b'Content-Type: image/jpeg' in chunk:
                    counters[viewer_id] += 1
                if time.time() - start > DURATION:
                    break
    except Exception as e:
        print(f"Viewer {viewer_id} failed: {e}")


async def start_load_test(viewers: int) -> float:
    counters = [0] * viewers
    start_time = time.time()

    connector = aiohttp.TCPConnector(limit=0)  # no artificial connection cap
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            asyncio.create_task(simulate_viewer(i, counters, session))
            for i in range(viewers)
        ]

        with tqdm(
            total=DURATION, desc=f"{viewers} viewer(s)",\
                unit="s") as bar:
            last_elapsed = 0.0
            while not all(t.done() for t in tasks):
                elapsed = min(time.time() - start_time, DURATION)
                bar.update(elapsed - last_elapsed)
                last_elapsed = elapsed
                bar.set_postfix(chunks=sum(counters))
                await asyncio.sleep(0.2)

        await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start_time
    total_chunks = sum(counters)
    avg_fps_per_viewer = (total_chunks / elapsed) / viewers\
        if viewers > 0 else 0
    print(f"  {viewers} viewer(s): {total_chunks} "
          f"total chunks over {elapsed:.1f}s "
          f"(~{avg_fps_per_viewer:.2f} chunks/s per viewer)\n")
    return avg_fps_per_viewer


async def main():
    for v in [1, 100, 500, 1000, 2000, 5000]:
        print(f"----- LOAD TEST: {v} viewer(s) -----")
        await start_load_test(v)


if __name__ == "__main__":
    asyncio.run(main())
