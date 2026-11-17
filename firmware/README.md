# Firmware ESP32-CAM

Alvo: AI-Thinker ESP32-CAM com OV2640, C++ e Arduino IDE.
Abrir EstacionamentoCam/EstacionamentoCam.ino; os módulos C++ ficam na mesma pasta.
O firmware inicializa a câmera, conecta ao Wi-Fi e serve JPEGs por HTTP.
Não usa microSD, flash branco, WS2812B ou processamento de imagem.

A base é o pacote esp32 by Espressif Systems 2.0.17 na Arduino IDE.
Antes da migração, o agente compilou a implementação da Etapa 2 com sucesso,
incluindo a linkagem do caminho Wi-Fi com SSID fictício temporário, removido
após a verificação. O usuário confirmou o upload na placa. Inicialização do sensor,
conexão Wi-Fi e captura real continuam sem confirmação; o agente não fez upload
nem teste físico.

A captura usa `esp_camera.h`, e a rede usa `WiFi.h` e `esp_http_server.h`
fornecidos pelo framework. Não instalar outro driver de câmera em paralelo.
A biblioteca WS2812B será adicionada na Etapa 4; candidata: Adafruit NeoPixel,
com versão fixada após verificar a compatibilidade com esta base.

Copie `EstacionamentoCam/config.example.h` para `EstacionamentoCam/config.local.h` e preencha as
credenciais localmente. app_config.h prioriza o arquivo local; sem ele, compila
usando o exemplo com SSID vazio e informa a configuração ausente no serial.
Nenhuma senha é impressa pelo código.
Depois de concluir setup(), o firmware informa o estado da câmera, Wi-Fi e HTTP
a cada 5 segundos. Se conectado, repete também o endereço de captura. Assim,
abrir o monitor depois do boot não faz perder definitivamente a informação do IP.
Há uma mensagem antes da inicialização da câmera para ajudar a localizar travas
nessa fase. A versão com diagnóstico periódico precisa de novo upload manual.

Com PSRAM, usa VGA (640x480) por padrão, JPEG qualidade 12 e dois buffers.
Sem PSRAM, tenta QVGA (320x240) na RAM interna e informa o fallback no serial.
Não inverter/espelhar imagens automaticamente: conferir orientação na maquete.

Rotas:

- `GET /capture`: JPEG sem cache, com dimensões nos headers X-Frame-Width/Height.
- `GET /health`: JSON camera_ready; HTTP 503 se a câmera não inicializou.

O HTTP inicia mesmo com falha de câmera para permitir diagnóstico, desde que
o Wi-Fi conecte. Falha de captura responde 503. Os buffers são devolvidos ao
driver mesmo se o envio falhar. O firmware tenta reconectar Wi-Fi a cada 10 s.

O número de LEDs será configurado no dispositivo e deverá cobrir todos os índices
de `config/parking.json`. Não é limite para o número de vagas no computador.

Leia `../docs/hardware.md` antes de escolher um GPIO.
Use Verificar (✓) para compilar e Carregar (→) para gravar na Arduino IDE.
Configuração da IDE: [arduino-ide.md](../docs/arduino-ide.md).
Gravação manual e ensaios: [camera.md](../docs/camera.md).

## Diagnóstico isolado de serial

O sketch SerialCheck/SerialCheck.ino não inicializa câmera, Wi-Fi, microSD ou LEDs. Seu único
comportamento é imprimir SERIAL_CHECK, sequência e uptime a cada segundo.

Para testar na Arduino IDE, abrir SerialCheck.ino e clicar em Carregar.
Depois, abrir o Monitor Serial a 115200. O log fornecido pelo usuário em 09/11/2026
confirma upload e verificação desse ambiente na COM8. A leitura posterior não
recebeu bytes; a execução do contador ainda não foi confirmada.

Ao terminar o diagnóstico, abrir EstacionamentoCam.ino e carregar para restaurar
a aplicação da câmera. Cada sketch possui somente um par setup/loop.

platformio.ini foi mantido como compatibilidade opcional e aponta para essas
pastas. Naquele ambiente de diagnóstico, BOARD_HAS_PSRAM é desativado; essa opção
não é aplicada automaticamente ao abrir SerialCheck na Arduino IDE.
