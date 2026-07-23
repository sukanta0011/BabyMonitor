import cv2
from dataclasses import dataclass
import numpy as np
import time
import threading
from collections import deque
from typing import List
from .global_variables import *
from .helper_functions import merge_frames_horizontally, merge_image_by_resizing
from .camera_stream import Camera, CameraStream
from .sensor_stream import Sensor, SensorStream


camera_data_lock = threading.Lock()
sensor_data_lock = threading.Lock()


CAMERAS = [
    Camera(ip=CAM1, name="camera1", lock=camera_data_lock, event=threading.Event()),
    Camera(ip=CAM2, name="camera2", lock=camera_data_lock, event=threading.Event()),
    Camera(ip="webcam", name="camera2", lock=camera_data_lock,event=threading.Event()),
]
SENSOR = Sensor(
    address=SENSORS, data=deque(), lock=sensor_data_lock)

def start_streaming() -> List[CameraStream]:
    streams = [CameraStream(camera) for camera in CAMERAS]
    working_streams  = []
    for stream in streams:
        if stream.is_connected():
            stream.start()
            working_streams.append(stream)
    if len(working_streams) == 0:
        print(f"There no active cameras at this moment")
    return working_streams


def start_all_camera_feed():
    working_streams = start_streaming()
    if len(working_streams) == 0:
        return

    while True:
        # Display the live frame in a desktop window
        with camera_data_lock:
            frames = tuple(stream.camera.frame for stream in working_streams)
        if any(f is None for f in frames):
            continue
        frame = merge_frames_horizontally(
            frames, merge_image_by_resizing)
        cv2.imshow("ESP32-CAM Baby Monitor Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        time.sleep(0.05)

    for stream in working_streams:
        stream.camera.capture.release()
    cv2.destroyAllWindows()
    print("Stream closed.")


from .face_detector import MediaPiperDetector
from .camera_stream_manager import CameraStreamManager, BestCameraStream

def start_best_camera_feed():
    working_streams = start_streaming()
    if len(working_streams) == 0:
        return
    face_detectors = [MediaPiperDetector(stream) for stream in working_streams]
    best_stream = BestCameraStream()
    stream_manager = CameraStreamManager(face_detectors, best_stream)
    while True:
        stream_manager.start_camera_feed()
        if best_stream.best_camera_index:
            frame = CAMERAS[best_stream.best_camera_index].frame
            if frame:
                cv2.imshow("ESP32-CAM Baby Monitor Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        time.sleep(0.05)

    for stream in working_streams:
        stream.camera.capture.release()
    cv2.destroyAllWindows()
    print("Stream closed.")


if __name__ == "__main__":
    start_best_camera_feed()