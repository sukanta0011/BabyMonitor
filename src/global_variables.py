import threading
from collections import deque

NUM_OF_CAMS = 3
FACE_DETECTION_THRESHOLD = 0.4
SHUTDOWN_EVENT = threading.Event()
# PRINT_LOCK = threading.Lock()
CAM1 = "http://192.168.1.104:81/stream"
CAM2 = "http://192.168.1.105:81/stream"
# SENSORS = "http://esp32_sensor1.local/sensors"
SENSORS = "http://192.168.1.111/sensors"
DATABASE_URL =\
    "postgresql+asyncpg://baby_monitor:baby_monitor@db/baby_monitor_db"


camera_data_lock = threading.Lock()
sensor_data_lock = threading.Lock()
active_camera_detection_lock = threading.Lock()

from src.backend.camera_stream import Camera # noqa: E402

CAMERAS = [
    Camera(
        ip=CAM1, name="cam1",
        lock=camera_data_lock,
        event=threading.Event()),
    Camera(
        ip=CAM2, name="cam2",
        lock=camera_data_lock,
        event=threading.Event()),
    # Camera(
    #     ip="webcam", name="webcam",
    #     lock=camera_data_lock,
    #     event=threading.Event()),
]

from src.backend.sensor_stream import Sensor # noqa: E402

SENSOR = Sensor(
    address=SENSORS, data=deque(), lock=sensor_data_lock)
