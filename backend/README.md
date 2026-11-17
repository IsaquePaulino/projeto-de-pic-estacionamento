# Backend

Funcionalidades em `src/parking_monitor/`:

- settings.py: carrega ESP32_BASE_URL do ambiente/.env e a seção camera do JSON.
- camera.py: cliente HTTP, timeout, limite de tamanho e validação/decodificação JPEG.
- capture.py: comando para salvar uma ou várias capturas no computador.
- configuration.py: cadastro, validação e persistência atômica de calibrações.
- detection.py: comparação com referência, filtros, evidências e confirmação temporal.
- monitor.py: uma aquisição compartilhada, estado, referência e LEDs simulados.
- app.py: FastAPI, vídeo MJPEG, arquivos da interface e ações de calibração.

O cliente retorna bytes JPEG, array BGR, dimensões, instante de recebimento UTC
e duração da operação. Erros de rede e imagens inválidas são exceções explícitas.
O detector identifica ocupação relativa à referência, não a categoria do objeto.

```powershell
.\.venv\Scripts\python.exe -m parking_monitor.capture --count 3
```

Executar da raiz, após instalar o pacote e configurar .env. Também existe o comando
parking-capture no ambiente virtual. Veja ../docs/camera.md.

Dependências e instalação: veja `pyproject.toml` e `../docs/ambiente.md`.
O projeto usa Python 3.12. Iniciar o painel da raiz:

```powershell
.\.venv\Scripts\python.exe -m uvicorn parking_monitor.app:app --host 127.0.0.1 --port 8000
```

Usar um único worker. Vários navegadores compartilham o mesmo produtor de imagens.
Configurações e referência são arquivos locais; não executar múltiplas instâncias
gravando nos mesmos arquivos. Não há transporte de LEDs físicos neste ensaio.
