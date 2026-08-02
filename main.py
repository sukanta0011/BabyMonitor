import cv2
from dataclasses import dataclass
import numpy as np
import time
import threading
from collections import deque
from typing import List
from src.global_variables import *
from src.backend.helper_functions import merge_frames_horizontally, merge_image_by_resizing, print_message
from src.backend.camera_stream import Camera, CameraStream
from src.backend.sensor_stream import Sensor, SensorStream
from src.backend.camera_stream_manager import FaceDetectionStatus


camera_data_lock = threading.Lock()
sensor_data_lock = threading.Lock()


CAMERAS = [
    Camera(ip=CAM1, name="cam1", lock=camera_data_lock, event=threading.Event()),
    # Camera(ip=CAM2, name="s3_cam1", lock=camera_data_lock, event=threading.Event()),
    Camera(ip="webcam", name="webcam", lock=camera_data_lock,event=threading.Event()),
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


from src.backend.face_detector import MediaPiperDetector
from src.backend.camera_stream_manager import CameraStreamManager, BestCameraStream

def start_best_camera_feed():
    working_streams = start_streaming()
    if len(working_streams) == 0:
        return
    face_detectors = [MediaPiperDetector(stream) for stream in working_streams]
    best_stream = BestCameraStream()
    stream_manager = CameraStreamManager(face_detectors, best_stream)

    stream_manager.start_camera_feed()
    try:
        while True:
            if best_stream.index is not None:
                with best_stream.lock:
                    frame = best_stream.frame
                cv2.imshow("ESP32-CAM Baby Monitor Feed", frame)

            if (cv2.waitKey(1) & 0xFF == ord('q')) or\
                    best_stream.detection_failure_event.is_set():
                SHUTDOWN_EVENT.set()
                break
            # time.sleep(1)
    except KeyboardInterrupt as e:
        print(f"Keyboard Interrupt: {e}")
    finally:
        SHUTDOWN_EVENT.set()
        stream_manager.stop_camera_feed()
        for stream in working_streams:
            stream.camera.capture.release()
        for detector in face_detectors:
            detector.close()
        cv2.destroyAllWindows()
        print("Stream closed.")

from src.streamlit_dashboard import run_dashboard

def start_dashboard():
    working_streams = []
    face_detectors = []
    stream_manager = None
    try:
        working_streams = start_streaming()
        if len(working_streams) == 0:
            return
        face_detectors = [MediaPiperDetector(stream) for stream in working_streams]
        best_stream = BestCameraStream()
        stream_manager = CameraStreamManager(face_detectors, best_stream)

        sensor_stream = SensorStream(SENSOR)
        if sensor_stream.is_connected():
            sensor_stream.start()

        stream_manager.start_camera_feed()
        run_dashboard(best_stream=best_stream, sensor_stream=sensor_stream)
    except RuntimeError as e:
        print_message(e)
    except KeyboardInterrupt as e:
        print_message(e)
    finally:
        print_message("Triggering Shutdown event...")
        SHUTDOWN_EVENT.set()
        if stream_manager is not None:
            stream_manager.stop_camera_feed()
        # for detector in face_detectors:
        #     detector.close()
        for stream in working_streams:
            stream.camera.capture.release()
        print("sensor stream stopped")


if __name__ == "__main__":
    # start_all_camera_feed()
    # start_best_camera_feed()
    start_dashboard()
