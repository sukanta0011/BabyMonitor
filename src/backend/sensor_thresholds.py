from enum import Enum
from dataclasses import dataclass


class SensorLevel(Enum):
    ALERT_LOW = "alert_low"
    LOW = "low"
    GOOD = "good"
    HIGH = "high"
    ALERT_HIGH = "alert_high"


@dataclass(frozen=True)
class Threshold:
    alert_low: float | None
    low: float | None
    high: float | None
    alert_high: float | None

    def classify(self, value: float) -> SensorLevel:
        if self.alert_low is not None and value < self.alert_low:
            return SensorLevel.ALERT_LOW
        if self.low is not None and value < self.low:
            return SensorLevel.LOW
        if self.alert_high is not None and value > self.alert_high:
            return SensorLevel.ALERT_HIGH
        if self.high is not None and value > self.high:
            return SensorLevel.HIGH
        return SensorLevel.GOOD


TEMPERATURE_THRESHOLD = Threshold(alert_low=15, low=20, high=22.2, alert_high=30)
HUMIDITY_THRESHOLD = Threshold(alert_low=30, low=40, high=60, alert_high=70)
CO2_THRESHOLD = Threshold(alert_low=None, low=None, high=1000, alert_high=1500)
LIGHT_THRESHOLD = Threshold(alert_low=None, low=10, high=500, alert_high=None)