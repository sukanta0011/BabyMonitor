from typing import List
import numpy as np
from enum import StrEnum
import time
from dataclasses import dataclass, field
import threading
import cv2
from ..global_variables import FACE_DETECTION_THRESHOLD, SHUTDOWN_EVENT
from .face_detector import FaceDetector, Result
from .custom_errors import FaceDetectionError
from .camera_stream import Camera
from .helper_functions import print_message


class FaceDetectionStatus(StrEnum):
    NORMAL = "normal"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class Message:
    status: FaceDetectionStatus = FaceDetectionStatus.NORMAL
    text: str = ""


@dataclass
class BestCameraStream:
    index: int | None = None
    name: str | None = None
    frame: np.ndarray | None = None
    encoded_frame: bytes | None = None
    result: Result | None = None
    message: Message = Message
    thread: threading.Thread | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    detection_failure_event: threading.Event =\
        field(default_factory=threading.Event)


class CameraStreamManager:
    def __init__(
            self, face_detectors: List[FaceDetector],
            best_stream: BestCameraStream,
            face_detection_threshold: float = FACE_DETECTION_THRESHOLD):
        self.face_detectors = face_detectors
        self.face_detection_threshold = face_detection_threshold
        self.best_stream = best_stream

    def start_camera_feed(self) -> np.ndarray:
        self.best_stream.thread = threading.Thread(
            target=self._run_detection_loop, args=(), daemon=True)
        self.best_stream.thread.start()

    def stop_camera_feed(self, timeout: float = 5) -> None:
        if self.best_stream.thread is not None:
            self.best_stream.thread.join(timeout)

    def _run_detection_loop(self) -> None:
        idx = self.best_stream.index
        time_out = 2
        sleep_time = 0.2
        time_since_detection_failed = time.time()
        single_result = Result(face=False)
        while not SHUTDOWN_EVENT.is_set():
            try:
                if idx is None:
                    idx = self.get_best_camera()
                    # self.stop_all_cam()
                    # self.start_single_cam(
                    #     self.face_detectors[idx].stream.camera)
                self._wait_for_frame_detection(self.face_detectors[idx])
                if not SHUTDOWN_EVENT.is_set():
                    result: Result = \
                        self.face_detectors[idx].extract_face_info()
                    if len(result) > 0:
                        single_result = result[0]
                    else:
                        single_result = Result(face=False)
                    if (not single_result.face or
                            single_result.confidence_level <
                            self.face_detection_threshold) and \
                            not SHUTDOWN_EVENT.is_set():
                        print_message(
                            "Face quality falls below threshold, trying again")
                        idx = self.retry_face_detection(idx)
                    time_since_detection_failed = time.time()
                    time.sleep(sleep_time)
            except FaceDetectionError as e:
                print_message(e)
                if (time.time() - time_since_detection_failed) > time_out:
                    msg = "Warning: face detection failure"
                    self.best_stream.message.status = \
                        FaceDetectionStatus.WARNING
                    self.best_stream.message.text = msg
                    print_message(msg)
                    self.best_stream.detection_failure_event.set()
                    self.trigger_alarm()

                msg = "Retrying for " + \
                      f"{time.time() - time_since_detection_failed}s"
                self.best_stream.message.status = FaceDetectionStatus.ERROR
                self.best_stream.message.text = msg
                print_message(msg)

            if idx is not None and not SHUTDOWN_EVENT.is_set():
                with self.best_stream.lock:
                    self.best_stream.message.status = \
                        FaceDetectionStatus.NORMAL
                    self.best_stream.message.text = "Face detected"
                    self.best_stream.index = idx
                    self.best_stream.name = \
                        self.face_detectors[idx].stream.camera.name
                    frame = self.face_detectors[idx].stream.camera.frame
                    self.best_stream.frame = frame
                    #  Encode the frame
                    success, buffer= cv2.imencode(".jpg", frame)
                    if success:
                        self.best_stream.encoded_frame = b'--frame\r\n' +\
                            b'Content-Type: image/jpeg\r\n\r\n' + \
                            buffer.tobytes() + b'\r\n'

                    self.best_stream.result = single_result

    def trigger_alarm(self) -> None:
        while not SHUTDOWN_EVENT.is_set() and \
                self.best_stream.detection_failure_event.is_set():
            try:
                if self.get_best_camera(retry=1) is not None:
                    self.best_stream.detection_failure_event.clear()
            except FaceDetectionError:
                print_message("ERROR......")
                msg = "ERROR...."
                self.best_stream.message.status = FaceDetectionStatus.ERROR
                self.best_stream.message.text = msg
                time.sleep(0.2)

    def get_best_camera(self, retry: int = 3) -> int:
        attempts = 0
        best_camera_index = None
        while (attempts < retry and not SHUTDOWN_EVENT.is_set()):
            results: List[Result] = []
            for detector in self.face_detectors:
                self._wait_for_frame_detection(detector)
                faces = detector.extract_face_info()
                if len(faces) > 0:
                    print_message(
                        f"best camera name: {detector.stream.camera.name}")
                    print_message(faces)
                    results.append(faces[0])
                else:
                    results.append(Result(face=False))
            scores = [result.confidence_level for result in results]
            best_camera_index = np.argmax(scores)
            if scores[best_camera_index] > self.face_detection_threshold:
                return best_camera_index
            attempts += 1
            time.sleep(1)
            msg = "best camera detection failed " + \
                  f"{attempts}/{retry}. Retrying ..."
            self.best_stream.message.status = FaceDetectionStatus.WARNING
            self.best_stream.message.text = msg
            print_message(msg)
        raise FaceDetectionError("Unable to detect face by any camera")

    def _wait_for_frame_detection(
            self, detector: FaceDetector,
            timeout: int = 2) -> None:
        wait_time = 0.0
        while (detector.stream.camera.frame is None and
                not SHUTDOWN_EVENT.is_set()):
            if wait_time < timeout:
                print_message(f"Waiting for {detector.stream.camera.name}")
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
        while (attempts < retry and not SHUTDOWN_EVENT.is_set()):
            result: Result = \
                self.face_detectors[cam_idx].extract_face_info()
            if len(result) > 0:
                single_result = result[0]
            if single_result.face and\
                    single_result.confidence_level >\
                    self.face_detection_threshold:
                return cam_idx
            else:
                msg = "Face detection quality decreased for " +\
                      f"{self.face_detectors[cam_idx].stream.camera.name}. " +\
                      f"Attempt {attempts + 1}/{retry}."
                self.best_stream.message.status = FaceDetectionStatus.WARNING
                self.best_stream.message.text = msg
                print_message(msg)
            attempts += 1
            time.sleep(1)
        return self.get_best_camera()

    def start_all_cam(self) -> None:
        for face_detector in self.face_detectors:
            self.start_single_cam(face_detector.stream.camera)

    def stop_all_cam(self) -> None:
        for face_detector in self.face_detectors:
            self.stop_single_cam(face_detector.stream.camera)

    def start_single_cam(self, camera: Camera) -> None:
        camera.event.set()

    def stop_single_cam(self, camera: Camera) -> None:
        camera.event.clear()
