import cv2
import logging
from dataclasses import dataclass, field
import numpy as np
import threading
from .face_detector import BoundingBoxSmoother
from .base_class import Stream


logger = logging.getLogger(__name__)


@dataclass
class Camera:
    ip: str
    name: str
    lock: threading.Lock
    event: threading.Event
    is_active: bool = False  # False == off, True == on
    capture: cv2.VideoCapture | None = None
    ret: int | None = None
    frame: np.ndarray | None = None
    thread: threading.Thread | None = None
    smoother: BoundingBoxSmoother = \
        field(default_factory=lambda: BoundingBoxSmoother(1))


from ..global_variables import SHUTDOWN_EVENT # noqa: E402


class CameraStream(Stream):
    def __init__(self, camera: Camera) -> None:
        self.camera = camera

    def is_connected(self) -> bool:
        logger.info(f"Connecting to stream: {self.camera.ip}")
        if self.camera.ip == "webcam":
            self.camera.capture = cv2.VideoCapture(0)
        else:
            self.camera.capture = cv2.VideoCapture(self.camera.ip)
        # Avoid storing frames
        self.camera.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self.camera.capture.isOpened():
            logger.warning("Error: Could not open the HTTP stream. "
                           "Check the IP and network connection.")
            return False
        logger.info(f"Connecting established to: {self.camera.ip}")
        self.camera.is_active = True
        return True

    def start(self) -> None:
        self.camera.thread = threading.Thread(
            target=self._continue_capturing, args=(), daemon=True
            )
        self.camera.event.set()
        self.camera.thread.start()
        logger.info(f"'{self.camera.name}' started")

    def _continue_capturing(self) -> None:
        consecutive_failures = 0
        failure_threshold = 5
        while not SHUTDOWN_EVENT.is_set():
            self.camera.event.wait()
            if self.camera.capture:
                ret, frame = self.camera.capture.read()
                if ret:
                    consecutive_failures = 0
                    with self.camera.lock:
                        self.camera.frame = frame
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= failure_threshold:
                        with self.camera.lock:
                            self.camera.is_active = False
                            self.camera.frame = None
                        logger.warning(f"'{self.camera.name}' connection lost")
                        return


if __name__ == "__main__":
    pass
