import streamlit as st
import cv2
import time
from .backend.sensor_thresholds import (
    TEMPERATURE_THRESHOLD,
    HUMIDITY_THRESHOLD,
    CO2_THRESHOLD,
    LIGHT_THRESHOLD,
    SensorLevel
)
from .backend.camera_stream_manager import BestCameraStream, FaceDetectionStatus
from .backend.sensor_stream import SensorStream
from .global_variables import SHUTDOWN_EVENT


LEVEL_DISPLAY = {
    SensorLevel.ALERT_LOW: ("🔴", "inverse"),
    SensorLevel.LOW: ("🟡", "off"),
    SensorLevel.GOOD: ("🟢", "normal"),
    SensorLevel.HIGH: ("🟡", "off"),
    SensorLevel.ALERT_HIGH: ("🔴", "inverse"),
}


ALERT_MESSAGES = {
    "Light": {SensorLevel.ALERT_LOW: "Too dark", SensorLevel.ALERT_HIGH: "Too bright"},
    "CO2": {SensorLevel.ALERT_HIGH: "CO2 too high — ventilate room"},
    "Temperature": {SensorLevel.ALERT_LOW: "Room too cold", SensorLevel.ALERT_HIGH: "Room too hot"},
    "Humidity": {SensorLevel.ALERT_LOW: "Air too dry", SensorLevel.ALERT_HIGH: "Air too humid"},
}

def render_metric(placeholder_col, label, value, unit, threshold):
    if value == "—":
        placeholder_col.metric(label, "—")
        return None
    level = threshold.classify(value)
    icon, _ = LEVEL_DISPLAY[level]
    placeholder_col.metric(f"{icon} {label}", f"{value} {unit}")
    if level in (SensorLevel.ALERT_LOW, SensorLevel.ALERT_HIGH):
        return ALERT_MESSAGES[label][level]
    return None


def run_dashboard(best_stream: BestCameraStream, sensor_stream: SensorStream):
    st.set_page_config(page_title="Baby Monitor", layout="wide")
    st.title("Baby Monitor Dashboard")

    col1, col2 = st.columns([2, 1])

    with col1:
        video_placeholder = st.empty()
        status_placeholder = st.empty()

    with col2:
        sensor_placeholder = st.empty()

    
    while not SHUTDOWN_EVENT.is_set():
        with best_stream.lock:
            frame = best_stream.frame
            name = best_stream.name
            result = best_stream.result
            message = best_stream.message

        if frame is not None:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(
                frame_rgb, caption=f"Camera: {name}", channels="RGB"
            )
        else:
            video_placeholder.warning("Waiting for camera feed...")

        if message.status == FaceDetectionStatus.ERROR:
            status_placeholder.error(message.text)
        elif message.status == FaceDetectionStatus.WARNING:
            status_placeholder.warning(message.text)
        else:
            score = round(result.confidence_level, 2) if result else 0.0
            status_placeholder.success(f"Monitoring normally — confidence: {score}")

        try:
            latest = sensor_stream.get_latest_data()
            data = latest["data"]
            with sensor_placeholder.container():
                st.subheader("Sensor Readings")
                bh = data.get("bh1750", {})
                scd = data.get("scd40", {})
                temp = scd.get("temperature", "-")
                humidity = scd.get("humidity", "-")
                if isinstance(temp, float):
                    temp = round(temp, 1)
                if isinstance(humidity, float):
                    humidity = round(humidity, 1)
                alerts = []
                for msg in [
                    render_metric(st, "Light", bh.get("lux", "—"), "lux", LIGHT_THRESHOLD),
                    render_metric(st, "CO2", scd.get("co2", "—"), "ppm", CO2_THRESHOLD),
                    render_metric(st, "Temperature", temp, "°C", TEMPERATURE_THRESHOLD),
                    render_metric(st, "Humidity", humidity, "%", HUMIDITY_THRESHOLD),
                ]:
                    if msg:
                        alerts.append(msg)

                if alerts:
                    st.warning(" · ".join(alerts))
        except (IndexError, KeyError):
            sensor_placeholder.info("Waiting for sensor data...")

        time.sleep(0.1)
