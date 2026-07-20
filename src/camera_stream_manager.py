from typing import List
import numpy as np
from .face_detector import FaceDetector, Result
from .custom_errors import FaceDetectionError
from .camera_stream import Camera


class CameraStreamManager:
    def __init__(self, face_detectors: List[FaceDetector],
                 face_detection_threshold: float = 0.6):
        self.face_detectors = face_detectors
        self.face_detection_threshold = face_detection_threshold

    def start_camera_feed(self) -> None:
        try:
            idx = self.get_best_camera()
            self.stop_all_cam()
            self.start_single_cam(
                self.face_detectors[idx].stream.camera)
            result: Result = self.face_detectors[idx].extract_face_info()
            if not result.face or\
                    result.confidence_level < self.face_detection_threshold:
                idx = self.retry_face_detection(idx)
        except FaceDetectionError as e:
            raise FaceDetectionError(e) from e

    def get_best_camera(self, retry: int = 3) -> int:
        attempts = 0
        best_camera_index = -1
        while (attempts < retry):
            results: List[Result] = []
            for detector in self.face_detectors:
                results.append(
                    detector.extract_face_info()[0])
            scores = [
                result.confidence_level if result.face else 0
                for result in results
                ]
            best_camera_index = np.argmax(scores)
            if scores[best_camera_index] > self.face_detection_threshold:
                return best_camera_index
            attempts += 1
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
                    "Attempt {attempts + 1}/retry")
            attempts += 1
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
        camera.event.pause()
 