import cv2
from dataclasses import dataclass
import numpy as np
import time
import threading
from .global_variables import *
from .helper_functions import merge_frames_horizontally, merge_image_by_resizing
from .camera_stream import Camera, CameraStream


global_lock = threading.Lock()


CAMERAS = [
    Camera(ip=CAM1, name="camera1", lock=global_lock),
    Camera(ip=CAM2, name="camera2", lock=global_lock),
]


def main():
    streams = [CameraStream(camera) for camera in CAMERAS]
    working_streams  = []
    for stream in streams:
        if stream.is_connected():
            stream.start()
            working_streams.append(stream)
    if len(working_streams) == 0:
        print(f"There no active cameras at this moment")
        return

    while True:
        # Display the live frame in a desktop window
        with global_lock:
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

if __name__ == "__main__":
    main()