from sqlalchemy import (
    DateTime, Column,
    Integer, Float,
    String, ForeignKey)
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

    co2_sensor_msg_id = Column(Integer, ForeignKey("error_message.id"))
    light_sensor_msg_id = Column(Integer, ForeignKey("error_message.id"))


class ErrorMessage(Base):
    __tablename__ = "error_message"
    id = Column(Integer, primary_key=True)
    msg = Column(String(200), unique=True)
