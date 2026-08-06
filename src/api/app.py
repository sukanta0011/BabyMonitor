from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict
import asyncio
from ..global_variables import SHUTDOWN_EVENT
from main import start_streaming, SENSOR
from ..backend.face_detector import MediaPiperDetector
from ..backend.camera_stream_manager import (
    CameraStreamManager, BestCameraStream)
from src.backend.sensor_stream import SensorStream
from fastapi.responses import FileResponse


async def generate_frame(best_frame: BestCameraStream):
    while not SHUTDOWN_EVENT.is_set():
        with best_frame.lock:
            index = best_frame.index
        if index is not None:
            with best_frame.lock:
                frame = best_frame.encoded_frame
            if frame is not None:
                yield(frame)
        await asyncio.sleep(0.1)


async def lifespan(app: FastAPI):
    working_streams = start_streaming()
    app.state.best_frame = BestCameraStream()
    app.state.sensor_stream = SensorStream(SENSOR)
    stream_manager = None

    if len(working_streams) > 0:
        face_detectors = [MediaPiperDetector(stream) for stream in working_streams]
        stream_manager = CameraStreamManager(face_detectors, app.state.best_frame)
        stream_manager.start_camera_feed()
    else:
        print("Warning: no working cameras found — starting without video")

    if app.state.sensor_stream.is_connected():
        app.state.sensor_stream.start()

    yield

    SHUTDOWN_EVENT.set()
    if stream_manager is not None:
        stream_manager.stop_camera_feed()
    for stream in working_streams:
        stream.camera.capture.release()


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
        generate_frame(best_frame),
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
