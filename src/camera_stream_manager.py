from typing import List
import numpy as np
import time
from dataclasses import dataclass, field
import threading
from .face_detector import FaceDetector, Result
from .custom_errors import FaceDetectionError
from .camera_stream import Camera
from .helper_functions import print_message


@dataclass
class BestCameraStream:
    best_camera_index: int| None = None
    thread: threading.Thread | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    detection_failure_event: threading.Event =\
        field(default_factory=threading.Event)


class CameraStreamManager:
    def __init__(
            self, face_detectors: List[FaceDetector],
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
        time_out = 2
        sleep_time = 0.2
        time_since_detection_failed = time.time()
        single_result = Result(face=False)
        while True:
            try:
                if not idx:
                    idx = self.get_best_camera()
                    self.stop_all_cam()
                    self.start_single_cam(
                        self.face_detectors[idx].stream.camera)
                self._wait_for_frame_detection(self.face_detectors[idx])
                result: Result = self.face_detectors[idx].extract_face_info()
                if len(result) > 0:
                    single_result = result[0]
                if not single_result.face or\
                        single_result.confidence_level < self.face_detection_threshold:
                    idx = self.retry_face_detection(idx)
                time_since_detection_failed = time.time()
                time.sleep(sleep_time)
            except FaceDetectionError as e:
                print_message(e)
                if (time.time() - time_since_detection_failed) > time_out:
                    print_message("Warning: face detection failure")
                    self.best_stream.detection_failure_event.set()
                print_message(f"Retrying for {time.time() - time_since_detection_failed}s")

            with self.best_stream.lock:
                self.best_stream.best_camera_index = idx

    def get_best_camera(self, retry: int = 3) -> int:
        attempts = 0
        best_camera_index = 0
        while (attempts < retry):
            results: List[Result] = []
            for detector in self.face_detectors:
                self._wait_for_frame_detection(detector)
                faces = detector.extract_face_info()
                if len(faces) > 1:
                    results.append(faces[0])
                else:
                    results.append(Result(face=False))
            scores = [result.confidence_level for result in results]
            best_camera_index = np.argmax(scores)
            if scores[best_camera_index] > self.face_detection_threshold:
                return best_camera_index
            attempts += 1
            time.sleep(1)
            print_message(f"best camera detection failed {attempts}/{retry}. Retrying ...")
        raise FaceDetectionError("Unable to detect face by any camera")

    def _wait_for_frame_detection(
            self, detector: FaceDetector, timeout: int = 2):
        wait_time = 0
        while detector.stream.camera.frame is None:
            if wait_time < timeout:
                time.sleep(0.1)
                wait_time += 0.1
            else:
                print_message(
                    "Unable to get camera feed from "
                    f"'{detector.stream.camera.name}'"
                )
                self.get_best_camera()

    def retry_face_detection(
            self, cam_idx: int,
            retry: int = 3) -> int:
        attempts = 0
        single_result = Result(face=False)
        while (attempts < retry):
            result: Result = \
                self.face_detectors[cam_idx].extract_face_info()
            if len(result) > 0:
                single_result = result[0]
            if single_result.face and\
                    single_result.confidence_level >\
                        self.face_detection_threshold:
                return cam_idx
            else:
                print_message(
                    "Face detection quality decreased for "
                    f"{self.face_detectors[cam_idx].stream.camera.name}. "
                    f"Attempt {attempts + 1}/{retry}.")
            attempts += 1
            time.sleep(1)
        return self.get_best_camera()

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
 