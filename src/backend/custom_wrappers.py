from functools import wraps
import requests
import time
from typing import Callable
from .custom_errors import ConnectionFailure
import logging


logger = logging.getLogger(__name__)


def reconnect(max_try: int, wait_time: int) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_try):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.ConnectTimeout:
                    time.sleep(wait_time)
                    logger.warning(
                        "Sensor stream is unreachable. "
                        f"Reconnecting {i}/{max_try}...")
            raise ConnectionFailure(
                f"Connection remain unreachable after {max_try} attempts")
        return wrapper
    return decorator
