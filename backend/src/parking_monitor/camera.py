"""Aquisição e validação de JPEG no computador, sem classificação de vagas."""

from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic

import cv2
import httpx
import numpy as np
from numpy.typing import NDArray

from parking_monitor.settings import CameraSettings


class CameraError(Exception):
    """Erro de aquisição que não deve ser interpretado como vaga livre."""


class CameraUnavailableError(CameraError):
    """Falha de rede, timeout ou resposta HTTP de erro."""


class InvalidFrameError(CameraError):
    """Resposta não contém um JPEG completo e decodificável."""


@dataclass(frozen=True)
class CapturedFrame:
    jpeg: bytes
    bgr: NDArray[np.uint8]
    received_at: datetime
    duration_seconds: float

    @property
    def width(self) -> int:
        return self.bgr.shape[1]

    @property
    def height(self) -> int:
        return self.bgr.shape[0]


class CameraClient:
    """Cliente reutilizável; use como context manager para liberar conexões."""

    def __init__(
        self,
        base_url: str,
        settings: CameraSettings,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.url = base_url.rstrip("/") + settings.capture_path
        self._client = httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    def __enter__(self) -> "CameraClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def capture(self) -> CapturedFrame:
        started = monotonic()
        payload = bytearray()
        try:
            with self._client.stream(
                "GET", self.url, headers={"Accept": "image/jpeg", "Cache-Control": "no-cache"}
            ) as response:
                if response.status_code != 200:
                    raise CameraUnavailableError(
                        f"A câmera respondeu HTTP {response.status_code}; captura não salva."
                    )
                content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                if content_type != "image/jpeg":
                    raise InvalidFrameError("A resposta da câmera não é image/jpeg.")
                content_length = response.headers.get("content-length")
                if content_length is not None:
                    try:
                        declared_size = int(content_length)
                    except ValueError as exc:
                        raise InvalidFrameError("Content-Length inválido.") from exc
                    if not 0 < declared_size <= self.settings.max_frame_bytes:
                        raise InvalidFrameError("Tamanho declarado da captura fora do limite.")
                for chunk in response.iter_bytes(chunk_size=65536):
                    if len(payload) + len(chunk) > self.settings.max_frame_bytes:
                        raise InvalidFrameError("A captura excedeu max_frame_bytes.")
                    payload.extend(chunk)
        except httpx.TimeoutException as exc:
            raise CameraUnavailableError("Timeout ao solicitar imagem à ESP32-CAM.") from exc
        except httpx.RequestError as exc:
            raise CameraUnavailableError("Falha de comunicação com a ESP32-CAM.") from exc

        received_at = datetime.now(UTC)
        jpeg = bytes(payload)
        if not jpeg.startswith(b"\xff\xd8") or not jpeg.endswith(b"\xff\xd9"):
            raise InvalidFrameError("JPEG vazio, truncado ou com marcadores inválidos.")
        try:
            image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        except cv2.error as exc:
            raise InvalidFrameError("Falha ao decodificar JPEG com OpenCV.") from exc
        if image is None or image.size == 0:
            raise InvalidFrameError("O JPEG recebido não pôde ser decodificado.")
        return CapturedFrame(jpeg, image, received_at, monotonic() - started)
