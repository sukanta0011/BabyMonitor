# Baby Sleep Monitoring System — v1

A portfolio project born out of a real need: keeping an eye on a sleeping
baby, from multiple angles, with actual environmental data instead of just
a video feed.

**Not a medical device.** It's an engineering project — real-time CV,
embedded firmware, systems design. See [Known Limitations](#known-limitations)
before reading anything else into what it outputs.

---

## What it does

- Streams video from two ESP32-CAM nodes over WiFi (MJPEG/HTTP, found via mDNS)
- Runs face detection on both feeds and automatically picks whichever camera
  currently has the clearest view of the face, switching when needed
- Reads live temperature, humidity, CO2, and light from a separate ESP32
  sensor node over I2C
- Flags sensor readings that fall outside nursery-appropriate ranges
- Shows all of it in a live Streamlit dashboard

---

## Architecture

```
ESP32-CAM #1 ─┐
              ├─ WiFi/HTTP ─┐
ESP32-CAM #2 ─┘             │
                             ├──▶ Python "brain" (laptop now, Pi later)
ESP32 sensor node ─ HTTP ────┘        │
 (BH1750 + SCD40)                     ├─ CameraStream + SensorStream (threaded)
                                       ├─ MediaPipe face detection
                                       ├─ best-camera selection
                                       └─ Streamlit dashboard
```

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

**mDNS instead of hardcoded IPs.** ESP32 IPs change every reboot (DHCP).
mDNS lets Python just ask for `esp32_cam1.local` and not care what the
current IP is.

**Polling over WebSockets.** Sensor data changes slowly — no need for a
push connection. Also skipped HTTPS on the ESP32s on purpose: a TLS
handshake takes 1-3 seconds on this chip with no hardware crypto, which
isn't worth it on a trusted home network. A reverse proxy on the Pi would
be the right place to add TLS later.

**Threads and locks everywhere, not asyncio.** Every I/O call in this
project is blocking (OpenCV captures, `requests.get`), so threads with
locks made more sense than wrapping everything for asyncio's benefit.
Same producer/consumer pattern repeats for camera frames, sensor data, and
best-camera selection.

**Best-camera selection runs on its own schedule**, not every frame.
Scanning every camera on every dashboard refresh would be wasteful — it
only re-scans all cameras when the current one's confidence drops and
stays down.

---

## Hardware

- 2× ESP32-CAM (AI-Thinker)
- 1× ESP32 sensor node
- BH1750 — light (I2C `0x23`)
- SCD40 — CO2, temperature, humidity (I2C `0x62`)
- BMP280 — turned out to be dead on arrival, confirmed via a raw SPI
  chip-ID read rather than assumed

## Software

- **Firmware:** Arduino/C++, ESPAsyncWebServer, ArduinoJson, ESPmDNS,
  FreeRTOS mutexes, an abstract `Sensor` base class for the I2C drivers
- **Python:** OpenCV, MediaPipe, `requests`/`httpx`, `threading`, Streamlit

---

## Known Limitations

Cut from v1 on purpose, not forgotten:

- **No covered-face detection.** MediaPipe's keypoints are predicted from
  overall face shape, not verified visible — covering the nose and mouth
  doesn't reliably change them. This needs a model trained specifically
  for it, which is genuinely most of what commercial baby monitors are
  selling. No training data, no time for it in v1.
- **No check that the detected face is actually the baby's.** Right now
  any face is treated the same — an adult leaning into frame counts as
  "face detected." Distance-based heuristics don't work once the baby can
  be anywhere in the cot, not just centered. Left as an open problem.
- **No multi-camera fusion** when neither camera has a clean view — that's
  a real multi-view geometry problem, out of scope here.
- **No tests.** Manual testing only, given the timeline.
- **Plain HTTP, no auth** on the ESP32 endpoints. Fine on a home network,
  not fine anywhere else.

---

## What's next (v2 ideas)

- Covered-face / obstruction detection with a trained classifier
- Baby-vs-adult face verification
- Multi-camera view fusion for hard angles
- Using Night-vision camera modules
- Move from laptop to Raspberry Pi — nothing in the code assumes laptop
  specifically, so this should mostly be a config change
- HTTPS via a reverse proxy on the Pi, keeping TLS off the ESP32s
- API key auth on the sensor/camera endpoints

---

## A few bugs worth mentioning

- **RTSP → MJPEG**, diagnosed by watching FFmpeg's transport behavior
  rather than guessing — UDP was silently dropping every video packet
  while the control connection succeeded
- **AP isolation** on a university WiFi network blocked all device-to-device
  traffic while WiFi itself connected fine — took testing on a completely
  different network to rule out a code bug
- **Dead BMP280**, confirmed by reading its SPI chip-ID register directly
  instead of assuming a wiring mistake
- **ESP32 crash from initializing a FreeRTOS mutex before the scheduler was
  ready** — tracked down through the exact assertion in the crash dump
  (`xQueueSemaphoreTake`)