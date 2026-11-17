#pragma once

// Modelo para config.local.h, ao lado de EstacionamentoCam.ino (ignorado pelo Git).
// Usado como fallback para permitir Build sem credenciais.
// Com SSID vazio, o firmware informa a falta de configuracao e nao conecta.
#define WIFI_SSID ""
#define WIFI_PASSWORD ""

// Parametros opcionais: defaults tambem definidos em app_config.h.
#define CAMERA_FRAME_SIZE FRAMESIZE_VGA
#define CAMERA_JPEG_QUALITY 12
#define CAMERA_HTTP_PORT 80
#define WIFI_RETRY_INTERVAL_MS 10000

// LEDs permanecem sem acionamento nesta etapa.
#define LED_SIMULATION 1
#define LED_DATA_GPIO (-1)  // Sem GPIO definido; candidato GPIO13 em docs/hardware.md.
#define LED_COUNT 10
#define LED_BRIGHTNESS 32  // Escala 0..255; validar na maquete.
#define LED_COMMAND_TIMEOUT_MS 5000
