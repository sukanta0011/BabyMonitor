from ..backend.sensor_stream import SensorStream
from ..global_variables import SHUTDOWN_EVENT
import asyncio
from ..backend.sensor_thresholds import LIGHT_THRESHOLD, SensorLevel


async def start_sensor_alerts(
        sensor_stream: SensorStream,
        interval: int = 10
        ) -> None:
    while not SHUTDOWN_EVENT.is_set():
        latest_data = sensor_stream.get_latest_data()
        if latest_data is not None:
            light_sensor = latest_data.get("bh1750")
            if light_sensor:
                lux = light_sensor.get("lux")
                threshold = LIGHT_THRESHOLD.classify(lux)
                if threshold == SensorLevel.ALERT_HIGH:
                    print("Alert: Too much light in the room.")
        await asyncio.sleep(interval)
