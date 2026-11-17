"""Ensaio de interface com fonte sintética, sem hardware ou alteração da configuração real.

Executar: .venv\\Scripts\\python.exe tests\\ui_smoke.py
Requer o extra ui e Chrome instalado. Capturas ficam em data/qa/.
"""

import json
import socket
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np
import uvicorn
from playwright.sync_api import expect, sync_playwright

from parking_monitor.app import create_app
from parking_monitor.camera import CameraUnavailableError, CapturedFrame
from parking_monitor.configuration import DetectionSettings, ImageCalibration
from parking_monitor.monitor import ParkingMonitor

ROOT = Path(__file__).resolve().parents[1]


class SyntheticCamera:
    occupied = False
    offline = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def capture(self):
        if self.offline:
            raise CameraUnavailableError("Fonte sintética desconectada para o ensaio.")
        image = np.full((480, 640, 3), (155, 165, 155), np.uint8)
        cv2.rectangle(image, (0, 220), (640, 310), (75, 85, 75), -1)
        for x in [35, 250, 465]:
            cv2.rectangle(image, (x, 28), (x + 145, 204), (225, 235, 225), 2)
            cv2.rectangle(image, (x, 330), (x + 145, 467), (225, 235, 225), 2)
        cv2.putText(image, "FONTE SINTETICA - TESTE DA INTERFACE", (15, 278), cv2.FONT_HERSHEY_SIMPLEX, .55, (245, 245, 245), 1)
        if self.occupied:
            cv2.rectangle(image, (70, 67), (153, 171), (35, 45, 205), -1)
            cv2.rectangle(image, (88, 87), (138, 120), (75, 75, 75), -1)
        success, encoded = cv2.imencode(".jpg", image)
        if not success:
            raise RuntimeError("Falha ao gerar a cena do ensaio.")
        payload = encoded.tobytes()
        decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        return CapturedFrame(payload, decoded, datetime.now(UTC), 0.01)


def main():
    artifacts = ROOT / "data/qa"
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="parking-ui-") as directory:
        root = Path(directory)
        (root / "config").mkdir()
        for filename in ["parking.json", "system.json"]:
            data = json.loads((ROOT / "config" / filename).read_text(encoding="utf-8"))
            if filename == "system.json":
                data["detection"] = DetectionSettings().model_dump(mode="json")
            else:
                data["camera_image"] = ImageCalibration().model_dump(mode="json")
                for spot in data["spots"]:
                    spot["camera_roi"] = None
            (root / "config" / filename).write_text(json.dumps(data), encoding="utf-8")
        camera = SyntheticCamera()
        monitor = ParkingMonitor(root, "http://fonte-sintetica.test", camera_factory=lambda: camera)
        application = create_app(monitor)
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(application, log_level="warning", access_log=False))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel="chrome", headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1150})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded")
                expect(page.locator("#connection")).to_have_text("Câmera conectada")
                page.wait_for_function("document.getElementById('camera-image').naturalWidth === 640")
                page.locator("#select-region").click()
                page.wait_for_function("document.getElementById('camera-image').src.startsWith('blob:')")
                stage = page.locator("#camera-stage")
                box = stage.bounding_box()
                # Cliques por linha (em vez de contornar) também devem salvar.
                # Um ponto repetido deve explicar o erro sem perder a seleção.
                for x, y in [(0.06, 0.06), (0.28, 0.06), (0.06, 0.43), (0.06, 0.43)]:
                    stage.click(position={"x": box["width"] * x, "y": box["height"] * y})
                expect(page.locator("#save-region")).to_be_enabled()
                page.locator("#save-region").click()
                expect(page.locator("#notice")).to_contain_text("quatro cantos distintos")
                expect(page.locator("#selection-controls")).to_be_visible()
                page.locator("#undo-point").click()
                stage.click(position={"x": box["width"] * .28, "y": box["height"] * .43})
                page.locator("#save-region").click()
                expect(page.locator("#notice")).to_contain_text("Região salva")
                saved = json.loads((root / "config/parking.json").read_text(encoding="utf-8"))
                assert saved["camera_image"]["calibrated"] is True
                assert len(saved["spots"][0]["camera_roi"]) == 4
                page.reload(wait_until="domcontentloaded")
                expect(page.locator("#calibrated-count")).to_have_text("1 de 10 regiões calibradas")
                expect(page.locator("#regions polygon")).to_have_count(1)
                page.locator("#confirm-empty").check()
                page.locator("#save-reference").click()
                expect(page.locator("#reference-status")).to_have_text("Referência pronta para o teste")
                page.locator("#toggle-analysis").click()
                expect(page.locator("#count-free")).to_have_text("1", timeout=10000)
                camera.occupied = True
                expect(page.locator("#count-occupied")).to_have_text("1", timeout=10000)
                expect(page.locator("#count-unknown")).to_have_text("9")
                page.screenshot(path=str(artifacts / "interface-desktop.png"), full_page=True)
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.screenshot(path=str(artifacts / "interface-mobile.png"), full_page=True)
                camera.offline = True
                expect(page.locator("#connection")).to_have_text("Câmera sem imagem", timeout=6000)
                expect(page.locator("#count-unknown")).to_have_text("10")
                camera.offline = False
                expect(page.locator("#connection")).to_have_text("Câmera conectada", timeout=6000)
                expect(page.locator("#count-occupied")).to_have_text("1", timeout=10000)
                assert not errors, errors
                browser.close()
            print("OK: vídeo, quatro pontos, ROI, referência, livre/ocupado, perda e reconexão.")
            print("OK: desktop/mobile sem overflow e sem erros JavaScript.")
            print("Fonte sintética; nenhum resultado físico de precisão foi medido.")
        finally:
            server.should_exit = True
            thread.join(timeout=8)
            listener.close()
            if thread.is_alive():
                raise RuntimeError("Servidor de ensaio não encerrou.")


if __name__ == "__main__":
    main()
