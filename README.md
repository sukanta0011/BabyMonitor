# Baby Sleep Monitoring System — v1

A portfolio project born out of a real need: keeping an eye on a sleeping
baby, from multiple angles, with actual environmental data instead of just
a video feed.

**Not a medical device.** It's an engineering project — real-time CV,
embedded firmware, systems design. See [Known Limitations](#known-limitations).

![](https://github.com/sukanta0011/BabyMonitor/blob/main/screenshots/babymonitor_v1.gif)

For the full story — why things are built this way, bugs hit and how they
were diagnosed, load-testing numbers — see [development_journey.md](development_journey.md).

---

## What it does

- Streams video from two ESP32-CAM nodes over WiFi (MJPEG/HTTP), with
  automatic best-camera selection based on live face-detection confidence,
  plus manual per-camera viewing for when the auto-selected feed can't
  confirm anything
- Automatically detects and reconnects cameras and the sensor node that
  weren't reachable at startup, or that drop out mid-session
- Reads live temperature, humidity, CO2, and light from a separate ESP32
  sensor node over I2C, and persists every reading to Postgres
- Flags sensor readings that fall outside nursery-appropriate ranges, with
  webhook push notifications (ntfy) on sustained threshold breaches or
  detection failures
- Serves a lightweight FastAPI backend + phone-optimized HTML dashboard,
  accessible from any device on the local network — tested with hundreds
  of concurrent viewers with no meaningful degradation
- Runs fully containerized via Docker Compose, deployed and verified on a
  Raspberry Pi 5, with CI (lint, type-check, cross-architecture Docker
  builds) on every push, and Watchtower auto-pulling new images on the Pi
- Structured JSON logging, rotated, for real production debugging

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
                  │  ├─ Postgres writer      │
                  │  └─ webhook alerts       │
                  └───────────┬─────────────┘
                               │
                    Postgres (Docker)
                               │
                    Phone / laptop browser
                    (HTML dashboard, polling)

CI (GitHub Actions) ──▶ ghcr.io ──▶ Watchtower on Pi (auto-pull, restart)
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
  + `asyncio` side by side, structured JSON logging
- **Frontend:** plain HTML/CSS/JS, phone-first, no framework
- **Deploy:** Docker Compose (FastAPI + Postgres + Watchtower), running on
  Raspberry Pi 5
- **CI:** GitHub Actions — `ruff`/`mypy` on every push and PR, `arm64`
  Docker image built and pushed to `ghcr.io` on every merge to `main`

---

## Known Limitations

Cut from v1 on purpose, not forgotten:

- **No covered-face detection** — needs a purpose-trained model, out of
  scope for v1.
- **Face detection has real, measured blind spots on natural sleeping
  poses** — empirically tested and confirmed (see development_journey.md);
  scale, rotation, and contrast preprocessing were all ruled out as
  fixes. Manual per-camera viewing is the current mitigation.
- **No check that the detected face is the baby's** — any face counts
  right now. Left as an open problem.
- **No multi-camera fusion** when neither camera has a clean view.
- **MQTT not yet implemented** — a direct Postgres writer is used instead,
  a deliberate tradeoff (see development_journey.md).
- **No automated tests running in CI yet** — a pytest suite exists
  (thresholds, sensor stream mocking) but isn't wired into the CI
  workflow; lint and type-checking are.
- **No database migrations (Alembic).** Currently using
  `Base.metadata.create_all()`, which only creates missing tables and
  never alters existing ones. This makes automated deployment **unsafe
  for any change that modifies `models.py`** — a schema change deployed
  via the automated pipeline would update the code but leave the database
  schema stale, breaking on the first read/write to the changed table.
  Until Alembic is in place, schema changes are deployed manually, with
  the migration applied by hand before the new image is allowed to run.
  Deliberately deferred until real schema iteration starts, rather than
  building migration tooling for a schema that's still finding its shape.
- **Plain HTTP, no auth** on ESP32 and dashboard endpoints — fine on a
  trusted home network only. No external/remote access is currently
  enabled (Tailscale evaluated, not yet set up).
- **`CameraStreamManager` has grown to cover several responsibilities**
  that would benefit from being split apart.
- **Best-camera status can go stale during a sustained no-face-detected
  period** — the recovery loop retries until any camera clears the
  confidence threshold, which can take a while if none currently can;
  the displayed "face detected" status can lag reality during that
  window. Manual per-camera selection is the workaround.

---

## What's next (v2 ideas)

- Alembic migrations, once real schema iteration starts
- Proper MQTT pub/sub once a second independent consumer justifies it
- pytest suite wired into CI
- Tailscale for remote (office) access, with real auth in front of the
  stream before any external exposure
- Fine-tuned/infant-specific face detection model
- Covered-face / obstruction detection with a trained classifier
- Baby-vs-adult face verification
- Multi-camera view fusion for hard angles
- Split `CameraStreamManager` into focused classes
- API key auth, HTTPS via a reverse proxy
- Data retention/downsampling policy once volume warrants it
- Two-way audio (dedicated ESP32, not layered onto the camera boards)