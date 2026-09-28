from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
import cv2
from typing import Dict
import asyncio
import httpx
from urllib.parse import urlparse
from fastapi import Path
from ..global_variables import SHUTDOWN_EVENT, CAMERAS, SENSOR
# from src.main import SENSOR
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
from ..logger_config import setup_logging


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
            success, buffer = cv2.imencode(
                ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            if success:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' +
                       buffer.tobytes() + b'\r\n')
        await asyncio.sleep(0.1)


async def lifespan(app: FastAPI):
    setup_logging()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # working_streams = start_streaming()
    app.state.best_frame = BestCameraStream()
    app.state.sensor_stream = SensorStream(SENSOR)
    stream_manager = None

    stream_manager = CameraStreamManager(
        CAMERAS, YuNetDetector, app.state.best_frame, 0.4)
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
        if camera.is_active and camera.capture:
            camera.capture.release()


app = FastAPI(
    title="Baby Monitor",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def index() -> FileResponse:
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
async def get_best_viewer_info(request: Request) -> JSONResponse:
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
async def get_sensor_data(request: Request) -> JSONResponse:
    sensor_stream: SensorStream = request.app.state.sensor_stream
    latest = sensor_stream.get_latest_data()
    if latest:
        return JSONResponse(content=latest.get('data'))
    return JSONResponse(content={})


@app.get("/cameras")
async def get_cameras() -> JSONResponse:
    cams = []
    for camera in CAMERAS:
        with camera.lock:
            cams.append({
                "name": camera.name,
                "ip": camera.ip,
                "state": camera.is_active
            })
    return JSONResponse(content=cams)


@app.get("/video/{camera_name}", response_model=None)
async def get_camera_view(
    camera_name: str) -> JSONResponse | StreamingResponse:
    camera = next(
        (c for c in CAMERAS if c.name == camera_name), None)
    if camera is None:
        return JSONResponse(
            status_code=404, content={"error": "camera not found"})
    return StreamingResponse(
        generate_camera_frame(camera),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


def resolve_camera_host(camera_name: str):
    """Returns (host, None) on success, or (None, JSONResponse) on failure."""
    camera = next((c for c in CAMERAS if c.name == camera_name), None)
    if camera is None:
        return None, JSONResponse(
            status_code=404, content={"error": "camera not found"})
    with camera.lock:
        online = camera.is_active
    if not online:
        return None, JSONResponse(
            status_code=503, content={"error": "camera offline"})
    host = urlparse(camera.ip).hostname
    if host is None:
        return None, JSONResponse(
            status_code=400, content={"error": "no network address"})
    return host, None


async def call_camera_ir(host: str, params: dict | None = None):
    """Returns (response, None) or (None, JSONResponse)."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"http://{host}/ir", params=params)
    except httpx.TimeoutException:
        return None, JSONResponse(
            status_code=504, content={"error": "camera timed out"})
    except httpx.RequestError:
        return None, JSONResponse(
            status_code=502, content={"error": "camera unreachable"})
    if resp.status_code != 200:
        return None, JSONResponse(
            status_code=502, content={"error": "camera rejected request"})
    return resp, None


@app.post("/ir/{camera_name}/{intensity}")
async def set_ir_intensity(
    camera_name: str,
    intensity: int = Path(ge=0, le=255),
):
    host, err = resolve_camera_host(camera_name)
    if host is None:
        return err

    resp, err = await call_camera_ir(
        host=host, params={"intensity": intensity})
    if err:
        return err

    return JSONResponse(
        content={"camera": camera_name, "intensity": intensity})


@app.get("/ir/{camera_name}")
async def get_ir_intensity(camera_name: str):
    host, err = resolve_camera_host(camera_name)
    if err:
        return err
    resp, err = await call_camera_ir(host)
    if err:
        return err
    try:
        level = int(resp.json()["intensity"])
    except (ValueError, KeyError, TypeError):
        return JSONResponse(
            status_code=502, content={"error": "bad reply from camera"})
    return JSONResponse(
        content={"camera": camera_name, "intensity": level})
