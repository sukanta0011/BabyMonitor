from src.backend.camera_stream import Camera, CameraStream
from src.backend.face_detector import MediaPiperDetector, YuNetDetector
import cv2
import threading
import time


test_lock = threading.Lock()

camera = Camera(
    ip="webcam", name="camera2",
    lock=test_lock, event=threading.Event()
    )
stream = CameraStream(camera)
fd = MediaPiperDetector(camera)
# fd = YuNetDetector(camera)
if stream.is_connected():
    stream.start()

while True:
    frame = stream.camera.frame
    if frame is not None and frame.size > 0:
        results = fd.extract_face_info()
        print(results)
    time.sleep(0.05)
