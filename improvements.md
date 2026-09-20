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
 
 ---

## Face detection on real-world sleeping poses (V1c investigation)

While testing the deployed system live, the best-camera pipeline froze
displaying a stale "face detected" result during a stretch where the
baby's actual sleeping pose produced no confident detection on any
camera. Rather than guess at a fix, the specific failing frame was pulled
and tested directly against the detector in isolation, ruling hypotheses
in or out one at a time.

**Hypothesis 1 — distance/scale.** The face occupies a small fraction of
the full frame; maybe the detector just needs a tighter, more zoomed-in
view. **Tested**: cropped the frame tightly around just the face and
re-ran detection on the crop alone. Score stayed effectively unchanged
(0.158 cropped vs 0.155 on the equivalent region in the full frame).
**Ruled out** — scale was not the limiting factor.

**Hypothesis 2 — in-plane rotation.** The head initially looked tilted;
maybe correcting rotation would help. **Tested**: on closer inspection
the face in this frame is not meaningfully rolled — rotation doesn't
apply here. (Kept as a real fix for a *different*, genuinely useful case:
when a camera is angled to catch a side-lying baby and the head is tipped
sideways in-frame, rotating the image before detection is a legitimate,
cheap fix — this is not to be confused with the camera seeing the face
from the *side* (yaw), which 2D image rotation cannot correct; that
problem is what the two-camera setup already exists to solve.)

**Hypothesis 3 — image contrast/quality.** The frame looked soft and
washed out; maybe a contrast enhancement pass would help the detector see
more distinct features. **Tested**: applied CLAHE (Contrast Limited
Adaptive Histogram Equalization) on the L channel in LAB color space
(preserves color balance while boosting local contrast) before detection.
Score stayed effectively unchanged (0.157).
**Ruled out** — image quality preprocessing was not the limiting factor.

