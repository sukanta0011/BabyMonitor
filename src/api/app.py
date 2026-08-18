from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import cv2
from typing import Dict
import asyncio
from ..global_variables import SHUTDOWN_EVENT, CAMERAS
from src.main import SENSOR
from ..backend.face_detector import YuNetDetector
from ..backend.camera_stream_manager import (
    CameraStreamManager, BestCameraStream)
from ..backend.camera_stream import Camera
from src.backend.sensor_stream import SensorStream
from fastapi.responses import FileResponse
from ..db.table_operations import TableOperationManager
from ..db.session import engine
from ..db.models import Base
from ..backend.alerts import start_sensor_alerts


async def generate_best_frame(best_frame: BestCameraStream):
    while not SHUTDOWN_EVENT.is_set():
        with best_frame.lock:
            index = best_frame.index
        if index is not None:
            with best_frame.lock:
                frame = best_frame.encoded_frame
            if frame is not None:
                yield frame
        await asyncio.sleep(0.1)


async def generate_camera_frame(camera: Camera):
    while not SHUTDOWN_EVENT.is_set():
        with camera.lock:
            frame = camera.frame
        if frame is not None:
            success, buffer = cv2.imencode(".jpg", frame)
            if success:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       buffer.tobytes() + b'\r\n')
        await asyncio.sleep(0.1)


async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # working_streams = start_streaming()
    app.state.best_frame = BestCameraStream()
    app.state.sensor_stream = SensorStream(SENSOR)
    stream_manager = None

    stream_manager = CameraStreamManager(
        CAMERAS, YuNetDetector, app.state.best_frame)
    stream_manager.start_auto_connection_check()
    stream_manager.start_camera_feed()
    # else:
    #     print("Warning: no working cameras found — starting without video")

    app.state.sensor_stream.start_auto_connection_check()
    asyncio.create_task(
        TableOperationManager.start_saving_in_db(
            app.state.sensor_stream)
        )
    asyncio.create_task(start_sensor_alerts(
        app.state.sensor_stream
    ))
    yield

    SHUTDOWN_EVENT.set()
    if stream_manager is not None:
        stream_manager.stop_camera_feed()
    for camera in CAMERAS:
        if camera.is_active:
            camera.capture.release()


app = FastAPI(
    title="Baby Monitor",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def index():
    return FileResponse("src/api/static/index.html")


@app.get("/health")
async def health_check() -> Dict:
    return {"status": "ok"}


@app.get("/video")
async def get_best_view(request: Request) -> StreamingResponse:
    best_frame = request.app.state.best_frame
    return StreamingResponse(
        generate_best_frame(best_frame),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/frame_info")
async def get_best_viewer_info(request: Request):
    best_frame: BestCameraStream = request.app.state.best_frame
    with best_frame.lock:
        frame_info = {
            "name": best_frame.name,
            "score": round(best_frame.result.confidence_level, 2)
            if best_frame.result else 0.0,
            "status": best_frame.message.status,
            "message": best_frame.message.text
        }
    return JSONResponse(content=frame_info)


@app.get("/sensors")
async def get_sensor_data(request: Request):
    sensor_stream: SensorStream = request.app.state.sensor_stream
    latest = sensor_stream.get_latest_data()
    if latest:
        return JSONResponse(content=latest.get('data'))


@app.get("/cameras")
async def get_cameras():
    cams = []
    for camera in CAMERAS:
        with camera.lock:
            cams.append({
                "name": camera.name,
                "ip": camera.ip,
                "state": camera.is_active
            })
    return JSONResponse(content=cams)


@app.get("/video/{camera_name}")
async def get_camera_view(camera_name: str):
    camera = next(
        (c for c in CAMERAS if c.name == camera_name), None)
    if camera is None:
        return JSONResponse(
            status_code=404, content={"error": "camera not found"})
    return StreamingResponse(
        generate_camera_frame(camera),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )