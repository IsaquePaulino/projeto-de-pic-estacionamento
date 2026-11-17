"""Configuração validada, calibração e gravação atômica de arquivos locais."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Literal

import cv2
import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_json(path: Path, data: dict) -> None:
    atomic_write(path, (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def valid_polygon(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not 3 <= len(points) <= 12:
        raise ValueError("Selecione de 3 a 12 pontos.")
    polygon = np.asarray(points, dtype=np.float32)
    if not np.isfinite(polygon).all() or (polygon < 0).any() or (polygon > 1).any():
        raise ValueError("Os pontos devem estar dentro da imagem.")
    if cv2.contourArea(polygon) < 0.0005 or not cv2.isContourConvex(polygon):
        raise ValueError("A região deve formar um polígono convexo, sem cruzar lados.")
    return points


class MapRect(BaseModel):
    x: float = Field(ge=0, allow_inf_nan=False)
    y: float = Field(ge=0, allow_inf_nan=False)
    width: float = Field(gt=0, allow_inf_nan=False)
    height: float = Field(gt=0, allow_inf_nan=False)
    rotation_degrees: float = Field(default=0, allow_inf_nan=False)


class Spot(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    label: str = Field(min_length=1, max_length=80)
    camera_roi: list[tuple[float, float]] | None = None
    map_rect: MapRect
    initial_state: Literal["unknown"] = "unknown"
    led_index: int = Field(ge=0)

    @field_validator("camera_roi")
    @classmethod
    def check_roi(cls, value):
        return valid_polygon(value) if value is not None else None


class ImageCalibration(BaseModel):
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    roi_coordinates: Literal["normalized"] = "normalized"
    calibrated: bool = False

    @model_validator(mode="after")
    def paired_dimensions(self):
        if (self.width is None) != (self.height is None):
            raise ValueError("Informe largura e altura juntas.")
        if self.calibrated and self.width is None:
            raise ValueError("Calibração exige dimensões da imagem.")
        return self


class ParkingMap(BaseModel):
    width: float = Field(gt=0, allow_inf_nan=False)
    height: float = Field(gt=0, allow_inf_nan=False)
    background_image: str | None = None


class ParkingConfig(BaseModel):
    schema_version: Literal[1] = 1
    camera_image: ImageCalibration
    map: ParkingMap
    spots: list[Spot] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_spots(self):
        if len({spot.id for spot in self.spots}) != len(self.spots):
            raise ValueError("IDs das vagas devem ser únicos.")
        if len({spot.led_index for spot in self.spots}) != len(self.spots):
            raise ValueError("Índices dos LEDs devem ser únicos.")
        for spot in self.spots:
            rect = spot.map_rect
            if rect.x + rect.width > self.map.width or rect.y + rect.height > self.map.height:
                raise ValueError("Retângulo da vaga fora do mapa.")
            if spot.camera_roi is not None and self.camera_image.width is None:
                raise ValueError("ROIs exigem dimensões da câmera.")
        return self


class DetectionSettings(BaseModel):
    enabled: bool = False
    reference_image: str = "data/reference/empty.jpg"
    gaussian_blur_kernel: int = Field(default=5, ge=1, le=31)
    pixel_difference_threshold: int = Field(default=25, ge=1, le=254)
    free_max_changed_ratio: float = Field(default=0.08, ge=0, le=1, allow_inf_nan=False)
    occupied_min_changed_ratio: float = Field(default=0.18, gt=0, le=1, allow_inf_nan=False)
    confirmation_frames: int = Field(default=4, ge=1, le=50)
    max_global_changed_ratio: float = Field(default=0.65, gt=0, le=1, allow_inf_nan=False)
    max_illumination_shift: float = Field(default=45, gt=0, le=255, allow_inf_nan=False)
    chromatic_difference_threshold: float = Field(default=12, gt=0, le=255, allow_inf_nan=False)
    min_color_changed_ratio: float = Field(default=0.06, ge=0, le=1, allow_inf_nan=False)
    min_new_edge_ratio: float = Field(default=0.012, ge=0, le=1, allow_inf_nan=False)
    max_camera_shift_pixels: float = Field(default=3, gt=0, allow_inf_nan=False)
    analysis_interval_seconds: float = Field(default=0.3, gt=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def ordered_thresholds(self):
        if self.free_max_changed_ratio >= self.occupied_min_changed_ratio:
            raise ValueError("O limiar de livre deve ser menor que o de ocupado.")
        if self.gaussian_blur_kernel % 2 == 0:
            raise ValueError("O filtro gaussiano deve ter tamanho ímpar.")
        return self


class ConfigRepository:
    def __init__(self, root: Path):
        self.root = root
        self.parking_path = root / "config/parking.json"
        self.system_path = root / "config/system.json"
        self.system = json.loads(self.system_path.read_text(encoding="utf-8"))
        if not isinstance(self.system, dict) or self.system.get("schema_version") != 1:
            raise ValueError("Versão de system.json inválida.")
        self.parking = ParkingConfig.model_validate_json(
            self.parking_path.read_text(encoding="utf-8")
        )
        self.detection = DetectionSettings.model_validate(self.system["detection"])
        led_section = self.system.get("leds")
        colors = led_section.get("colors") if isinstance(led_section, dict) else None
        if not isinstance(colors, dict):
            raise ValueError("Configure as cores RGB dos LEDs simulados.")
        for state in ("free", "occupied", "unknown"):
            rgb = colors.get(state)
            if (
                not isinstance(rgb, list) or len(rgb) != 3
                or any(type(channel) is not int or not 0 <= channel <= 255 for channel in rgb)
            ):
                raise ValueError(f"Cor RGB inválida para {state}.")
        reference = (root / self.detection.reference_image).resolve()
        if not reference.is_relative_to((root / "data").resolve()):
            raise ValueError("A referência deve ficar na pasta data/.")
        self.reference_path = reference
        self.reference_metadata_path = reference.with_suffix(".json")

    def save_parking(self, parking: ParkingConfig) -> None:
        write_json(self.parking_path, parking.model_dump(mode="json"))
        self.parking = parking

    def save_detection(self, detection: DetectionSettings) -> None:
        data = {**self.system, "detection": detection.model_dump(mode="json")}
        write_json(self.system_path, data)
        self.system = data
        self.detection = detection

    def fingerprint(self, origin: str) -> str:
        data = {
            "origin": origin.rstrip("/"),
            "image": self.parking.camera_image.model_dump(),
            "regions": [(spot.id, spot.camera_roi) for spot in self.parking.spots],
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
