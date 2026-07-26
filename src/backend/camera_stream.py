import cv2
from dataclasses import dataclass, field
import numpy as np
import threading
from .face_detector import BoundingBoxSmoother
from ..global_variables import SHUTDOWN_EVENT


@dataclass
class Camera:
    ip: str
    name: str
    lock: threading.Lock
    event: threading.Event
    capture: cv2.VideoCapture | None = None
    ret: int | None = None
    frame: np.ndarray | None = None
    thread: threading.Thread | None = None
    smoother: BoundingBoxSmoother = \
        field(default_factory=lambda: BoundingBoxSmoother(1))


class CameraStream:
    def __init__(self, camera: Camera) -> None:
        self.camera = camera

    def is_connected(self) -> bool:
        print(f"Connecting to stream: {self.camera.ip}")
        if self.camera.ip == "webcam":
            self.camera.capture = cv2.VideoCapture(0)
        else:
            self.camera.capture = cv2.VideoCapture(self.camera.ip)
        self.camera.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Avoid storing frames

        if not self.camera.capture.isOpened():
            print("Error: Could not open the HTTP stream." \
                "Check the IP and network connection.")
            return False
        print(f"Connecting established to: {self.camera.ip}")
        return True
    
    def start(self) -> None:
        self.camera.thread = threading.Thread(
            target=self._continue_capturing, args=(), daemon=True
            )
        self.camera.event.set()
        self.camera.thread.start()
        print(f"'{self.camera.name}' started")

    def _continue_capturing(self) -> None:
        while not SHUTDOWN_EVENT.is_set():
            self.camera.event.wait()
            ret, frame = self.camera.capture.read()
            if ret:
                with self.camera.lock:
                    self.camera.frame = frame


if __name__ == "__main__":
    pass