**Conclusion.** With scale, rotation, and contrast all tested and ruled
out, the remaining explanation is the detection model itself: general-
purpose face detectors (both YuNet and MediaPipe's BlazeFace) are trained
predominantly on adult faces in more conventional orientations, and have
a real, measurable blind spot on infant faces in natural sleeping
poses — partial self-occlusion from position (chin tucked, cheek pressed
into bedding), proportions that differ from adult training data, and
poses uncommon in typical face-detection training sets. No amount of
image preprocessing closes that gap; it requires a detector trained or
fine-tuned on infant-specific data, which is a real ML undertaking (data
collection, labeling, training) rather than a quick fix. This is the same
underlying limitation already named for covered-face detection in
[README.md](README.md#known-limitations) — general-purpose models don't
transfer well to this domain, and it's now been directly confirmed
empirically for plain face detection too, not just assumed.

**Immediate mitigation shipped**: manual per-camera selection
(`/video/{camera_name}`) lets a parent check any raw feed directly,
independent of what the best-camera engine currently shows — a real
workaround for the gap, not a fix for it.

**Deferred to V2/V3**: fine-tuning or sourcing a face detector trained on
infant sleeping poses.

---
 
## Building a standalone MJPEG display client on ESP32-S3, from scratch
 
Wanted a physical, always-on display that shows the live video feed and
sensor data with no phone or laptop involved. This turned into a genuine
embedded-systems build: parsing a live network stream by hand, a custom
fixed-size data structure, real dual-core concurrency, and more than one
race condition found and fixed the hard way.
 
### Parsing MJPEG-over-chunked-HTTP by hand
 
`HTTPClient::getStreamPtr()` hands back a raw, continuously-open
`WiFiClient` — nothing decodes the multipart boundaries or the underlying
HTTP chunked-transfer-encoding for you, unlike `requests`/`aiohttp` on the
Python side, which do this transparently. Built a small state machine:
accumulate incoming bytes into a buffer, search for the `--frame\r\n`
boundary marker, treat everything between two consecutive markers as one
complete JPEG frame.
 
**Bug found via raw byte-dump diagnostics**: chunked-transfer-encoding
prefixes (`1856\r\n`-style hex length headers) sit *between* the boundary
marker and the JPEG payload — invisible on the Python side, since
`requests` strips them automatically, but present and unhandled on the raw
socket read. Confirmed by printing the actual incoming bytes as raw
integers rather than trusting assumptions about the wire format.
 
### Ring buffer, sized against a moving target
 
Built a templated, generic `RingBuffer<T, N>` (fixed-size, FIFO, tested
independently with Catch2 on the host before ever touching hardware) to
hold incoming bytes without unbounded growth. Its correct size turned out
to depend on a fact that wasn't static: JPEG frame size varies
significantly with lighting and scene detail — a dark nighttime frame
compresses far more than a bright, detailed daytime one, confirmed via a
standalone quality/size test script run against the same camera at
different times of day. Sizing the buffer against a single measured frame
size was sizing against a moving target; the real fix was capping the
*source* encoding, not chasing an ever-larger buffer.
 
**Bug found via a from-scratch minimal reproduction**: reading a whole
network burst before ever checking for a complete frame let the ring
buffer's own (correct, working-as-designed) eviction-when-full behavior
silently destroy a still-needed frame's boundary marker before it was
ever searched for — not a race condition, a pure sequencing bug, isolated
and proven with a tiny standalone C++ demo (a hardcoded byte string, no
networking) before touching the real firmware. Fixed by interleaving
read-and-extract, checking for a complete frame after every small chunk
rather than after a whole burst.
 
### Dual-core FreeRTOS, and the races that came with it
 
Split network reading, JPEG decode/display, and sensor polling into three
separate FreeRTOS tasks, confirmed genuinely running on separate physical
cores via `xPortGetCoreID()`. This surfaced real concurrency problems that
single-threaded code never hits:
 
- **Reused `HTTPClient` object, touched from two tasks** — caused a hard
  crash (`assert failed: xQueueSemaphoreTake`) the first time a shared
  client was used for both the continuous video stream and a one-off
  sensor request from a different task. Fixed by giving sensors,
  camera 1, and camera 2 each their own dedicated `HTTPClient`.
- **Same failure resurfaced switching between CAM1 and CAM2** — traced to
  a genuine copy-paste bug (a duplicated `if (mode == CAM1)` guard meaning
  CAM2's connection logic never ran at all) compounding the shared-object
  risk; fixing the condition and keeping the per-camera client split
  resolved it.
- **HTTP keep-alive vs. server-side idle timeout** — sensor polling
  failed with `HTTPC_ERROR_SEND_HEADER_FAILED` on a strict, alternating
  every-other-request pattern; the server was closing the idle
  keep-alive connection between 10-second polls, and the client's default
  connection reuse tried to send on an already-dead socket. Fixed with
  `setReuse(false)`, forcing a fresh connection per request.
- **`xSemaphoreTake` on an uninitialized handle** — the exact same class
  of bug hit twice tonight, once on the sensor mutex and once earlier on
  a different ESP32 firmware months ago: a `SemaphoreHandle_t` used
  before `xSemaphoreCreateMutex()` had actually run.
### Letterboxed scaling, written from scratch, block by block
 
`TJpgDec` only offers fixed power-of-two scale factors — none of which
land cleanly on a 320×480 target from a 640×480 source. Rather than
buffer a full decoded frame (expensive, and reintroduces the moving-
target sizing problem), the scale factor is computed **dynamically per
frame** via `getJpgSize()`, and each small decoded block is scaled and
repositioned individually inside the decoder's own per-block callback —
no full-frame buffer ever held.
 
**Bug found from a visibly regular artifact, not random corruption**: a
repeating grid of thin black lines appeared between blocks. Diagnosed as
independently-rounded position and size calculations per block drifting
apart at every block boundary — not corruption, a systematic rounding
gap. Fixed by deriving each block's destination width/height from the
*difference* between two consecutive rounded boundary positions, rather
than rounding width and position independently — guaranteeing adjacent
blocks' edges always line up exactly.
 
### Lesson, in one line
 
Every one of these bugs was found the same way: reproduce it in
isolation, look at the actual raw data (bytes, timings, core IDs) rather
than assume, and fix the sequencing/ownership problem underneath the
symptom rather than the symptom itself.
 
