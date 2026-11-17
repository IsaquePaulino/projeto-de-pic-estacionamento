import asyncio
import json

import numpy as np
import pytest

from parking_monitor.app import video_chunks
from parking_monitor.monitor import ParkingMonitor

ROI = [(0.25, 0.25), (0.70, 0.25), (0.70, 0.75), (0.25, 0.75)]


def prepare(monitor_root, empty_scene, make_frame):
    clock = [10.0]
    monitor = ParkingMonitor(monitor_root, "http://camera.test", clock=lambda: clock[0])
    monitor.accept_frame(make_frame(empty_scene))
    monitor.save_roi("V01", ROI, 320, 240)
    monitor.save_reference(True)
    monitor.configure_detection({"enabled": True})
    return monitor, clock


def test_confirmation_counts_persistence_and_simulated_leds(monitor_root, empty_scene, car_scene, make_frame):
    monitor, clock = prepare(monitor_root, empty_scene, make_frame)
    for _ in range(4):
        clock[0] += .5
        monitor.accept_frame(make_frame(car_scene))
    status = monitor.status()
    assert status["counts"] == {"total": 10, "free": 0, "occupied": 1, "unknown": 9}
    assert status["led_mode"] == "simulation"
    assert status["leds"]["0"]["state"] == "occupied"
    assert status["leds"]["0"]["rgb"] == [255, 0, 0]
    assert json.loads((monitor_root / "config/parking.json").read_text())["spots"][0]["camera_roi"]
    restarted = ParkingMonitor(monitor_root, "http://camera.test", clock=lambda: clock[0])
    restarted.accept_frame(make_frame(empty_scene))
    assert restarted.status()["reference_ready"]
    assert restarted.status()["counts"]["unknown"] == 10


def test_network_failure_and_stale_frames_never_report_free(monitor_root, empty_scene, make_frame):
    monitor, clock = prepare(monitor_root, empty_scene, make_frame)
    for _ in range(4):
        clock[0] += .5
        monitor.accept_frame(make_frame(empty_scene))
    assert monitor.status()["counts"]["free"] == 1
    clock[0] += 6
    assert not monitor.status()["camera_online"]
    assert monitor.status()["counts"]["unknown"] == 10
    assert monitor.video_frame() is None
    monitor.accept_frame(make_frame(empty_scene))
    monitor.capture_failed("Timeout no teste.")
    assert monitor.status()["camera_error"] == "Timeout no teste."
    assert monitor.status()["counts"]["unknown"] == 10


def test_roi_changes_and_camera_origin_invalidate_reference(monitor_root, empty_scene, make_frame):
    monitor, clock = prepare(monitor_root, empty_scene, make_frame)
    other_origin = ParkingMonitor(monitor_root, "http://other-camera.test", clock=lambda: clock[0])
    other_origin.accept_frame(make_frame(empty_scene))
    assert not other_origin.status()["reference_ready"]
    monitor.save_roi("V01", [(0.2, .2), (.6, .2), (.6, .8), (.2, .8)], 320, 240)
    assert not monitor.status()["reference_ready"]
    with pytest.raises(ValueError):
        monitor.configure_detection({"enabled": True})
    restarted = ParkingMonitor(monitor_root, "http://camera.test")
    assert restarted.detector.reference is None


def test_reference_requires_empty_confirmation_and_fresh_image(monitor_root, empty_scene, make_frame):
    clock = [0]
    monitor = ParkingMonitor(monitor_root, "http://camera.test", clock=lambda: clock[0])
    with pytest.raises(ValueError):
        monitor.save_reference(True)
    monitor.accept_frame(make_frame(empty_scene))
    with pytest.raises(ValueError):
        monitor.save_reference(True)
    monitor.save_roi("V01", ROI, 320, 240)
    with pytest.raises(ValueError):
        monitor.save_reference(False)
    monitor.save_reference(True)
    assert monitor.status()["reference_ready"]
    clock[0] += 6
    with pytest.raises(ValueError):
        monitor.save_reference(True)


def test_reference_image_and_metadata_must_match(monitor_root, empty_scene, make_frame):
    monitor, _ = prepare(monitor_root, empty_scene, make_frame)
    (monitor_root / "data/reference/empty.jpg").write_bytes(b"corrupted")
    restarted = ParkingMonitor(monitor_root, "http://camera.test")
    assert restarted.detector.reference is None
    assert "metadados" in restarted.reference_note


def test_bad_reference_metadata_does_not_prevent_startup(monitor_root, empty_scene, make_frame):
    prepare(monitor_root, empty_scene, make_frame)
    (monitor_root / "data/reference/empty.json").write_text("[]", encoding="utf-8")
    restarted = ParkingMonitor(monitor_root, "http://camera.test")
    assert restarted.detector.reference is None
    assert "Metadados" in restarted.reference_note


def test_invalid_simulation_colors_are_rejected_at_startup(monitor_root):
    path = monitor_root / "config/system.json"
    settings = json.loads(path.read_text())
    settings["leds"]["colors"]["unknown"] = [-1, 300, 0]
    path.write_text(json.dumps(settings), encoding="utf-8")
    with pytest.raises(ValueError, match="RGB"):
        ParkingMonitor(monitor_root, "http://camera.test")


def test_resolution_recalibration_clears_other_old_regions(monitor_root, empty_scene, make_frame):
    monitor, _ = prepare(monitor_root, empty_scene, make_frame)
    monitor.save_roi("V02", ROI, 320, 240)
    image = np.full((120, 160, 3), 128, np.uint8)
    monitor.accept_frame(make_frame(image))
    with pytest.raises(ValueError):
        monitor.save_roi("V01", ROI, 320, 240)
    monitor.save_roi("V01", ROI, 160, 120)
    assert monitor.repository.parking.spots[1].camera_roi is None
    assert not monitor.status()["reference_ready"]


def test_mjpeg_uses_cached_frames_and_exits_when_camera_is_lost(monitor_root, empty_scene, car_scene, make_frame):
    monitor, _ = prepare(monitor_root, empty_scene, make_frame)

    async def check():
        viewer = video_chunks(monitor)
        first = await anext(viewer)
        assert first.startswith(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ")
        first_frame = monitor.frame.jpeg
        assert first.endswith(first_frame + b"\r\n")
        monitor.accept_frame(make_frame(car_scene))
        second = await anext(viewer)
        assert second != first
        monitor.capture_failed("offline")
        with pytest.raises(StopAsyncIteration):
            await anext(viewer)
        await viewer.aclose()

    asyncio.run(check())
