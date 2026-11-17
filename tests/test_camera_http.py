"""Integração HTTP em loopback; não representa teste com ESP32-CAM física."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

import cv2
import numpy as np
import pytest

from parking_monitor.camera import CameraClient, CameraUnavailableError
from parking_monitor.settings import CameraSettings


@pytest.mark.parametrize("disconnect", [False, True])
def test_real_http_transfer_and_incomplete_body(disconnect):
    success, jpeg = cv2.imencode(".jpg", np.full((40, 60, 3), 100, dtype=np.uint8))
    assert success
    payload = jpeg.tobytes()
    paths = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            paths.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(payload) + (10 if disconnect else 0)))
            self.end_headers()
            self.wfile.write(payload)
            self.close_connection = True

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        with CameraClient(url, CameraSettings()) as camera:
            if disconnect:
                with pytest.raises(CameraUnavailableError):
                    camera.capture()
            else:
                frame = camera.capture()
                assert frame.jpeg == payload
                assert (frame.width, frame.height) == (60, 40)
        assert paths == ["/capture"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
