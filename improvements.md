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