## Whole script is commented out to avoid import error
## This is just a copy of the origin script running on pi5


# #!/usr/bin/env python3
# import time
# import socket
# from datetime import datetime
# import spidev
# import gpiod
# from gpiod.line_settings import Direction, Value
# from PIL import Image, ImageDraw, ImageFont
# import psutil
# import docker

# # -------------------------------------------------------------
# # 0. CONFIGURATION & CONSTANTS (LANDSCAPE)
# # -------------------------------------------------------------
# WIDTH, HEIGHT = 160, 128

# PIN_DC = 24    # Pin 18 on 40-pin header
# PIN_RST = 25   # Pin 22 on 40-pin header

# MONITORED_CONTAINERS = [
#     {"name": "babymonitor-api-1", "label": "API"},
#     {"name": "postgres_db",       "label": "DB"},
#     {"name": "watchtower",        "label": "WT"},
# ]

# # -------------------------------------------------------------
# # 1. HARDWARE LAYER
# # -------------------------------------------------------------
# chip = gpiod.Chip("/dev/gpiochip0")
# settings = gpiod.LineSettings(direction=Direction.OUTPUT)
# lines = chip.request_lines(
#     consumer="server_monitor",
#     config={
#         PIN_DC: settings,
#         PIN_RST: settings,
#     },
# )

# def set_pin(pin, val):
#     lines.set_value(pin, Value.ACTIVE if val else Value.INACTIVE)

# spi = spidev.SpiDev()
# spi.open(0, 0)
# spi.max_speed_hz = 24000000
# spi.mode = 0b00

# def write_cmd(cmd):
#     set_pin(PIN_DC, 0)
#     spi.writebytes([cmd])

# def write_data(data):
#     set_pin(PIN_DC, 1)
#     spi.writebytes(data)

# def init_st7735():
#     set_pin(PIN_RST, 1)
#     time.sleep(0.05)
#     set_pin(PIN_RST, 0)
#     time.sleep(0.05)
#     set_pin(PIN_RST, 1)
#     time.sleep(0.15)

#     write_cmd(0x01)     # Software Reset
#     time.sleep(0.15)
#     write_cmd(0x11)     # Sleep Out
#     time.sleep(0.12)

#     # MADCTL: Memory Data Access Control (Landscape)
#     write_cmd(0x36)
#     write_data([0xA0])

#     write_cmd(0x3A)     # COLMOD: 16-bit color (RGB565)
#     write_data([0x05])
#     write_cmd(0x29)     # Display ON
#     time.sleep(0.05)

# def push_frame(image):
#     write_cmd(0x2A)  # Column Address Set
#     write_data([0x00, 0x00, 0x00, WIDTH - 1])
#     write_cmd(0x2B)  # Row Address Set
#     write_data([0x00, 0x00, 0x00, HEIGHT - 1])
#     write_cmd(0x2C)  # Memory Write (RAMWR)

#     rgb_image = image.convert("RGB")
#     raw_bytes = bytearray(WIDTH * HEIGHT * 2)
#     idx = 0

#     for r, g, b in rgb_image.getdata():
#         pixel = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
#         raw_bytes[idx] = (pixel >> 8) & 0xFF
#         raw_bytes[idx + 1] = pixel & 0xFF
#         idx += 2

#     chunk_size = 4096
#     set_pin(PIN_DC, 1)
#     for i in range(0, len(raw_bytes), chunk_size):
#         spi.writebytes(raw_bytes[i : i + chunk_size])

# # -------------------------------------------------------------
# # 2. TELEMETRY EXTRACTION
# # -------------------------------------------------------------
# try:
#     docker_client = docker.from_env()
# except Exception:
#     docker_client = None

# def get_ip():
#     try:
#         s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         s.connect(("8.8.8.8", 80))
#         ip = s.getsockname()[0]
#         s.close()
#         return ip
#     except Exception:
#         return "127.0.0.1"

# def get_cpu_temp():
#     try:
#         with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
#             return float(f.read().strip()) / 1000.0
#     except Exception:
#         return 0.0

# def get_docker_stack_telemetry():
#     if not docker_client:
#         return []

#     results = []
#     for item in MONITORED_CONTAINERS:
#         name = item["name"]
#         label = item["label"]
#         try:
#             c = docker_client.containers.get(name)
#             state = c.attrs.get("State", {})
#             status = c.status.lower()
#             health = state.get("Health", {}).get("Status", "")
#             restarts = c.attrs.get("RestartCount", 0)
#             oom = state.get("OOMKilled", False)

#             results.append({
#                 "label": label,
#                 "status": status,
#                 "health": health,
#                 "restarts": restarts,
#                 "oom": oom,
#             })
#         except docker.errors.NotFound:
#             results.append(
#                 {"label": label,
#                  "status": "missing",
#                  "health": "",
#                  "restarts": 0,
#                  "oom": False})
#         except Exception:
#             results.append(
#                 {"label": label,
#                  "status": "error",
#                  "health": "",
#                  "restarts": 0,
#                  "oom": False})
#     return results

# # -------------------------------------------------------------
# # 3. TIGHTENED LANDSCAPE DASHBOARD LAYOUT
# # -------------------------------------------------------------
# def draw_bar(draw, x, y, w, h, pct, fill_color, bg_color=(30, 30, 40)):
#     draw.rectangle([x, y, x + w, y + h], fill=bg_color)
#     fill_w = int((w * min(max(pct, 0), 100)) / 100)
#     if fill_w > 0:
#         draw.rectangle([x, y, x + fill_w, y + h], fill=fill_color)

# def render_dashboard(font):
#     img = Image.new("RGB", (WIDTH, HEIGHT), color=(0, 0, 0))
#     draw = ImageDraw.Draw(img)

