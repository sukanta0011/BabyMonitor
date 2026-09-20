# Baby Sleep Monitoring System — v1

A portfolio project born out of a real need: keeping an eye on a sleeping
baby, from multiple angles, with actual environmental data instead of just
a video feed.

**Not a medical device.** It's an engineering project — real-time CV,
embedded firmware, systems design. See [Known Limitations](#known-limitations).

![](https://github.com/sukanta0011/BabyMonitor/blob/main/screenshots/babymonitor_v1.gif)

For the full story — why things are built this way, bugs hit and how they
were diagnosed, load-testing numbers — see [development_journey.md](development_journey.md)
and [improvements.md](improvements.md).

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
- **Standalone ESP32-S3 display client**: a physical, always-on 480×320
  SPI screen that pulls the live video feed and sensor data directly from
  the FastAPI backend and renders them with no phone or laptop involved —
  custom MJPEG-over-chunked-HTTP parser, a fixed-size ring buffer, and
  dual-core FreeRTOS tasks for network I/O and decode/display, written
  from scratch (see [improvements.md](improvements.md))
- A physical push button on the S3 client cycles between two camera feeds
  and a live sensor panel, debounced and interrupt-driven
- **ESP8266 sensor node has its own local ST7735 display**, showing indoor
  readings and live outdoor weather (fetched from Open-Meteo, geolocated
  via IP) independently of the S3 client or the Pi — the room stays
  monitorable even if the rest of the stack is down
- **Second physical status display on the Pi itself**: a landscape ST7735
  dashboard showing host health (CPU, RAM, disk, load, uptime) and
  per-container Docker status (`api`, `db`, `watchtower`) via `docker-py`
  and raw `spidev`/`gpiod` — a glance-able "is the system actually alive"
  readout with no laptop needed
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
ESP32 sensor node ─ HTTP ────┤        ESP32-S3 display client
 (BH1750 + SCD40,            │        (480x320 SPI, button-switched
  local ST7735 + weather)    │         CAM1/CAM2/Sensors, custom
                             ▼         MJPEG parser + ring buffer)
                  ┌─────────────────────────┐        ▲
                  │   FastAPI (Docker, Pi)   │────────┘
                  │  ├─ CameraStream(s)      │  /video/{cam}, /sensors
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

Pi's own SPI status display (spidev/gpiod) ── host + Docker telemetry
CI (GitHub Actions) ──▶ ghcr.io ──▶ Watchtower on Pi (auto-pull, restart)
```

---

## Hardware

- 2× ESP32-CAM (AI-Thinker)
- 1× ESP8266 sensor node (BH1750, SCD40) with its own ST7735 display
- 1× ESP32-S3 — dedicated video/sensor display client, ILI9488 480×320
  SPI TFT, one push button
- BH1750 — light (I2C `0x23`)
- SCD40 — CO2, temperature, humidity (I2C `0x62`)
- BMP280 — turned out to be dead on arrival
- Raspberry Pi 5 — production host, headless (Raspberry Pi OS Lite), with
  its own ST7735 status display wired directly to its GPIO/SPI header

## Software

- **Firmware:** Arduino/C++, ESPAsyncWebServer, ArduinoJson, ESPmDNS,
  FreeRTOS mutexes, an abstract `Sensor` base class for the I2C drivers
- **S3 display client:** custom C++ ring buffer (templated, dual-mutex —
  `std::mutex` for host testing, `SemaphoreHandle_t` on-device), hand-
  written chunked-transfer/multipart MJPEG parser, TJpg_Decoder with a
  from-scratch per-block nearest-neighbor scaler for letterboxed display,
  dual-core FreeRTOS tasks (network read / decode+display / sensor poll),
  interrupt-driven mode switching, PSRAM-backed buffers
- **Backend:** FastAPI, async MJPEG fan-out, SQLAlchemy (async) + Postgres,
  OpenCV, YuNet (ARM) / MediaPipe (x86, optional), `requests`, `threading`
  + `asyncio` side by side, structured JSON logging
- **Pi status display:** Python, `spidev` + `gpiod` (direct SPI/GPIO, no
  display library), `PIL` for rendering, `psutil` + `docker` for telemetry
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
  poses** — empirically tested and confirmed (see improvements.md);
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
  never alters existing ones — schema changes are deployed manually until
  Alembic is in place (see development_journey.md).
- **Plain HTTP, no auth** on ESP32 and dashboard endpoints — fine on a
  trusted home network only. No external/remote access is currently
  enabled (Tailscale evaluated, not yet set up).
- **`CameraStreamManager` has grown to cover several responsibilities**
  that would benefit from being split apart.
- **Best-camera status can go stale during a sustained no-face-detected
  period** — manual per-camera selection is the workaround.
- **S3 display client has no camera reconnect-on-failure retry** — a
  failed connection shows a persistent error screen until the button is
  pressed again; it does not auto-retry.
- **Pi status display's startup/persistence across reboots not yet
  formalized** (no systemd unit/restart policy confirmed).

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
- systemd unit + restart policy for the Pi status display
- Auto-retry/reconnect on the S3 display client's camera connection