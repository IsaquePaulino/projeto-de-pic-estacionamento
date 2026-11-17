import json
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from parking_monitor.camera import CapturedFrame
from parking_monitor.configuration import DetectionSettings, ImageCalibration, ParkingConfig

ROOT = Path(__file__).resolve().parents[1]
ROI = [(0.25, 0.25), (0.70, 0.25), (0.70, 0.75), (0.25, 0.75)]


@pytest.fixture
def monitor_root(tmp_path):
    config = tmp_path / "config"
    config.mkdir()
    for name in ["system.json", "parking.json"]:
        data = json.loads((ROOT / "config" / name).read_text(encoding="utf-8"))
        if name == "system.json":
            data["detection"] = DetectionSettings().model_dump(mode="json")
        else:
            data["camera_image"] = ImageCalibration().model_dump(mode="json")
            for spot in data["spots"]:
                spot["camera_roi"] = None
        (config / name).write_text(json.dumps(data), encoding="utf-8")
    return tmp_path


@pytest.fixture
def parking(monitor_root):
    data = ParkingConfig.model_validate_json(
        (monitor_root / "config/parking.json").read_text(encoding="utf-8")
    )
    data.camera_image = ImageCalibration(width=320, height=240, calibrated=True)
    data.spots[0].camera_roi = ROI.copy()
    return data


@pytest.fixture
def empty_scene():
    return np.full((240, 320, 3), 128, dtype=np.uint8)


@pytest.fixture
def car_scene(empty_scene):
    image = empty_scene.copy()
    # Objeto sintético com corpo e janela dentro da vaga; não é validação física.
    cv2.rectangle(image, (105, 85), (195, 165), (20, 35, 210), -1)
    cv2.rectangle(image, (120, 100), (175, 125), (65, 65, 65), -1)
    return image


@pytest.fixture
def make_frame():
    def encode(image):
        success, jpeg = cv2.imencode(".jpg", image)
        assert success
        payload = jpeg.tobytes()
        bgr = cv2.imdecode(jpeg, cv2.IMREAD_COLOR)
        return CapturedFrame(payload, bgr, datetime.now(UTC), 0.01)
    return encode
