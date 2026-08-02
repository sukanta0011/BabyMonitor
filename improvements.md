## Load testing & concurrency findings (V1a)
 
Load-tested the MJPEG fan-out endpoint (`/video`) with simulated concurrent
viewers, iterating through three progressively more realistic test-client
designs as each one's own bottleneck was found and fixed:
 
1. **Threaded sync client, sync server generator** — degradation started
   around 50 viewers. Root cause: `generate_frame` was a blocking sync
   generator, which Starlette runs on a dedicated OS thread per connection —
   overhead scaled directly with viewer count.
2. **Fixed the server**: converted `generate_frame` to a true `async def`
   generator (`await asyncio.sleep` instead of `time.sleep`), letting
   Starlette serve all viewers on one event loop instead of one thread each.
   Result: stable throughput up to ~500 viewers with the same threaded test
   client — but the *client* itself was now the bottleneck (memory pressure
   from hundreds of OS thread stacks, confirmed via swap usage in `top`).
3. **Fixed the client to match**: rewrote the load-test client using
   `aiohttp` + `asyncio` (coroutines instead of threads). Removed the
   memory bottleneck, but exposed a new, different one — a single Python
   process is limited to one CPU core, and parsing thousands of chunks/sec
   pinned that core at 100% well before the server was stressed.
4. **Multi-process client**: split simulated viewers across
   `multiprocessing.cpu_count()` worker processes, each running its own
   `asyncio` event loop. This finally generated enough real parallel load
   to find the server's actual ceiling — at which point `uvicorn` itself
   (a single process, single event loop) became the bottleneck, confirmed
   by CPU usage pinned on the server process rather than any client process.
**Result:** a single-process FastAPI/uvicorn server comfortably serves
1000-2000 concurrent viewers on this hardware with the shared-buffer
async fan-out design (capture and JPEG encoding happen once, regardless
of viewer count). Beyond that, the bottleneck is `uvicorn` running as a
single process on one core — the standard next step is horizontal
scaling via multiple `uvicorn` workers, which requires moving the shared
frame buffer out of in-process `app.state` and into an external store
(e.g. Redis) all worker processes can read from, since separate OS
processes don't share memory. Deferred as a deliberate scope cut — the
1000-2000 viewer ceiling already far exceeds this project's realistic
usage (a handful of family members checking a feed), and Redis-backed
multi-worker scaling is a cleaner fit for the V1b/V1c infrastructure work
than a mid-V1a detour.
 