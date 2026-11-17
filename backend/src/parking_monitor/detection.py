"""Ocupação por referência, máscaras, limiares e confirmação temporal. Sem IA."""

from dataclasses import dataclass

import cv2
import numpy as np

from parking_monitor.configuration import DetectionSettings, ParkingConfig


@dataclass
class SpotState:
    state: str = "unknown"
    candidate: str = "unknown"
    streak: int = 0
    last_evidence: float | None = None
    changed_ratio: float | None = None
    color_ratio: float | None = None
    edge_ratio: float | None = None
    reason: str = "Análise ainda não iniciada."


class OccupancyDetector:
    def __init__(
        self, parking: ParkingConfig, settings: DetectionSettings, stale_after: float = 5
    ):
        self.parking = parking
        self.settings = settings
        self.stale_after = stale_after
        self.reference = None
        self.gray_reference = None
        self.chroma_reference = None
        self.edges_reference = None
        self.masks = {}
        self.background = None
        self.states = {spot.id: SpotState() for spot in parking.spots}

    def invalidate(self, reason: str) -> None:
        self.states = {spot.id: SpotState(reason=reason) for spot in self.parking.spots}

    @staticmethod
    def quality_error(image) -> str | None:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if gray.std() < 2 and (gray.mean() < 5 or gray.mean() > 250):
            return "Imagem muito escura ou saturada; confira a iluminação."
        return None

    @staticmethod
    def chromaticity(image):
        values = image.astype(np.float32)
        intensity = values.sum(axis=2, keepdims=True)
        return values * 255 / np.maximum(intensity, 1), intensity[:, :, 0] >= 30

    def set_reference(self, image) -> None:
        error = self.quality_error(image)
        if error:
            raise ValueError(error)
        self.reference = image.copy()
        height, width = image.shape[:2]
        kernel = self.settings.gaussian_blur_kernel
        self.gray_reference = cv2.GaussianBlur(
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (kernel, kernel), 0
        ).astype(np.float32)
        self.chroma_reference, self.reference_color_valid = self.chromaticity(image)
        self.edges_reference = cv2.dilate(
            cv2.Canny(self.gray_reference.astype(np.uint8), 50, 120), np.ones((3, 3), np.uint8)
        )
        self.masks = {}
        occupied_pixels = np.zeros((height, width), dtype=np.uint8)
        for spot in self.parking.spots:
            if spot.camera_roi is None:
                continue
            points = np.rint(np.asarray(spot.camera_roi) * [width - 1, height - 1]).astype(np.int32)
            mask = np.zeros((height, width), dtype=np.uint8)
            cv2.fillConvexPoly(mask, points, 255)
            mask = cv2.erode(mask, np.ones((5, 5), dtype=np.uint8))
            if np.count_nonzero(mask) < 16:
                continue
            self.masks[spot.id] = mask > 0
            occupied_pixels |= mask
        self.background = occupied_pixels == 0
        self.invalidate("Aguardando capturas consecutivas.")

    def _confirm(self, identifier: str, candidate: str, now: float, reason: str) -> None:
        state = self.states[identifier]
        state.reason = reason
        if candidate == "unknown":
            state.candidate = "unknown"
            state.streak = 0
            if state.last_evidence is None or now - state.last_evidence >= self.stale_after:
                state.state = "unknown"
            return
        if candidate == state.candidate:
            state.streak = min(state.streak + 1, self.settings.confirmation_frames)
        else:
            state.candidate = candidate
            state.streak = 1
        if state.streak >= self.settings.confirmation_frames:
            state.state = candidate
            state.last_evidence = now
            state.reason = "Vaga livre confirmada." if candidate == "free" else "Ocupação confirmada."
        elif candidate == state.state:
            state.last_evidence = now
        else:
            state.reason = f"Confirmando mudança: {state.streak}/{self.settings.confirmation_frames}."

    def analyze(self, image, now: float) -> None:
        if self.reference is None:
            self.invalidate("Capture uma referência com as vagas vazias.")
            return
        calibration = self.parking.camera_image
        if (image.shape[1], image.shape[0]) != (calibration.width, calibration.height):
            self.invalidate("A resolução mudou. Refaça a calibração e a referência.")
            return
        if image.shape != self.reference.shape:
            self.invalidate("Referência incompatível com a imagem atual.")
            return
        error = self.quality_error(image)
        if error:
            self.invalidate(error)
            return
        kernel = self.settings.gaussian_blur_kernel
        gray = cv2.GaussianBlur(
            cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (kernel, kernel), 0
        ).astype(np.float32)
        raw_difference = gray - self.gray_reference
        # Estimar luz no fundo, não na região que pode ter recebido um carro.
        has_background = np.count_nonzero(self.background) >= max(100, image.shape[0] * image.shape[1] * 0.05)
        offset = float(np.median(raw_difference[self.background])) if has_background else 0.0
        if abs(offset) > self.settings.max_illumination_shift:
            self.invalidate("Mudança forte de iluminação; análise suspensa.")
            return
        normalized = np.clip(gray - offset, 0, 255)
        chroma, color_valid = self.chromaticity(image)
        color_changed = (
            (np.max(np.abs(chroma - self.chroma_reference), axis=2) > self.settings.chromatic_difference_threshold)
            & color_valid & self.reference_color_valid
        )
        # Também detecta um carro colorido com luminância semelhante à do piso.
        changed = (
            (np.abs(normalized - self.gray_reference) > self.settings.pixel_difference_threshold)
            | color_changed
        ).astype(np.uint8) * 255
        morphology_kernel = np.ones((3, 3), dtype=np.uint8)
        changed = cv2.morphologyEx(changed, cv2.MORPH_OPEN, morphology_kernel)
        changed = cv2.morphologyEx(changed, cv2.MORPH_CLOSE, morphology_kernel) > 0
        if float(changed.mean()) > self.settings.max_global_changed_ratio:
            self.invalidate("Mudança global da cena; confira câmera e iluminação.")
            return
        # Movimento do enquadramento, quando existe textura suficiente para estimá-lo.
        if float(self.gray_reference.std()) > 5:
            window = cv2.createHanningWindow((image.shape[1], image.shape[0]), cv2.CV_32F)
            (dx, dy), response = cv2.phaseCorrelate(
                self.gray_reference.copy(), normalized.astype(np.float32), window
            )
            if response > 0.2 and max(abs(dx), abs(dy)) > self.settings.max_camera_shift_pixels:
                self.invalidate("Possível movimento da câmera. Refaça a referência.")
                return
        edges = cv2.Canny(normalized.astype(np.uint8), 50, 120)
        new_edges = (edges > 0) & (self.edges_reference == 0)
        for spot in self.parking.spots:
            state = self.states[spot.id]
            mask = self.masks.get(spot.id)
            if mask is None:
                self._confirm(spot.id, "unknown", now, "Região ainda não calibrada.")
                continue
            state.changed_ratio = float(changed[mask].mean())
            state.color_ratio = float(color_changed[mask].mean())
            state.edge_ratio = float(new_edges[mask].mean())
            evidence = (
                state.color_ratio >= self.settings.min_color_changed_ratio
                or state.edge_ratio >= self.settings.min_new_edge_ratio
            )
            if state.changed_ratio <= self.settings.free_max_changed_ratio:
                candidate, reason = "free", "Pouca alteração em relação à referência."
            elif state.changed_ratio >= self.settings.occupied_min_changed_ratio and evidence:
                candidate, reason = "occupied", "Alteração com evidência de cor ou contorno."
            else:
                candidate, reason = "unknown", "Resultado ambíguo ou possível sombra."
            self._confirm(spot.id, candidate, now, reason)

    def snapshot(self) -> dict:
        return {
            identifier: {
                "state": state.state,
                "candidate": state.candidate,
                "confirmation_count": state.streak,
                "changed_ratio": state.changed_ratio,
                "color_ratio": state.color_ratio,
                "edge_ratio": state.edge_ratio,
                "reason": state.reason,
            }
            for identifier, state in self.states.items()
        }
