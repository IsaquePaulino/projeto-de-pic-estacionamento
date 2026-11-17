"""API local, vídeo MJPEG e tela de calibração/teste de ocupação."""

import asyncio
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from parking_monitor.configuration import valid_polygon
from parking_monitor.monitor import ParkingMonitor
from parking_monitor.settings import PROJECT_ROOT, NetworkSettings


class RoiRequest(BaseModel):
    points: list[tuple[float, float]]
    width: int = Field(gt=0)
    height: int = Field(gt=0)

    @field_validator("points")
    @classmethod
    def check_points(cls, points):
        return valid_polygon(points)


class ReferenceRequest(BaseModel):
    confirm_empty: bool = False


class DetectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool | None = None
    pixel_difference_threshold: Annotated[int | None, Field(ge=1, le=254)] = None
    free_max_changed_ratio: Annotated[float | None, Field(ge=0, le=1, allow_inf_nan=False)] = None
    occupied_min_changed_ratio: Annotated[float | None, Field(gt=0, le=1, allow_inf_nan=False)] = None
    confirmation_frames: Annotated[int | None, Field(ge=1, le=50)] = None


async def video_chunks(monitor: ParkingMonitor):
    sequence = -1
    while not monitor.stop_event.is_set():
        frame = monitor.video_frame()
        if frame is None:
            return
        current, jpeg = frame
        if current != sequence:
            sequence = current
            yield (
                b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                + str(len(jpeg)).encode()
                + b"\r\n\r\n" + jpeg + b"\r\n"
            )
        await asyncio.sleep(0.03)


def create_app(monitor: ParkingMonitor | None = None, *, start_acquisition: bool = True):
    @asynccontextmanager
    async def lifespan(application):
        service = monitor
        if service is None:
            network = NetworkSettings()
            service = ParkingMonitor(PROJECT_ROOT, str(network.esp32_base_url))
        application.state.monitor = service
        if start_acquisition:
            service.start()
        try:
            yield
        finally:
            if start_acquisition:
                await asyncio.to_thread(service.stop)

    application = FastAPI(title="Projeto de PIC Estacionamento", lifespan=lifespan)

    def service(request: Request) -> ParkingMonitor:
        return request.app.state.monitor

    @application.get("/", include_in_schema=False)
    def index():
        return FileResponse(PROJECT_ROOT / "frontend/index.html", headers={"Cache-Control": "no-store"})

    @application.get("/api/status")
    def status(request: Request):
        return service(request).status()

    @application.get("/api/frame.jpg")
    def snapshot(request: Request):
        try:
            jpeg, width, height = service(request).snapshot_frame()
        except ValueError as exc:
            raise HTTPException(503, str(exc)) from exc
        return Response(
            jpeg, media_type="image/jpeg",
            headers={"Cache-Control": "no-store", "X-Frame-Width": str(width), "X-Frame-Height": str(height)},
        )

    @application.get("/api/video")
    def video(request: Request):
        monitor = service(request)
        if monitor.video_frame() is None:
            raise HTTPException(503, "Câmera sem imagem recente.")
        return StreamingResponse(
            video_chunks(monitor),
            media_type="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    @application.put("/api/spots/{identifier}/roi")
    def save_roi(identifier: str, payload: RoiRequest, request: Request):
        try:
            return service(request).save_roi(
                identifier, payload.points, payload.width, payload.height
            )
        except KeyError as exc:
            raise HTTPException(404, "Vaga não encontrada.") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except OSError as exc:
            raise HTTPException(500, "Não foi possível salvar a calibração no computador.") from exc

    @application.post("/api/reference")
    def reference(payload: ReferenceRequest, request: Request):
        try:
            return service(request).save_reference(payload.confirm_empty)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except OSError as exc:
            raise HTTPException(500, "Não foi possível salvar a referência no computador.") from exc

    @application.put("/api/detection")
    def configure(payload: DetectionRequest, request: Request):
        try:
            return service(request).configure_detection(payload.model_dump(exclude_none=True))
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except OSError as exc:
            raise HTTPException(500, "Não foi possível salvar os parâmetros de análise.") from exc

    application.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "frontend/assets"), name="assets")
    return application


app = create_app()
