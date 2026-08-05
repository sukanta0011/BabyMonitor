from src.backend.sensor_thresholds import Threshold, SensorLevel


class TestTemperatureThresholds:
    threshold = Threshold(
            alert_low=15, low=20,
            high=22.2, alert_high=30)

    def test_temperature_is_good(self):
        result = self.threshold.classify(21)
        assert result == SensorLevel.GOOD

    def test_temperature_is_low(self):
        result = self.threshold.classify(18)
        assert result == SensorLevel.LOW

    def test_temperature_is_very_low(self):
        result = self.threshold.classify(12)
        assert result == SensorLevel.ALERT_LOW

    def test_temperature_is_high(self):
        result = self.threshold.classify(28)
        assert result == SensorLevel.HIGH

    def test_temperature_is_very_high(self):
        result = self.threshold.classify(35)
        assert result == SensorLevel.ALERT_HIGH

    def test_temperature_is_low_edge(self):
        result = self.threshold.classify(15)
        assert result == SensorLevel.LOW
