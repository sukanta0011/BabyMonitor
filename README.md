# Baby Sleep Monitoring System — v1

A portfolio project born out of a real need: keeping an eye on a sleeping
baby, from multiple angles, with actual environmental data instead of just
a video feed.

**Not a medical device.** It's an engineering project — real-time CV,
embedded firmware, systems design. See [Known Limitations](#known-limitations).

![](https://github.com/sukanta0011/BabyMonitor/blob/main/screenshots/babymonitor_v1.gif)

For the full story — why things are built this way, bugs hit and how they
were diagnosed, load-testing numbers — see [DEVELOPMENT.md](DEVELOPMENT.md).

---

## What it does

- Streams video from two ESP32-CAM nodes over WiFi (MJPEG/HTTP), with
  automatic best-camera selection based on live face-detection confidence
- Automatically detects and reconnects cameras and the sensor node that
  weren't reachable at startup, or that drop out mid-session
- Reads live temperature, humidity, CO2, and light from a separate ESP32
  sensor node over I2C, and persists every reading to Postgres
- Flags sensor readings that fall outside nursery-appropriate ranges
- Serves a lightweight FastAPI backend + phone-optimized HTML dashboard,
  accessible from any device on the local network — tested with hundreds
  of concurrent viewers with no meaningful degradation
- Runs fully containerized via Docker Compose, deployed and verified on a
  Raspberry Pi 5

---

## Architecture

```
ESP32-CAM #1 ─┐
              ├─ WiFi/HTTP ─┐
ESP32-CAM #2 ─┘             │
                             │
ESP32 sensor node ─ HTTP ────┤
 (BH1750 + SCD40)            │
                             ▼
                  ┌─────────────────────────┐
                  │   FastAPI (Docker, Pi)   │
                  │  ├─ CameraStream(s)      │
                  │  ├─ SensorStream         │
                  │  ├─ auto-discovery loops │
                  │  ├─ face detection       │
                  │  │  (YuNet on ARM /      │
                  │  │   MediaPipe on x86)   │
                  │  ├─ best-camera select   │
                  │  └─ Postgres writer      │
                  └───────────┬─────────────┘
                               │
                    Postgres (Docker)
                               │
                    Phone / laptop browser
                    (HTML dashboard, polling)
```

---

## Hardware

- 2× ESP32-CAM (AI-Thinker)
- 1× ESP32 sensor node
- BH1750 — light (I2C `0x23`)
- SCD40 — CO2, temperature, humidity (I2C `0x62`)
- BMP280 — turned out to be dead on arrival
- Raspberry Pi 5 — production host, headless (Raspberry Pi OS Lite)

## Software

- **Firmware:** Arduino/C++, ESPAsyncWebServer, ArduinoJson, ESPmDNS,
  FreeRTOS mutexes, an abstract `Sensor` base class for the I2C drivers
- **Backend:** FastAPI, async MJPEG fan-out, SQLAlchemy (async) + Postgres,
  OpenCV, YuNet (ARM) / MediaPipe (x86, optional), `requests`, `threading`
  + `asyncio` side by side
- **Frontend:** plain HTML/CSS/JS, phone-first, no framework
- **Deploy:** Docker Compose (FastAPI + Postgres), running on Raspberry Pi 5

---

## Known Limitations

Cut from v1 on purpose, not forgotten:

- **No covered-face detection** — needs a purpose-trained model, out of
  scope for v1.
- **No check that the detected face is the baby's** — any face counts
  right now. Left as an open problem.
- **No multi-camera fusion** when neither camera has a clean view.
- **MQTT not yet implemented** — a direct Postgres writer is used instead,
  a deliberate tradeoff (see DEVELOPMENT.md).
- **No automated tests, no CI.**
- **Plain HTTP, no auth** on ESP32 and dashboard endpoints — fine on a
  trusted home network only.
- **`CameraStreamManager` has grown to cover several responsibilities**
  that would benefit from being split apart.

---

## What's next (v2 ideas)

- Proper MQTT pub/sub once a second independent consumer justifies it
- CI/CD with cross-architecture (`arm64`) builds pushed to a registry
- Alembic migrations
- Covered-face / obstruction detection with a trained classifier
- Baby-vs-adult face verification
- Multi-camera view fusion for hard angles
- Split `CameraStreamManager` into focused classes
- API key auth, HTTPS via a reverse proxy
- Data retention/downsampling policy once volume warrants it