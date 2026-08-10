from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict
from .models import SensorsReadings, ErrorMessage


class SensorDataOperations:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: SensorsReadings) -> SensorsReadings:
        self.session.add(data)
        await self.session.commit()
        await self.session.refresh(data)
        return data

    async def get_recent_readings(session: AsyncSession, limit: int = 100):
        result = await session.execute(
            select(SensorsReadings)
            .order_by(SensorsReadings.time_stamp.desc())
            .limit(limit)
        )
        return result.scalars().all()


class ErrorMessageOperation:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, msg: str) -> int:
        err_msg = ErrorMessage(msg=msg)
        self.session.add(err_msg)
        await self.session.commit()
        await self.session.refresh(err_msg)
        return err_msg.id

    async def get_id(self, msg: str) -> int | None:
        result = await self.session.execute(
            select(ErrorMessage.id).where(ErrorMessage.msg == msg))
        return result.scalar_one_or_none()


class DataManager:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.sensor_readings = SensorDataOperations(session)
        self.error_msg = ErrorMessageOperation(session)

    async def save_data(self, data: Dict) -> SensorsReadings:
        transformed_data = await self.transform_data(data)
        await self.sensor_readings.create(transformed_data)
        return transformed_data

    async def transform_data(self, data: Dict) -> SensorsReadings:
        reading = SensorsReadings()
        await self._apply_sensor(
            reading, data.get("scd40"),
            value_map={"co2_level": "co2",
                       "temperature": "temperature",
                       "humidity": "humidity"},
            status_field="co2_sensor_status",
            msg_field="co2_sensor_msg_id")
        await self._apply_sensor(
            reading, data.get("bh1750"),
            value_map={"light_intensity": "lux"},
            status_field="light_sensor_status",
            msg_field="light_sensor_msg_id")
        return reading

    async def _apply_sensor(
            self, reading, sensor_data, value_map, status_field, msg_field):
        if sensor_data is None:
            return
        status = sensor_data.get("status")
        setattr(reading, status_field, status)
        if status == "on":
            for reading_field, json_key in value_map.items():
                setattr(reading, reading_field, sensor_data.get(json_key))
        else:
            msg = sensor_data.get("error")
            msg_id = await self.error_msg.get_id(msg)
            if msg_id is None:
                msg_id = await self.error_msg.create(msg)
            setattr(reading, msg_field, msg_id)
