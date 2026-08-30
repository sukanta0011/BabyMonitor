import requests
import threading
import time
from tqdm import tqdm

URL = "http://localhost:8000/video"
DURATION = 10


def simulate_viewer(viewer_id: int, counters: dict, lock: threading.Lock):
    start = time.time()
    try:
        with requests.get(URL, stream=True, timeout=5) as response:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk.startswith(
                    b'--frame') or b'Content-Type: image/jpeg' in chunk:
                    with lock:
                        counters[viewer_id] += 1
                if time.time() - start > DURATION:
                    break
    except Exception as e:
        print(f"Viewer {viewer_id} failed: {e}")


def start_load_test(viewers: int) -> float:
    threads = []
    counters = {i: 0 for i in range(viewers)}
    lock = threading.Lock()

    start_time = time.time()
    for i in range(viewers):
        t = threading.Thread(
            target=simulate_viewer, args=(i, counters, lock), daemon=True)
        threads.append(t)
        t.start()

    with tqdm(total=DURATION, desc=f"{viewers} viewer(s)", unit="s") as bar:
        last_elapsed = 0.0
        while any(t.is_alive() for t in threads):
            elapsed = min(round(time.time() - start_time, 2), DURATION)
            bar.update(elapsed - last_elapsed)
            last_elapsed = elapsed
            with lock:
                total = sum(counters.values())
            bar.set_postfix(chunks=total)
            time.sleep(0.2)

    for t in threads:
        t.join()

    elapsed = round(time.time() - start_time, 2)
    total_chunks = sum(counters.values())
    avg_fps_per_viewer = (
        total_chunks / elapsed) / viewers if viewers > 0 else 0
    print(f"  {viewers} viewer(s): {total_chunks} total chunks over "
          f"{elapsed:.1f}s  (~{avg_fps_per_viewer:.2f} chunks/s per viewer)\n")
    return avg_fps_per_viewer


if __name__ == "__main__":
    for v in [1, 10, 100, 200, 400, 500, 750, 1000]:
        start_load_test(v)
