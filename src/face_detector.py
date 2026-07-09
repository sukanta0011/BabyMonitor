from __future__ import annotations
import numpy as np
import mediapipe as mp
from typing import List, TYPE_CHECKING
from abc import ABC, abstractmethod
import time

from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from collections import deque
import numpy as np
if TYPE_CHECKING:
    from .camera_stream import Camera

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
    def __init__(self):
        self._initialize_the_model()

    @abstractmethod
    def _initialize_the_model(self) -> None:
        pass
    
    @abstractmethod
    def extract_face_info(self):
        pass


class MediaPiperDetector(FaceDetector):
    def _initialize_the_model(self):
        base_options = python.BaseOptions(
            model_asset_path='face_detection_models/blaze_face_full_range.tflite')
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE)
        self.detector = vision.FaceDetector.create_from_options(options)

    def extract_face_info(self, cameras: Camera):
        self.face_info = []
        mp_images = []
        for camera in cameras:
            rgb_frame = cv2.cvtColor(camera.frame, cv2.COLOR_BGR2RGB)
            mp_images.append(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame))
        for mp_image in mp_images:
            self.face_info.append(self.detector.detect(mp_image))
        return self.face_info
    
    def draw_detections(self, cameras: Camera, results) -> List[np.ndarray]:
        for c, r in zip(cameras, results):
            if len(r.detections) > 0:
                x_c, y_c = r.detections[0].bounding_box.origin_x,\
                    r.detections[0].bounding_box.origin_y
                width_c = r.detections[0].bounding_box.width
                height_c = r.detections[0].bounding_box.height
                c.smoother.update(x_c, y_c, width_c, height_c)
                x, y, w, h = c.smoother.get_smooth()

                cv2.rectangle(c.frame, (x, y), (x + w, y + h), (255, 0, 0), 1)
                cv2.putText(c.frame, str(round(r.detections[0].categories[0].score, 2)),
                            (x, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                for keypoint in r.detections[0].keypoints:
                    cv2.circle(c.frame, (int(keypoint.x * c.frame.shape[1]), int(keypoint.y * c.frame.shape[0])), 2, (255, 0, 0), 1)

    def store_result(self, result, output_image: mp.Image, timestamp_ms: int):
        self.face_info.append(result)


if __name__ == "__main__":
    from .camera_stream import Camera, CameraStream, BoundingBoxSmoother
    import threading
    import cv2
    import time

    test_lock = threading.Lock()

    cameras = [Camera(ip="webcam", name="camera2", lock=test_lock)]
    stream = CameraStream(cameras[0])
    media_pipe = MediaPiperDetector()
    if stream.is_connected():
        stream.start()

    while True:
        frame = stream.camera.frame
        if frame is not None and frame.size > 0:
            results = media_pipe.extract_face_info(cameras)
            media_pipe.draw_detections(cameras, results)
            cv2.imshow("Webcam", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        time.sleep(0.05)

    stream.camera.capture.release()
    cv2.destroyAllWindows()
    print("Stream closed.")

