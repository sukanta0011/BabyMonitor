import cv2
import logging
import numpy as np
from typing import Tuple, Callable
from ..global_variables import SHUTDOWN_EVENT


logger = logging.getLogger(__name__)


def merge_image_using_padding(frames: Tuple[np.ndarray, ...]) -> np.ndarray:
    target_h = max([frame.shape[0] for frame in frames])

    final_frame = frames[0]
    if final_frame.shape[0] != target_h:
        final_frame = np.pad(
            final_frame, ((0, target_h - frames[0].shape[0]),
                          (0, 0), (0, 0)), mode='constant', constant_values=0)

    for i in range(1, len(frames)):
        if target_h == frames[i].shape[0]:
            final_frame = np.hstack((final_frame, frames[i]))
        else:
            masked_frame = np.pad(
                frames[i], ((0, target_h - frames[i].shape[0]),
                            (0, 0), (0, 0)),
                mode='constant', constant_values=0)
            final_frame = np.hstack((final_frame, masked_frame))
    return final_frame


def merge_image_by_resizing(frames: Tuple[np.ndarray, ...]) -> np.ndarray:
    target_h = max([frame.shape[0] for frame in frames])

    resized_frames = [cv2.resize(
        frame, (
            int(target_h * frame.shape[1]/frame.shape[0]),
            target_h)) for frame in frames]
    # print(f"resized_images:
    # {int(target_h * frames[1].shape[1]/frames[1].shape[0])}, {target_h}")
    return merge_image_using_padding(tuple(resized_frames))


def merge_frames_horizontally(frames: Tuple[np.ndarray, ...],
                              method: Callable) -> np.ndarray:
    if len(frames) == 0:
        raise ValueError("No frames received for merging")
    final_frame = method(frames)
    return final_frame


# def print_message(message: str) -> None:
#     if not SHUTDOWN_EVENT.is_set():
#         with PRINT_LOCK:
#             print(message)
