from sqlalchemy import DateTime, Column, Integer, Float, String, Enum
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


class SensorsReadings(Base):
    __tablename__ = "sensors_results"
    id = Column(Integer, primary_key=True)
    time_stamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=timezone.utc),
        index=True)
    co2_level = Column(Integer)
    temperature = Column(Float)
    humidity = Column(Float)
    light_intensity = Column(Integer)
    co2_sensor_status = Column(String, nullable=False)
    light_sensor_status = Column(String, nullable=False)
    co2_sensor_message = Column(String)
    light_sensor_message = Column(String)
