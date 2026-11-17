from fastapi.testclient import TestClient

from parking_monitor.app import create_app
from parking_monitor.monitor import ParkingMonitor


def test_api_calibration_reference_analysis_and_validation(monitor_root, empty_scene, make_frame):
    clock = [0.0]
    monitor = ParkingMonitor(monitor_root, "http://camera.test", clock=lambda: clock[0])
    application = create_app(monitor, start_acquisition=False)
    with TestClient(application) as client:
        assert client.get("/").status_code == 200
        assert client.get("/assets/app.js").status_code == 200
        assert client.get("/api/video").status_code == 503
        assert client.get("/api/frame.jpg").status_code == 503
        assert client.get("/api/status").json()["counts"]["unknown"] == 10
        assert client.put("/api/detection", json={"enabled": True}).status_code == 400
        monitor.accept_frame(make_frame(empty_scene))
        photo = client.get("/api/frame.jpg")
        assert photo.headers["content-type"] == "image/jpeg"
        assert photo.headers["x-frame-width"] == "320"
        roi = {"points": [[.25, .25], [.7, .25], [.7, .75], [.25, .75]], "width": 320, "height": 240}
        assert client.put("/api/spots/UNKNOWN/roi", json=roi).status_code == 404
        assert client.put("/api/spots/V01/roi", json={**roi, "points": [[0, 0], [1, 1]]}).status_code == 422
        assert client.put("/api/spots/V01/roi", json=roi).status_code == 200
        assert client.post("/api/reference", json={}).status_code == 400
        baseline = client.post("/api/reference", json={"confirm_empty": True})
        assert baseline.status_code == 200
        assert baseline.json()["reference_ready"]
        assert client.put("/api/detection", json={"enabled": True}).status_code == 200
        for _ in range(4):
            clock[0] += .5
            monitor.accept_frame(make_frame(empty_scene))
        assert client.get("/api/status").json()["counts"]["free"] == 1
        invalid = client.put("/api/detection", json={"free_max_changed_ratio": .8, "occupied_min_changed_ratio": .2})
        assert invalid.status_code == 400
        assert monitor.repository.detection.free_max_changed_ratio == .08
        assert client.put("/api/detection", json={"reference_image": "wrong"}).status_code == 422
        assert client.put("/api/detection", json={"enabled": False}).status_code == 200
        assert client.get("/api/status").json()["counts"]["unknown"] == 10
