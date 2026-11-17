#include <Arduino.h>

#include "app_config.h"
#include "camera.h"

namespace {
bool initialized = false;
}

namespace parking_camera {
bool begin() {
    if (initialized) {
        return true;
    }
    camera_config_t config = {};
    // Pinagem AI-Thinker / OV2640, conforme exemplo oficial Arduino-ESP32 2.0.17.
    config.pin_pwdn = 32;
    config.pin_reset = -1;
    config.pin_xclk = 0;
    config.pin_sccb_sda = 26;
    config.pin_sccb_scl = 27;
    config.pin_d0 = 5;
    config.pin_d1 = 18;
    config.pin_d2 = 19;
    config.pin_d3 = 21;
    config.pin_d4 = 36;
    config.pin_d5 = 39;
    config.pin_d6 = 34;
    config.pin_d7 = 35;
    config.pin_vsync = 25;
    config.pin_href = 23;
    config.pin_pclk = 22;
    config.xclk_freq_hz = 20000000;
    config.ledc_timer = LEDC_TIMER_0;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.pixel_format = PIXFORMAT_JPEG;
    config.jpeg_quality = CAMERA_JPEG_QUALITY;

    const bool has_psram = psramFound();
    config.frame_size = has_psram ? CAMERA_FRAME_SIZE : FRAMESIZE_QVGA;
    config.fb_location = has_psram ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
    config.fb_count = has_psram ? 2 : 1;
    config.grab_mode = CAMERA_GRAB_LATEST;
    if (!has_psram) {
        Serial.println("PSRAM ausente: usando QVGA (320x240) em RAM interna.");
    }
    const esp_err_t result = esp_camera_init(&config);
    if (result != ESP_OK) {
        Serial.printf("Falha ao inicializar camera: %s (0x%x).\n",
                      esp_err_to_name(result), result);
        return false;
    }
    initialized = true;
    Serial.println("Camera inicializada em JPEG; sem processamento de imagem.");
    return true;
}

bool ready() {
    return initialized;
}
}  // namespace parking_camera
