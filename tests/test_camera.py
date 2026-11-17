from datetime import UTC

import cv2
import httpx
import numpy as np
import pytest

from parking_monitor.camera import CameraClient, CameraUnavailableError, InvalidFrameError
from parking_monitor.settings import CameraSettings


@pytest.fixture
def jpeg():
    # Imagem sintética conhecida; não exige câmera nem arquivo real versionado.
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    image[:, :32] = (20, 60, 220)
    image[:, 32:] = (180, 120, 40)
    success, encoded = cv2.imencode(".jpg", image)
    assert success
    return encoded.tobytes()


def test_valid_jpeg_has_pixels_dimensions_and_receipt_time(jpeg):
    def handler(request):
        assert request.method == "GET"
        assert request.url == "http://camera.test/capture"
        assert request.headers["accept"] == "image/jpeg"
        assert all(value == 2.0 for value in request.extensions["timeout"].values())
        return httpx.Response(200, content=jpeg, headers={"content-type": "image/jpeg"})

    with CameraClient(
        "http://camera.test/", CameraSettings(), transport=httpx.MockTransport(handler)
    ) as camera:
        frame = camera.capture()
    assert frame.jpeg == jpeg
    assert (frame.width, frame.height) == (64, 48)
    assert frame.bgr.dtype == np.uint8
    assert np.allclose(frame.bgr[20, 10], (20, 60, 220), atol=5)
    assert frame.received_at.tzinfo is UTC
    assert frame.duration_seconds >= 0


@pytest.mark.parametrize("status", [302, 404, 503])
def test_http_errors_and_redirects_are_not_images(status, jpeg):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            status, content=jpeg, headers={"content-type": "image/jpeg", "location": "/login"}
        )
    )
    with CameraClient("http://camera.test", CameraSettings(), transport=transport) as camera:
        with pytest.raises(CameraUnavailableError, match=str(status)):
            camera.capture()


@pytest.mark.parametrize("failure", [httpx.ConnectError, httpx.ReadTimeout])
def test_connection_failure_and_next_capture_can_recover(failure, jpeg):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise failure("falha simulada", request=request)
        return httpx.Response(200, content=jpeg, headers={"content-type": "image/jpeg"})

    with CameraClient(
        "http://camera.test", CameraSettings(), transport=httpx.MockTransport(handler)
    ) as camera:
        with pytest.raises(CameraUnavailableError):
            camera.capture()
        assert camera.capture().jpeg == jpeg
    assert calls == 2


@pytest.mark.parametrize("kind", ["html", "empty", "truncated", "undecodable", "png"])
def test_invalid_frames_are_rejected(kind, jpeg):
    payloads = {
        "html": b"<html>portal de login</html>",
        "empty": b"",
        "truncated": jpeg[:-10],
        "undecodable": b"\xff\xd8invalid\xff\xd9",
        "png": b"\x89PNG\r\n\x1a\n",
    }
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            content=payloads[kind],
            headers={"content-type": "text/html" if kind == "html" else "image/jpeg"},
        )
    )
    with CameraClient("http://camera.test", CameraSettings(), transport=transport) as camera:
        with pytest.raises(InvalidFrameError):
            camera.capture()


@pytest.mark.parametrize("length", ["invalid", "-1", "0", "2000001"])
def test_bad_content_length_is_rejected(length, jpeg):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200, content=jpeg, headers={"content-type": "image/jpeg", "content-length": length}
        )
    )
    with CameraClient("http://camera.test", CameraSettings(), transport=transport) as camera:
        with pytest.raises(InvalidFrameError):
            camera.capture()


def test_stream_limit_without_content_length_closes_response(jpeg):
    class ChunkedFrame(httpx.SyncByteStream):
        closed = False

        def __iter__(self):
            yield jpeg[:300]
            yield jpeg[300:]

        def close(self):
            self.closed = True

    stream = ChunkedFrame()
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, stream=stream, headers={"content-type": "image/jpeg"})
    )
    settings = CameraSettings(max_frame_bytes=len(jpeg) - 1)
    with CameraClient("http://camera.test", settings, transport=transport) as camera:
        with pytest.raises(InvalidFrameError, match="max_frame_bytes"):
            camera.capture()
    assert stream.closed
