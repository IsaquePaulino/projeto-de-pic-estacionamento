import json

import cv2
import httpx
import numpy as np
import pytest
from pydantic import ValidationError

from parking_monitor import capture
from parking_monitor.camera import CameraClient
from parking_monitor.settings import CameraSettings, NetworkSettings, load_camera_settings


def test_environment_overrides_dotenv_without_requiring_other_future_settings(tmp_path, monkeypatch):
    dotenv = tmp_path / ".env"
    dotenv.write_text("ESP32_BASE_URL=http://192.168.1.50\nLED_MODE=simulation\n", encoding="utf-8")
    monkeypatch.setenv("ESP32_BASE_URL", "http://192.168.1.70:8080")
    network = NetworkSettings(_env_file=dotenv)
    assert str(network.esp32_base_url) == "http://192.168.1.70:8080/"


@pytest.mark.parametrize(
    "value",
    ["ftp://camera.test", "http://camera.test/capture", "http://user:secret@camera.test", "http://camera.test?x=1"],
)
def test_invalid_camera_origins(value):
    with pytest.raises(ValidationError):
        NetworkSettings(_env_file=None, esp32_base_url=value)


@pytest.mark.parametrize(
    "values",
    [
        {"request_timeout_seconds": 0},
        {"request_timeout_seconds": float("inf")},
        {"poll_interval_seconds": -1},
        {"max_frame_bytes": 0},
        {"capture_path": "//other-host/capture"},
        {"capture_path": "capture"},
    ],
)
def test_invalid_capture_parameters(values):
    with pytest.raises(ValidationError):
        CameraSettings(**values)


def test_load_camera_section(tmp_path):
    path = tmp_path / "system.json"
    path.write_text(
        json.dumps({"schema_version": 1, "camera": {"request_timeout_seconds": 4.5}}),
        encoding="utf-8",
    )
    assert load_camera_settings(path).request_timeout_seconds == 4.5


@pytest.mark.parametrize("data", [{"schema_version": 2, "camera": {}}, {"schema_version": 1}])
def test_incompatible_configuration_is_rejected(tmp_path, data):
    path = tmp_path / "system.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_camera_settings(path)


@pytest.mark.parametrize("status, expected_code, expected_files", [(200, 0, 2), (503, 1, 0)])
def test_cli_saves_only_valid_new_captures(tmp_path, monkeypatch, capsys, status, expected_code, expected_files):
    success, jpeg = cv2.imencode(".jpg", np.full((24, 32, 3), 80, dtype=np.uint8))
    assert success
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            status, content=jpeg.tobytes(), headers={"content-type": "image/jpeg"}
        )
    )
    monkeypatch.setenv("ESP32_BASE_URL", "http://camera.test")
    monkeypatch.setattr(
        capture, "CameraClient",
        lambda base_url, settings: CameraClient(base_url, settings, transport=transport),
    )
    pauses = []
    monkeypatch.setattr(capture, "sleep", pauses.append)
    # Um diretorio de trabalho diferente nao altera a origem dos arquivos de configuracao.
    monkeypatch.chdir(tmp_path)
    destination = tmp_path / "images"
    assert capture.main(["--count", "2", "--output-dir", str(destination)]) == expected_code
    files = list(destination.glob("*.jpg"))
    assert len(files) == expected_files
    for path in files:
        assert path.read_bytes() == jpeg.tobytes()
    output = capsys.readouterr()
    if status == 200:
        assert len(pauses) == 1
        assert "32x24" in output.out
        assert not output.err
    else:
        assert not pauses
        assert "HTTP 503" in output.err


def test_cli_requires_camera_address(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("ESP32_BASE_URL", raising=False)
    monkeypatch.setattr(capture, "NetworkSettings", lambda: NetworkSettings(_env_file=None))
    assert capture.main(["--output-dir", str(tmp_path / "images")]) == 1
    assert "esp32_base_url" in capsys.readouterr().err
    assert not (tmp_path / "images").exists()


def test_cli_keeps_both_captures_even_with_identical_timestamps(tmp_path, monkeypatch, make_frame):
    frame = make_frame(np.full((24, 32, 3), 100, dtype=np.uint8))

    class FixedCamera:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def capture(self):
            return frame

    monkeypatch.setenv("ESP32_BASE_URL", "http://camera.test")
    monkeypatch.setattr(capture, "CameraClient", lambda *_: FixedCamera())
    monkeypatch.setattr(capture, "sleep", lambda _: None)
    assert capture.main(["--count", "2", "--output-dir", str(tmp_path)]) == 0
    saved = list(tmp_path.glob("capture-*.jpg"))
    assert len(saved) == 2
    assert all(path.read_bytes() == frame.jpeg for path in saved)
