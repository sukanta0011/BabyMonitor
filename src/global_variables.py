import threading

NUM_OF_CAMS = 3
FACE_DETECTION_THRESHOLD = 0.4
SHUTDOWN_EVENT = threading.Event()
PRINT_LOCK = threading.Lock()
CAM1 = "http://192.168.1.104:81/stream"
CAM2 = "http://192.168.1.107:81/stream"
SENSORS = "http://esp32_cam1.local/sensors"