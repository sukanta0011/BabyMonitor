import requests
import threading
import time
from datetime import datetime
from typing import Deque, Dict, Any
from dataclasses import dataclass
from .custom_wrappers import reconnect
from .custom_errors import ConnectionFailure
from ..global_variables import SHUTDOWN_EVENT


@dataclass
class Sensor:
    address: str
    data: Deque
    lock: threading.Lock
    thread: threading.Thread | None = None
    max_size: int = 50


class SensorStream:
    def __init__(self, sensor: Sensor):
        self.sensor = sensor
        self.connected = False

    def is_connected(self) -> bool:
        try:
            self._get_response(self.sensor.address, 5)
        except ConnectionFailure:
            print("Sensor stream is unreachable.")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False
        self.connected = True
        return True

    @reconnect(max_try=5, wait_time=5)
    def _get_response(self, address: str, timeout: int) -> Dict:
        response = requests.get(url=address, timeout=timeout)
        if not response:
            self.connected = False
        return response

    def get_latest_data(self) -> Dict[Any, Any] | None:
        if not self.connected:
            return
        with self.sensor.lock:
            latest_data = self.sensor.data[-1]
        return latest_data

    def start(self) -> None:
        self.sensor.thread = threading.Thread(
            target=self._continue_reading,
            args=(), daemon=True
        )
        self.sensor.thread.start()
        print("Sensor streaming started.")

    def _continue_reading(self) -> None:
        while not SHUTDOWN_EVENT.is_set():
            try:
                response = self._get_response(self.sensor.address, 5)
                if response.status_code != 500:
                    with self.sensor.lock:
                        if len(self.sensor.data) > self.sensor.max_size:
                            self.sensor.data.popleft()
                        self.sensor.data.append(
                            {"time_stamp": datetime.now(),
                             "data": response.json()})
                else:
                    print(f"{response.text}")
            except ConnectionFailure:
                pass

            time.sleep(10)
