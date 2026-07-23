from typing import List
import numpy as np
import time
from dataclasses import dataclass, field
import threading
from .face_detector import FaceDetector, Result
from .custom_errors import FaceDetectionError
from .camera_stream import Camera


@dataclass
class BestCameraStream:
    best_camera_index: int| None = None
    thread: threading.Thread | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    detection_failure_event: threading.Event =\
        field(default_factory=threading.Event)


class CameraStreamManager:
    def __init__(self, face_detectors: List[FaceDetector],
                 best_stream: BestCameraStream,
                 face_detection_threshold: float = 0.6):
        self.face_detectors = face_detectors
        self.face_detection_threshold = face_detection_threshold
        self.best_stream = best_stream

    def start_camera_feed(self) -> np.ndarray:
        self.best_stream.thread = threading.Thread(
            target=self._run_detection_loop, args=(), daemon=True)
        self.best_stream.thread.start()

    def _run_detection_loop(self) -> None:
        idx = self.best_stream.best_camera_index
        time_out = 5
        sleep_time = 0.5
        time_since_detection_failed = 0
        while True:
            try:
                if not idx:
                    idx = self.get_best_camera()
                    self.stop_all_cam()
                    self.start_single_cam(
                        self.face_detectors[idx].stream.camera)
                result: Result = self.face_detectors[idx].extract_face_info()
                if not result.face or\
                        result.confidence_level < self.face_detection_threshold:
                    idx = self.retry_face_detection(idx)
                time_since_detection_failed = 0
                time.sleep(sleep_time)
            except FaceDetectionError as e:
                print(e)
                if time_since_detection_failed > time_out:
                    print("Warning: face detection failure")
                    self.best_stream.detection_failure_event.set()
                time_since_detection_failed += sleep_time

            with self.best_stream.lock:
                self.best_stream.best_camera_index = idx

    def get_best_camera(self, retry: int = 3) -> int:
        attempts = 0
        best_camera_index = 0
        while (attempts < retry):
            results: List[Result] = []
            for detector in self.face_detectors:
                if len(detector.extract_face_info()) > 1:
                    results.append(
                        detector.extract_face_info()[0])
            scores = [
                result.confidence_level if result.face else 0
                for result in results]
            best_camera_index = np.argmax(scores)
            if scores[best_camera_index] > self.face_detection_threshold:
                return best_camera_index
            attempts += 1
            time.sleep(1)
            print(f"best camera detection failed {attempts}/{retry}. Retrying ...")
            
        raise FaceDetectionError("Unable to detect face by any camera")

    def retry_face_detection(
            self, cam_idx: int,
            retry: int = 3) -> int:
        attempts = 0
        while (attempts < retry):
            result: Result = \
                self.face_detectors[cam_idx].extract_face_info()
            if result.face and\
                    result.confidence_level >\
                        self.face_detection_threshold:
                return cam_idx
            else:
                print(
                    "Face detection quality decreased for "
                    f"{self.face_detectors[cam_idx].stream.camera.name}. "
                    f"Attempt {attempts + 1}/{retry}.")
            attempts += 1
            time.sleep(1)
        return None

    def start_all_cam(self):
        for face_detector in self.face_detectors:
            self.start_single_cam(face_detector.stream.camera)
    
    def stop_all_cam(self):
        for face_detector in self.face_detectors:
            self.stop_single_cam(face_detector.stream.camera)
    
    def start_single_cam(self, camera: Camera) -> None:
        camera.event.set()
    
    def stop_single_cam(self, camera: Camera) -> None:
        camera.event.clear()
 