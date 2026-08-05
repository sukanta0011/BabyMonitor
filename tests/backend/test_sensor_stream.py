from unittest.mock import patch, Mock
import requests
from src.backend.sensor_stream import Sensor, SensorStream
import threading
from collections import deque


class TestSensorStream:
    sensor = Sensor(
        address="http://example.local,",
        data=deque(), lock=threading.Lock())
    stream = SensorStream(sensor)

    def test_is_connected_connection_error(self):
        with patch("src.backend.sensor_stream.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectTimeout
            result = self.stream.is_connected()
        assert result is False

    def test_is_connected_connection_ok(self):
        mock_response = Mock()
        mock_response.status_code = 200
        with patch("src.backend.sensor_stream.requests.get") as mock_get:
            mock_get.return_value = mock_response
            result = self.stream.is_connected()
        assert result is True
