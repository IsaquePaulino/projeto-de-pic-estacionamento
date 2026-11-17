#pragma once

#include "esp_camera.h"

#if __has_include("config.local.h")
#include "config.local.h"
#else
#include "config.example.h"
#endif

// Preserva compatibilidade com a configuracao local migrada do PlatformIO.
#ifndef WIFI_SSID
#define WIFI_SSID ""
#endif
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD ""
#endif
#ifndef CAMERA_FRAME_SIZE
#define CAMERA_FRAME_SIZE FRAMESIZE_VGA
#endif
#ifndef CAMERA_JPEG_QUALITY
#define CAMERA_JPEG_QUALITY 12
#endif
#ifndef CAMERA_HTTP_PORT
#define CAMERA_HTTP_PORT 80
#endif
#ifndef WIFI_RETRY_INTERVAL_MS
#define WIFI_RETRY_INTERVAL_MS 10000
#endif

static_assert(CAMERA_HTTP_PORT > 0 && CAMERA_HTTP_PORT <= 65535, "Porta HTTP invalida.");
static_assert(CAMERA_JPEG_QUALITY >= 0 && CAMERA_JPEG_QUALITY <= 63, "Qualidade JPEG invalida.");
static_assert(WIFI_RETRY_INTERVAL_MS >= 1000, "Intervalo Wi-Fi deve ser >= 1000 ms.");