#     # Telemetry sampling
#     cpu_pct = psutil.cpu_percent()
#     cpu_temp = get_cpu_temp()
#     ram = psutil.virtual_memory()
#     ip = get_ip()
#     containers = get_docker_stack_telemetry()

#     # Timestamps
#     now = datetime.now()
#     str_time = now.strftime("%H:%M:%S")
#     str_date = now.strftime("%d %b %Y")

#     # Color Palette
#     c_cyan   = (0, 210, 255)
#     c_green  = (40, 220, 80)
#     c_orange = (255, 150, 20)
#     c_red    = (255, 50, 50)
#     c_white  = (240, 240, 240)
#     c_gray   = (120, 125, 140)
#     c_sep    = (45, 50, 65)

#     # --- TWO-LINE TOP HEADER ---
#     # Line 1: Hostname & Date
#     draw.text((4, 1), "PI 5 MONITOR", font=font, fill=c_cyan)
#     draw.text((92, 1), str_date, font=font, fill=c_gray)

#     # Line 2: IP Address & Time
#     draw.text((4, 12), f"IP:{ip}", font=font, fill=c_gray)
#     draw.text((106, 12), str_time, font=font, fill=c_white)

#     # Header separator
#     draw.line([(0, 24), (WIDTH, 24)], fill=c_sep, width=1)

#     # --- LEFT COLUMN: COMPACT HOST METRICS (X: 4 to 76) ---
#     # CPU & Temp block
#     cpu_color = c_green if cpu_pct < 60 \
#         else (c_orange if cpu_pct < 85 else c_red)
#     temp_color = c_green if cpu_temp < 65 \
#         else (c_orange if cpu_temp < 80 else c_red)
#     draw.text((4, 27), f"CPU:{cpu_pct:3.0f}%", font=font, fill=cpu_color)
#     draw.text((46, 27), f"{cpu_temp:4.1f}C", font=font, fill=temp_color)
#     draw_bar(draw, 4, 38, 70, 3, cpu_pct, cpu_color)

#     # RAM block
#     ram_pct = ram.percent
#     ram_used_mb = ram.used // (1024 * 1024)
#     ram_color = c_green if ram_pct < 70 \
#         else (c_orange if ram_pct < 88 else c_red)
#     draw.text((4, 44), f"RAM:{ram_pct:3.0f}%", font=font, fill=ram_color)
#     draw.text((46, 44), f"{ram_used_mb}M", font=font, fill=c_gray)
#     draw_bar(draw, 4, 55, 70, 3, ram_pct, ram_color)

#     # Load average block
#     load1, load5, _ = psutil.getloadavg()
#     draw.text((4, 61), f"L1:{load1:.2f}", font=font, fill=c_white)
#     draw.text((46, 61), f"L5:{load5:.2f}", font=font, fill=c_gray)

#     # Disk usage block (utilizing former empty space)
#     disk = psutil.disk_usage("/")
#     disk_pct = disk.percent
#     disk_color = c_green if disk_pct < 75 \
#         else (c_orange if disk_pct < 90 else c_red)
#     draw.text((4, 73), f"DSK:{disk_pct:3.0f}%", font=font, fill=disk_color)
#     draw.text(
#              (46, 73), f"{disk.free // (1024**3)}GB", font=font, fill=c_gray)
#     draw_bar(draw, 4, 84, 70, 3, disk_pct, disk_color)

#     # --- VERTICAL DIVIDER ---
#     draw.line([(78, 24), (78, 114)], fill=c_sep, width=1)

#     # --- RIGHT COLUMN: DOCKER CONTAINERS (X: 82 to 156) ---
#     draw.text((82, 27), "CONTAINERS", font=font, fill=c_cyan)

#     y_pos = 41
#     for c in containers:
#         if c["status"] == "running":
#             status_text = "UNHLTH" if c["health"] == "unhealthy" else "OK"
#             status_col = c_red if c["health"] == "unhealthy" else c_green
#         else:
#             status_text = c["status"][:4].upper()
#             status_col = c_red

#         rst = c["restarts"]
#         warn_text = "OOM" if c["oom"] else (f"R:{rst}" if rst > 0 else "")
#         warn_col = c_red if c["oom"] else c_orange

#         draw.text((82, y_pos), f"{c['label']}:", font=font, fill=c_white)
#         draw.text((106, y_pos), status_text, font=font, fill=status_col)
#         if warn_text:
#             draw.text((138, y_pos), warn_text, font=font, fill=warn_col)

#         y_pos += 15

#     # --- FOOTER BAR (Uptime & Task Count) ---
#     draw.line([(0, 114), (WIDTH, 114)], fill=c_sep, width=1)
#     uptime_sec = int(time.time() - psutil.boot_time())
#     hrs = uptime_sec // 3600
#     mins = (uptime_sec % 3600) // 60
#     draw.text((4, 117), f"UP : {hrs}h {mins}m", font=font, fill=c_gray)
#     draw.text(
#         (106, 117), f"TASKS:{len(psutil.pids())}", font=font, fill=c_gray)

#     return img

# # -------------------------------------------------------------
# # 4. ENTRYPOINT
# # -------------------------------------------------------------
# def main():
#     init_st7735()
#     font = ImageFont.load_default()
#     psutil.cpu_percent(interval=None)

#     print("Dashboard running. Press Ctrl+C to exit.")
#     try:
#         while True:
#             frame = render_dashboard(font)
#             push_frame(frame)
#             time.sleep(1.0)
#     except KeyboardInterrupt:
#         print("\nExiting...")
#     finally:
#         spi.close()

# if __name__ == "__main__":
#     main()
