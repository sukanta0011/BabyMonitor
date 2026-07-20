from __future__ import annotations
import numpy as np
import mediapipe as mp
from typing import List, TYPE_CHECKING, Tuple
from abc import ABC, abstractmethod
import time
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from collections import deque
import numpy as np
from dataclasses import dataclass
if TYPE_CHECKING:
    from .camera_stream import CameraStream


@dataclass
class Result:
    face: bool
    face_region: Tuple = ()
    confidence_level: float = 0.0


class BoundingBoxSmoother:
    def __init__(self, window: int = 10):
        self.xs = deque(maxlen=window)
        self.ys = deque(maxlen=window)
        self.ws = deque(maxlen=window)
        self.hs = deque(maxlen=window)

    def update(self, x: int, y: int, w: int, h: int):
        self.xs.append(x)
        self.ys.append(y)
        self.ws.append(w)
        self.hs.append(h)

    def get_smooth(self):
        if not self.xs:
            return None
        return (
            int(np.mean(self.xs)),
            int(np.mean(self.ys)),
            int(np.mean(self.ws)),
            int(np.mean(self.hs))
        )


class FaceDetector(ABC):
    def __init__(self, camera_stream: CameraStream):
        self.stream = camera_stream
        self.initialize_the_model()

    @abstractmethod
    def initialize_the_model(self) -> None:
        pass
    
    @abstractmethod
    def extract_face_info(self):
        pass


class MediaPiperDetector(FaceDetector):
    def initialize_the_model(self):
        base_options = python.BaseOptions(
            model_asset_path='face_detection_models/blaze_face_full_range.tflite')
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE)
        self.detector = vision.FaceDetector.create_from_options(options)

    def extract_face_info(self) -> List[Result]:
        rgb_frame = cv2.cvtColor(
            self.stream.camera.frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        raw_info = self.detector.detect(mp_image)
        return self._store_face_info(raw_info)

    def _store_face_info(self, raw_info):
        results: List[Result]= []
        for info in raw_info.detections:
            results.append(Result(
                face=True,
                face_region=info.bounding_box,
                confidence_level=info.categories[0].score,
            ))
        if len(results) > 1:
            print(f"Faces: {len(results)}")
        return results

    def draw_detections(self) -> None:
        results = self.extract_face_info()
        camera = self.stream.camera
        for result in results:
            if result.face:
                x_c, y_c = result.face_region.origin_x,\
                    result.face_region.origin_y
                width_c = result.face_region.width
                height_c = result.face_region.height
                camera.smoother.update(x_c, y_c, width_c, height_c)
                x, y, w, h = camera.smoother.get_smooth()

                cv2.rectangle(camera.frame, (x, y), (x + w, y + h), (255, 0, 0), 1)
                cv2.putText(camera.frame, str(round(result.confidence_level, 2)),
                            (x, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                # cv2.circle(
                #     camera.frame,
                #     (int(result.left_eye.x * camera.frame.shape[1]),
                #         int(result.left_eye.y * camera.frame.shape[0])),
                #         2, (255, 0, 0), 1)



if __name__ == "__main__":
    from .camera_stream import Camera, CameraStream, BoundingBoxSmoother
    import threading
    import cv2
    import time

    test_lock = threading.Lock()

    camera = Camera(ip="webcam", name="camera2", lock=test_lock)
    stream = CameraStream(camera)
    media_pipe = MediaPiperDetector(stream)
    if stream.is_connected():
        stream.start()

    while True:
        frame = stream.camera.frame
        if frame is not None and frame.size > 0:
            results = media_pipe.extract_face_info()
            media_pipe.draw_detections()
            cv2.imshow("Webcam", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        time.sleep(0.05)

    stream.camera.capture.release()
    cv2.destroyAllWindows()
    print("Stream closed.")

