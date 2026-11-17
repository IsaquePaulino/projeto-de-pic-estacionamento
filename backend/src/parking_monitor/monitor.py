"""Uma aquisição compartilhada entre vídeo, calibração e detector no computador."""

import hashlib
import json
import logging
import threading
from collections import deque
from pathlib import Path
from time import monotonic

import cv2
import numpy as np

from parking_monitor.camera import CameraClient, CameraError, CapturedFrame
from parking_monitor.configuration import (
    ConfigRepository,
    DetectionSettings,
    ImageCalibration,
    ParkingConfig,
    atomic_write,
    valid_polygon,
    write_json,
)
from parking_monitor.detection import OccupancyDetector
from parking_monitor.settings import CameraSettings

logger = logging.getLogger(__name__)


class ParkingMonitor:
    def __init__(self, root: Path, origin: str, *, camera_factory=None, clock=monotonic):
        self.root = root
        self.origin = origin.rstrip("/")
        self.repository = ConfigRepository(root)
        self.camera_settings = CameraSettings.model_validate(self.repository.system["camera"])
        self.clock = clock
        self.camera_factory = camera_factory or (
            lambda: CameraClient(self.origin, self.camera_settings)
        )
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None
        self.frame: CapturedFrame | None = None
        self.frame_sequence = 0
        self.last_frame_time = None
        self.last_analysis_time = None
        self.camera_error = "Aguardando a primeira imagem."
        self.frame_times = deque(maxlen=60)
        self.reference_note = "Capture uma referência com as vagas vazias."
        self.detector = self._new_detector()
        self.simulated_leds = {}
        self._load_reference()

    def _new_detector(self):
        return OccupancyDetector(
            self.repository.parking,
            self.repository.detection,
            self.camera_settings.stale_after_seconds,
        )

    def _load_reference(self):
        try:
            metadata = json.loads(self.repository.reference_metadata_path.read_text(encoding="utf-8"))
            if not isinstance(metadata, dict):
                raise ValueError("Metadados da referência inválidos.")
            jpeg = self.repository.reference_path.read_bytes()
            if metadata.get("schema_version") != 1:
                raise ValueError("Versão da referência inválida.")
            if metadata.get("fingerprint") != self.repository.fingerprint(self.origin):
                raise ValueError("Calibração ou endereço da câmera mudou; recapture a referência.")
            if metadata.get("image_sha256") != hashlib.sha256(jpeg).hexdigest():
                raise ValueError("Imagem de referência incompatível com seus metadados.")
            image = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Referência não pôde ser decodificada.")
            calibration = self.repository.parking.camera_image
            if (image.shape[1], image.shape[0]) != (calibration.width, calibration.height):
                raise ValueError("Referência com resolução incompatível.")
            self.detector.set_reference(image)
            self.reference_note = "Referência vazia carregada."
        except FileNotFoundError:
            pass
        except (OSError, ValueError, cv2.error) as exc:
            self.reference_note = str(exc)
            self.detector.invalidate(self.reference_note)

    def start(self):
        if self.thread is not None and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name="parking-camera", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=self.camera_settings.request_timeout_seconds * 4 + 1)
            if self.thread.is_alive():
                logger.warning("A aquisição ainda está encerrando uma operação de rede.")

    def _run(self):
        with self.camera_factory() as camera:
            while not self.stop_event.is_set():
                delay = self.camera_settings.preview_interval_seconds
                try:
                    self.accept_frame(camera.capture())
                except CameraError as exc:
                    self.capture_failed(str(exc))
                    delay = max(delay, 1.0)
                except Exception:
                    logger.exception("Falha inesperada na aquisição/análise.")
                    self.capture_failed("Falha no processamento; confira o terminal do backend.")
                    delay = 1.0
                self.stop_event.wait(delay)

    def accept_frame(self, frame: CapturedFrame):
        """Publica somente capturas novas e válidas; também permite testes sem hardware."""
        now = self.clock()
        with self.lock:
            self.frame = frame
            self.frame_sequence += 1
            self.last_frame_time = now
            self.camera_error = None
            self.frame_times.append(now)
            if not self.repository.detection.enabled:
                self.detector.invalidate("Análise pausada.")
            elif (
                self.last_analysis_time is None
                or now - self.last_analysis_time >= self.repository.detection.analysis_interval_seconds
            ):
                self.detector.analyze(frame.bgr, now)
                self.last_analysis_time = now
            self._simulate_leds()

    def capture_failed(self, reason):
        with self.lock:
            self.camera_error = reason
            self.frame_times.clear()
            self.detector.invalidate("Imagem indisponível; estado desconhecido.")
            self.last_analysis_time = None
            self._simulate_leds()

    def _simulate_leds(self):
        # Nunca abre conexão com /leds. LEDs reais permanecem fora deste teste.
        states = self.detector.snapshot()
        colors = self.repository.system["leds"]["colors"]
        leds = {
            str(spot.led_index): {
                "spot_id": spot.id,
                "state": states[spot.id]["state"],
                "rgb": colors[states[spot.id]["state"]],
            }
            for spot in self.repository.parking.spots
        }
        if leds != self.simulated_leds:
            logger.info("LEDs em simulação: %s", {key: value["state"] for key, value in leds.items()})
            self.simulated_leds = leds

    def _fresh(self):
        return (
            self.frame is not None
            and self.camera_error is None
            and self.last_frame_time is not None
            and self.clock() - self.last_frame_time <= self.camera_settings.stale_after_seconds
        )

    def _require_frame(self):
        if not self._fresh():
            raise ValueError("A câmera não tem uma imagem recente. Confira rede e endereço.")
        return self.frame

    def _reference_ready(self):
        return (
            self.detector.reference is not None
            and self.frame is not None
            and self.detector.reference.shape == self.frame.bgr.shape
        )

    def status(self):
        with self.lock:
            online = self._fresh()
            if not online:
                self.detector.invalidate("Câmera desconectada ou imagem vencida.")
                self._simulate_leds()
            states = self.detector.snapshot()
            spots = []
            for spot in self.repository.parking.spots:
                spots.append({**spot.model_dump(mode="json"), **states[spot.id]})
            counts = {
                "total": len(spots),
                "free": sum(spot["state"] == "free" for spot in spots),
                "occupied": sum(spot["state"] == "occupied" for spot in spots),
                "unknown": sum(spot["state"] == "unknown" for spot in spots),
            }
            elapsed = (
                self.frame_times[-1] - self.frame_times[0] if len(self.frame_times) > 1 else 0
            )
            fps = (len(self.frame_times) - 1) / elapsed if elapsed > 0 and online else 0
            return {
                "camera_online": online,
                "camera_error": (self.camera_error or "A última imagem está vencida.") if not online else None,
                "camera_url": self.origin,
                "frame_sequence": self.frame_sequence,
                "image_width": self.frame.width if self.frame is not None else None,
                "image_height": self.frame.height if self.frame is not None else None,
                "updated_at": self.frame.received_at.isoformat() if self.frame is not None else None,
                "fps": round(fps, 1),
                "analysis_enabled": self.repository.detection.enabled,
                "reference_ready": self._reference_ready(),
                "reference_note": (
                    "A resolução mudou. Recalibre e capture uma nova referência."
                    if self.detector.reference is not None and self.frame is not None
                    and self.detector.reference.shape != self.frame.bgr.shape
                    else self.reference_note
                ),
                "calibrated_count": sum(spot.camera_roi is not None for spot in self.repository.parking.spots),
                "counts": counts,
                "spots": spots,
                "detection": self.repository.detection.model_dump(mode="json"),
                "led_mode": "simulation",
                "leds": self.simulated_leds,
            }

    def video_frame(self):
        with self.lock:
            if not self._fresh():
                return None
            return self.frame_sequence, self.frame.jpeg

    def snapshot_frame(self):
        with self.lock:
            frame = self._require_frame()
            return frame.jpeg, frame.width, frame.height

    def save_roi(self, identifier, points, width, height):
        points = valid_polygon(points)
        with self.lock:
            frame = self._require_frame()
            if (width, height) != (frame.width, frame.height):
                raise ValueError("A resolução mudou durante a seleção. Capture outra imagem.")
            parking = self.repository.parking.model_copy(deep=True)
            if identifier not in {spot.id for spot in parking.spots}:
                raise KeyError(identifier)
            previous = parking.camera_image
            if (previous.width, previous.height) not in [(None, None), (width, height)]:
                for spot in parking.spots:
                    spot.camera_roi = None
            for spot in parking.spots:
                if spot.id == identifier:
                    spot.camera_roi = points
            parking.camera_image = ImageCalibration(width=width, height=height, calibrated=True)
            parking = ParkingConfig.model_validate(parking.model_dump())
            self.repository.save_parking(parking)
            self.detector = self._new_detector()
            self.reference_note = "Regiões alteradas. Capture novamente a referência vazia."
            self.last_analysis_time = None
            self.repository.save_detection(
                self.repository.detection.model_copy(update={"enabled": False})
            )
            self.detector.settings = self.repository.detection
            self._simulate_leds()
        return self.status()

    def save_reference(self, confirm_empty: bool):
        if not confirm_empty:
            raise ValueError("Confirme explicitamente que todas as regiões estão vazias.")
        with self.lock:
            frame = self._require_frame()
            parking = self.repository.parking
            if not any(spot.camera_roi is not None for spot in parking.spots):
                raise ValueError("Calibre pelo menos uma vaga antes de capturar a referência.")
            if (parking.camera_image.width, parking.camera_image.height) != (frame.width, frame.height):
                raise ValueError("Refaça a calibração para a resolução atual.")
            detector = self._new_detector()
            detector.set_reference(frame.bgr)
            if not detector.masks:
                raise ValueError("As regiões estão pequenas demais. Refaça a seleção.")
            metadata = {
                "schema_version": 1,
                "fingerprint": self.repository.fingerprint(self.origin),
                "image_sha256": hashlib.sha256(frame.jpeg).hexdigest(),
                "captured_at": frame.received_at.isoformat(),
            }
            try:
                atomic_write(self.repository.reference_path, frame.jpeg)
                write_json(self.repository.reference_metadata_path, metadata)
            except OSError:
                self.detector = self._new_detector()
                self.reference_note = "Falha ao salvar referência; análise invalidada."
                self._simulate_leds()
                raise
            self.detector = detector
            self.last_analysis_time = None
            self.reference_note = "Referência vazia capturada."
            self._simulate_leds()
        return self.status()

    def configure_detection(self, values: dict):
        # A API não permite trocar o caminho do arquivo de referência.
        allowed = {
            "enabled", "pixel_difference_threshold", "free_max_changed_ratio",
            "occupied_min_changed_ratio", "confirmation_frames",
        }
        if set(values) - allowed:
            raise ValueError("Parâmetro de análise não editável pela interface.")
        with self.lock:
            settings = DetectionSettings.model_validate(
                {**self.repository.detection.model_dump(), **values}
            )
            if settings.enabled and (not self._fresh() or not self._reference_ready()):
                raise ValueError("É preciso uma imagem recente e uma referência válida para iniciar.")
            reference = self.detector.reference
            self.repository.save_detection(settings)
            detector = self._new_detector()
            if reference is not None:
                detector.set_reference(reference)
            self.detector = detector
            self.last_analysis_time = None
            self._simulate_leds()
        return self.status()
