"""Carregamento apenas das configurações necessárias à aquisição da Etapa 2."""

import json
from pathlib import Path

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class NetworkSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    esp32_base_url: AnyHttpUrl

    @field_validator("esp32_base_url")
    @classmethod
    def validate_origin(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.username or value.password or value.query or value.fragment:
            raise ValueError("Informe somente a origem HTTP, sem credenciais ou parâmetros.")
        if value.path not in (None, "/"):
            raise ValueError("A URL deve conter somente host e porta, sem /capture.")
        return value


class CameraSettings(BaseModel):
    capture_path: str = "/capture"
    poll_interval_seconds: float = Field(default=0.5, gt=0, allow_inf_nan=False)
    request_timeout_seconds: float = Field(default=2.0, gt=0, allow_inf_nan=False)
    stale_after_seconds: float = Field(default=5.0, gt=0, allow_inf_nan=False)
    max_frame_bytes: int = Field(default=2_000_000, gt=0)
    preview_interval_seconds: float = Field(default=0.1, gt=0, allow_inf_nan=False)

    @field_validator("capture_path")
    @classmethod
    def validate_capture_path(cls, value: str) -> str:
        if not value.startswith("/") or value.startswith("//") or "?" in value or "#" in value:
            raise ValueError("capture_path deve ser um caminho absoluto HTTP simples.")
        return value


def load_camera_settings(path: Path | None = None) -> CameraSettings:
    """Lê a seção camera, sem ativar detector ou controlar estados/LEDs."""
    config_path = path if path is not None else PROJECT_ROOT / "config/system.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Versão de config/system.json inválida.")
    section = data.get("camera")
    if not isinstance(section, dict):
        raise ValueError("Seção camera ausente ou inválida em config/system.json.")
    return CameraSettings.model_validate(section)
