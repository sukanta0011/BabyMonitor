from __future__ import annotations
import numpy as np
from typing import List, Tuple, TYPE_CHECKING, Deque, Any
from abc import ABC, abstractmethod
from collections import deque
import cv2
from dataclasses import dataclass
if TYPE_CHECKING:
    from .camera_stream import Camera


@dataclass
class Result:
    face: bool
    face_region: Tuple = ()
    confidence_level: float = 0.0


class BoundingBoxSmoother:
    def __init__(self, window: int = 10) -> None:
        self.xs: Deque = deque(maxlen=window)
        self.ys: Deque = deque(maxlen=window)
        self.ws: Deque = deque(maxlen=window)
        self.hs: Deque = deque(maxlen=window)

    def update(
            self, x: int, y: int,
            w: int, h: int) -> None:
        self.xs.append(x)
        self.ys.append(y)
        self.ws.append(w)
        self.hs.append(h)

    def get_smooth(self) -> Tuple | None:
        if not self.xs:
            return None
        return (
            int(np.mean(self.xs)),
            int(np.mean(self.ys)),
            int(np.mean(self.ws)),
            int(np.mean(self.hs))
        )


class FaceDetector(ABC):
    def __init__(self, camera: Camera) -> None:
        self.camera = camera
        self.initialize_the_model()

    @abstractmethod
    def initialize_the_model(self) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def extract_face_info(self) -> List[Result]:
        pass


class MediaPiperDetector(FaceDetector):
    def initialize_the_model(self) -> None:
        # import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        base_options = python.BaseOptions(
            model_asset_path='face_detection_models/' +
            'blaze_face_full_range.tflite')
        options = vision.FaceDetectorOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE)
        self.detector = vision.FaceDetector.create_from_options(options)

    def close(self) -> None:
        self.detector.close()

    def extract_face_info(self) -> List[Result]:
        if self.camera.frame is None:
            return [Result(face=False)]
        rgb_frame = cv2.cvtColor(
            self.camera.frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        raw_info = self.detector.detect(mp_image)
        return self._store_face_info(raw_info)

    def _store_face_info(self, raw_info: Any) -> List[Result]:
        results: List[Result] = []
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
        camera = self.camera
        for result in results:
            if result.face:
                x_c, y_c = result.face_region.origin_x, \
                    result.face_region.origin_y
                width_c = result.face_region.width
                height_c = result.face_region.height
                camera.smoother.update(x_c, y_c, width_c, height_c)
                x, y, w, h = camera.smoother.get_smooth()

                cv2.rectangle(
                    camera.frame, (x, y), (x + w, y + h), (255, 0, 0), 1)
                cv2.putText(
                    camera.frame, str(round(result.confidence_level, 2)),
                    (x, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                # cv2.circle(
                #     camera.frame,
                #     (int(result.left_eye.x * camera.frame.shape[1]),
                #         int(result.left_eye.y * camera.frame.shape[0])),
                #         2, (255, 0, 0), 1)


class YuNetDetector(FaceDetector):
    def initialize_the_model(self) -> None:
        self.detector = cv2.FaceDetectorYN.create(
            model='face_detection_models/face_detection_yunet_2023mar.onnx',
            config='',
            input_size=(320, 320),
            score_threshold=0.6,
            nms_threshold=0.3,
            top_k=5000
        )

    def close(self) -> None:
        pass

    def extract_face_info(self) -> List[Result]:
        if self.camera.frame is None:
            return [Result(face=False)]

        frame = self.camera.frame
        h, w = frame.shape[:2]
        self.detector.setInputSize((w, h))

        _, faces = self.detector.detect(frame)
        if faces is None:
            return [Result(face=False)]

        results: List[Result] = []
        for face in faces:
            x, y, box_w, box_h = face[0:4].astype(int)
            confidence = float(face[14])
            results.append(Result(
                face=True,
                face_region=(x, y, box_w, box_h),
                confidence_level=confidence,
            ))
        return results


if __name__ == "__main__":
    pass
