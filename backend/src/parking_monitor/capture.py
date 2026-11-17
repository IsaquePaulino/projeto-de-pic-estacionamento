"""Comando de validação da câmera: python -m parking_monitor.capture."""

import argparse
import sys
from pathlib import Path
from time import sleep
from uuid import uuid4

from pydantic import ValidationError

from parking_monitor.camera import CameraClient, CameraError
from parking_monitor.settings import PROJECT_ROOT, NetworkSettings, load_camera_settings


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Informe um número inteiro maior que zero.")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Captura JPEG da ESP32-CAM, sem detecção.")
    parser.add_argument("--count", type=positive_int, default=1, help="Quantidade de capturas.")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/captures"), help="Pasta de saída."
    )
    args = parser.parse_args(argv)
    destination = args.output_dir
    if not destination.is_absolute():
        destination = PROJECT_ROOT / destination
    try:
        network = NetworkSettings()
        camera = load_camera_settings()
        destination.mkdir(parents=True, exist_ok=True)
        with CameraClient(str(network.esp32_base_url), camera) as client:
            for index in range(args.count):
                frame = client.capture()
                timestamp = frame.received_at.strftime("%Y%m%dT%H%M%S%fZ")
                target = destination / f"capture-{timestamp}-{uuid4().hex}.jpg"
                # Não sobrescrever capturas anteriores nem reutilizar imagem em falhas.
                with target.open("xb") as output:
                    output.write(frame.jpeg)
                print(
                    f"{index + 1}/{args.count}: {frame.width}x{frame.height}, "
                    f"{len(frame.jpeg)} bytes, {frame.duration_seconds:.3f}s -> {target}"
                )
                if index + 1 < args.count:
                    sleep(camera.poll_interval_seconds)
    except ValidationError as exc:
        fields = ", ".join(".".join(map(str, error["loc"])) for error in exc.errors())
        print(f"Configuração inválida ({fields}). Confira .env e config/system.json.", file=sys.stderr)
        return 1
    except (CameraError, OSError, ValueError) as exc:
        print(f"Falha na captura: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
