# Development Journey

The reasoning, tradeoffs, and bugs behind [README.md](README.md) — why
things are built the way they are, not just what they do.

---

## Why it's built this way

**Two cameras, not one.** A baby on its side shows a profile a single
camera can't reliably see without physically moving to face it. Two fixed
cameras cover both sides for the cost of a second $8 board — no motors,
nothing that can jam next to a crib. A moving pan-tilt rig was seriously
considered and dropped for this reason.

**ESP32s are dumb, Python is the brain.** The ESP32 can stream video and
read sensors, but it can't run face detection — not enough CPU or RAM. So
each ESP32 does one small job well and a central Python process does the
thinking. Standard IoT split.

**MJPEG over HTTP, not RTSP.** Started with RTSP, spent a long time
debugging a stream that "connected" but delivered zero frames — turned out
the `Micro-RTSP` library only really works over UDP, and UDP drops packets
on WiFi badly enough to break it. MJPEG-over-HTTP is what the ESP32-CAM's
JPEG hardware is built for anyway, and it's actually lighter on the chip
than RTSP would be.

**FastAPI over Streamlit.** Streamlit was the fast prototype, but it runs
each browser tab as its own independent script execution — multiple
simultaneous viewers meant multiple competing infinite loops in the same
process, not a real shared feed. FastAPI with an async generator and a
shared, lock-protected frame buffer serves any number of viewers from one
capture pipeline instead.

**Async for serving, threads for capture.** The MJPEG endpoint is a true
`async def` generator — cheap, many-cheap-connections is exactly what
asyncio is for. Camera and sensor *capture*, on the other hand, calls
blocking C libraries (`cv2.VideoCapture`, `requests.get`) with no
async-native equivalent, so those stay on real OS threads. Async doesn't
remove the need for locks where genuine threads still touch shared
state — it just removes the need for them on the purely async side.

**mDNS instead of hardcoded IPs**, for the ESP32s and, later, for reaching
the Pi itself from a phone — DHCP means IPs change, `.local` names don't.
Hit a real limitation here too: mDNS depends on multicast traffic, which
Docker's bridge network doesn't pass through by default. Solved for the
sensor node by resolving the IP once on the host and injecting it as
config, rather than getting a full in-container Avahi/D-Bus setup working
under time pressure — a deliberate, documented scope cut.

**Postgres before MQTT.** The roadmap called for MQTT pub/sub from the
start, but it was deliberately built the "naive" way first — a background
task polling the sensor stream and writing straight to Postgres — to
actually feel the coupling problem before reaching for a broker. That
experiment made the real gap concrete: anything living *outside* the
FastAPI process (a separate script, a future model-training job) has no
way to get live sensor data except reimplementing HTTP polling from
scratch. MQTT is deferred until a second, genuinely independent consumer
actually needs that decoupling — the naive version is enough for now.

**Auto-discovery and reconnection, not startup-only detection.** Cameras
and the sensor node are checked at startup, but that's a single snapshot —
a device unreachable at boot, or one that drops mid-session, previously
had no path back into the running system. A background task now retries
unreachable devices on an interval and rejoins them once they respond,
using the same consecutive-failure-counting pattern on both the camera
and sensor sides (a single flaky read doesn't trigger it — several in a
row do, to avoid flapping on transient blips).

**Docker for deploy, not just packaging.** Moving to the Raspberry Pi
surfaced a real platform gap — MediaPipe has no published ARM64 Linux
wheel for the version used here. An official from-source build path
exists (compiling MediaPipe via Bazel for aarch64) but proved too slow
and fragile to complete under the deployment timeline. Solved by swapping
the face detector to OpenCV's built-in YuNet model on ARM, while keeping
MediaPipe as an optional, platform-gated dependency (`platform_machine !=
'aarch64'`) so local x86 development can still use it.

---

## Load-testing & concurrency findings

Load-tested the MJPEG fan-out endpoint (`/video`) with simulated concurrent
viewers, iterating through progressively more realistic test-client
designs as each one's own bottleneck was found and fixed:

1. **Threaded sync client, sync server generator** — degradation started
   around 50 viewers. Root cause: `generate_frame` was a blocking sync
   generator, which Starlette runs on a dedicated OS thread per
   connection — overhead scaled directly with viewer count.
2. **Fixed the server**: converted `generate_frame` to a true `async def`
   generator, letting Starlette serve all viewers on one event loop
   instead of one thread each. Stable up to ~500 viewers with the same
   threaded test client — but the *client* itself became the bottleneck
   (memory pressure from hundreds of OS thread stacks, confirmed via swap
   usage in `top`).
3. **Fixed the client to match**: rewrote it using `aiohttp` + `asyncio`.
   Removed the memory bottleneck, exposed a new one — a single Python
   process is limited to one CPU core, and parsing thousands of chunks/sec
   pinned that core before the server was genuinely stressed.
4. **Multi-process client**: split simulated viewers across
   `multiprocessing.cpu_count()` worker processes, each with its own event
   loop. This finally generated enough real parallel load to find the
   server's actual ceiling — `uvicorn` itself (single process, single
   event loop) became the bottleneck, confirmed by CPU pinned on the
   server process rather than any client process.

**Result:** a single-process FastAPI/uvicorn server comfortably serves
1000–2000 concurrent viewers on this hardware, with capture and JPEG
encoding happening once regardless of viewer count. Beyond that, horizontal
scaling via multiple `uvicorn` workers is the next step — deferred, since
it requires moving the shared frame buffer out of in-process `app.state`
into an external store (e.g. Redis) all workers can read, and the current
ceiling already far exceeds this project's realistic usage.

---

## Notable bugs and how they were found

- **RTSP → MJPEG**, diagnosed by watching FFmpeg's transport behavior
  rather than guessing — UDP was silently dropping every video packet
  while the control connection succeeded.
- **AP isolation** on a university WiFi network blocked all
  device-to-device traffic while WiFi itself connected fine — took
  testing on a different network to rule out a code bug.
- **Dead BMP280**, confirmed by reading its SPI chip-ID register directly
  instead of assuming a wiring mistake.
- **ESP32 crash from initializing a FreeRTOS mutex before the scheduler
  was ready** — tracked down through the exact assertion in the crash
  dump (`xQueueSemaphoreTake`).
- **Postgres "database does not exist" loop** — the healthcheck passed
  `-U` without `-d`; `pg_isready` silently defaults the target database to
  match the username when `-d` is omitted.
- **`socket.gaierror` connecting to Postgres from FastAPI** — Docker
  Compose's internal DNS resolves services by name (`db`), not by
  `container_name`; fixed by addressing Postgres as `db`, matching the
  compose service key.
- **Missing shared libraries in the Docker image** (`libxcb`, later
  `libGLESv2`/`libEGL`) — diagnosed efficiently by running `ldd` directly
  against the failing `.so` file inside a container shell, surfacing every
  missing dependency in one pass instead of a rebuild-guess-repeat cycle.
- **MediaPipe has no ARM64 Linux wheel** for the version used here —
  spent real time on an official-but-slow from-source build path before
  switching to OpenCV's built-in YuNet detector for the ARM deployment,
  keeping MediaPipe as a platform-gated optional dependency for x86 dev.
- **Mobile viewport not rendering correctly** — missing `<meta
  name="viewport">` tag meant phones rendered the page at desktop width
  and scaled it, rather than laying it out natively; adding the tag plus
  `-webkit-text-size-adjust: 100%` fixed both the sizing and the
  "have to zoom to read" symptom.