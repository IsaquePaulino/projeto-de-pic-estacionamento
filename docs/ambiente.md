# Preparação do ambiente

## Requisitos

- Windows com PowerShell, Python 3.12 e Git.
- Arduino IDE 2.x com pacote esp32 by Espressif Systems 2.0.17 para o firmware.
- Navegador moderno para a futura interface.
- Wi-Fi local nas etapas com ESP32-CAM, sem serviço pago ou nuvem.

Python está delimitado a 3.12 para uma base inicial única. Outras versões só serão
liberadas após validar dependências. No Windows, preferir `py -3.12` ao Python MSYS2.

## Dependências do computador

| Pacote | Papel nas etapas futuras |
| --- | --- |
| FastAPI | API HTTP, validação de entradas e arquivos estáticos |
| Uvicorn | Servidor ASGI para executar FastAPI |
| HTTPX | Solicitar JPEGs e enviar comandos com timeout |
| NumPy | Arrays e máscaras do processamento |
| opencv-python-headless | OpenCV sem janelas; calibração pelo navegador |
| pydantic-settings | Carregamento tipado de ambiente/configuração local |
| pytest (extra dev) | Testes automatizados quando houver funcionalidades |

As faixas estão em backend/pyproject.toml. Escolhemos OpenCV 4.x deliberadamente;
não instalar variantes concorrentes, pois usam o mesmo módulo cv2. Veja a
[documentação do pacote](https://pypi.org/project/opencv-python-headless/).
Outras referências: [FastAPI](https://fastapi.tiangolo.com/),
[HTTPX](https://www.python-httpx.org/) e
[Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

O pacote 0.3.0 está instalado em modo editável no ambiente local e
pip check passou. HTTPX 0.28.1, NumPy 2.5.4, OpenCV headless 4.14.0.94,
pydantic-settings 2.16.2 e pytest 9.2.0 foram usados nos testes.
Não há lock completo; faixas não garantem versões idênticas em outra instalação.

O painel pode ser iniciado por iniciar-monitor.bat ou com Uvicorn, conforme
[teste-ocupacao.md](teste-ocupacao.md). Playwright é um extra opcional ui para
ensaios de navegador; não é necessário para usar o painel.

## Instalação

Executar a partir da raiz:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"
.\.venv\Scripts\python.exe -m pip check
```

A invocação direta dispensa mudar a política de execução do PowerShell.
O download inicial precisa de internet.

Para criar configurações locais somente se ainda não existirem:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
if (!(Test-Path firmware/EstacionamentoCam/config.local.h)) {
    Copy-Item firmware/EstacionamentoCam/config.example.h firmware/EstacionamentoCam/config.local.h
}
```

Para testar com a placa, preencher o Wi-Fi somente em config.local.h e o IP
da câmera em .env. O comando de captura já lê esse endereço. APP_HOST, APP_PORT,
LED_MODE e LOG_LEVEL ficam reservados para etapas futuras.
Veja o roteiro completo em [camera.md](camera.md).

## Firmware

Arduino IDE é o fluxo principal. Abrir firmware/EstacionamentoCam/EstacionamentoCam.ino
e selecionar AI Thinker ESP32-CAM no pacote esp32 by Espressif Systems 2.0.17.
Câmera, Wi-Fi e HTTP são fornecidos por esse pacote; WS2812B será adicionado na integração.
Consulte docs/hardware.md antes de selecionar GPIOs.

Na IDE, clicar em Verificar (✓) compila e Carregar (→) grava na porta selecionada.
Configurar Flash Mode DIO, Flash Frequency 40MHz e Huge APP.
Veja [arduino-ide.md](arduino-ide.md) para instalação e menus.
O arquivo platformio.ini permanece somente para compatibilidade opcional.
A gravação é feita pelo usuário; compilar não confirma funcionamento físico.

## Git e GitHub

Versionar fontes e configurações sem segredos. Conferir `git status --short`
antes de adicionar arquivos. Publicação no GitHub e cadastro de remote dependem
de solicitação posterior; operação local não precisa de GitHub.

## Testes no computador

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Os testes usam imagens sintéticas, transporte simulado e servidor HTTP em
loopback. Não exigem placa, Wi-Fi real ou credenciais; não validam hardware.
Veja tests/README.md para a cobertura e as verificações físicas pendentes.
