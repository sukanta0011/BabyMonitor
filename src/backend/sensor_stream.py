import requests
import threading
import time
import logging
from datetime import datetime
from typing import Deque, Dict, Any
from dataclasses import dataclass
from .custom_wrappers import reconnect
from .custom_errors import ConnectionFailure
from ..global_variables import SHUTDOWN_EVENT
from .base_class import Stream


logger = logging.getLogger(__name__)


@dataclass
class Sensor:
    address: str
    data: Deque
    lock: threading.Lock
    is_active: bool = False
    thread: threading.Thread | None = None
    max_size: int = 50


class SensorStream(Stream):
    def __init__(self, sensor: Sensor):
        self.sensor = sensor

    def is_connected(self) -> bool:
        try:
            self._get_response(self.sensor.address, 5)
        except ConnectionFailure:
            logger.warning("Sensor stream is unreachable.")
            return False
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        self.sensor.is_active = True
        return True

    @reconnect(max_try=3, wait_time=5)
    def _get_response(self, address: str, timeout: int) -> Dict:
        return requests.get(url=address, timeout=timeout)

    def get_latest_data(self) -> Dict[Any, Any] | None:
        if not self.sensor.is_active:
            return None
        if len(self.sensor.data) == 0:
            return None
        with self.sensor.lock:
            latest_data = self.sensor.data[-1]
        return latest_data

    def start(self) -> None:
        self.sensor.thread = threading.Thread(
            target=self._continue_reading,
            args=(), daemon=True
        )
        self.sensor.thread.start()
        logger.info("Sensor streaming started.")

    def _continue_reading(self) -> None:
        consecutive_failures = 0
        failure_threshold = 3

        while not SHUTDOWN_EVENT.is_set():
            try:
                response = self._get_response(self.sensor.address, 5)
                if response.status_code != 500:
                    consecutive_failures = 0
                    with self.sensor.lock:
                        if len(self.sensor.data) > self.sensor.max_size:
                            self.sensor.data.popleft()
                        self.sensor.data.append(
                            {"time_stamp": datetime.now(),
                             "data": response.json()})
                else:
                    logger.warning(f"{response.text}")
            except ConnectionFailure:
                consecutive_failures += 1
                logger.warning("Sensor read failed ("
                      f"{consecutive_failures}/{failure_threshold})")
                if consecutive_failures >= failure_threshold:
                    self.sensor.is_active = False
                    logger.warning(
                        "Sensor considered offline — "
                        "waiting for rediscovery")
                    return

            time.sleep(10)

    def start_auto_connection_check(self, interval: int = 60) -> None:
        self.connection_checking_thread = threading.Thread(
            target=self._run_connection_checking_loop,
            args=(interval,), daemon=True
        )
        self.connection_checking_thread.start()

    def _run_connection_checking_loop(self, interval: int) -> None:
        while not SHUTDOWN_EVENT.is_set():
            if not self.sensor.is_active:
                logger.warning("Attempting to reconnect sensor at "
                      f"{self.sensor.address}...")
                if self.is_connected():
                    logger.info(f"Sensor at {self.sensor.address} "
                          "reconnected — restarting stream")
                    self.start()
            time.sleep(interval)
