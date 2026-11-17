#include <Arduino.h>
#include <memory>

#include "app_config.h"
#include "camera.h"
#include "camera_server.h"
#include "esp_http_server.h"

namespace {
httpd_handle_t server = nullptr;

struct ReturnFrame {
    void operator()(camera_fb_t* frame) const {
        if (frame) {
            esp_camera_fb_return(frame);
        }
    }
};
using Frame = std::unique_ptr<camera_fb_t, ReturnFrame>;

esp_err_t unavailable(httpd_req_t* request) {
    httpd_resp_set_status(request, "503 Service Unavailable");
    httpd_resp_set_type(request, "text/plain; charset=utf-8");
    httpd_resp_set_hdr(request, "Cache-Control", "no-store");
    return httpd_resp_sendstr(request, "Camera indisponivel. Confira o monitor serial.");
}

esp_err_t health_handler(httpd_req_t* request) {
    const bool ready = parking_camera::ready();
    httpd_resp_set_type(request, "application/json");
    httpd_resp_set_hdr(request, "Cache-Control", "no-store");
    if (!ready) {
        httpd_resp_set_status(request, "503 Service Unavailable");
    }
    return httpd_resp_sendstr(request, ready ? "{\"camera_ready\":true}"
                                            : "{\"camera_ready\":false}");
}

esp_err_t capture_handler(httpd_req_t* request) {
    if (!parking_camera::ready()) {
        return unavailable(request);
    }
    // Descarta um quadro enfileirado antes de obter o que sera transmitido.
    // O tempo do sensor continua sendo relativo ao boot, nao ao relogio do PC.
    {
        Frame queued(esp_camera_fb_get());
        if (!queued) {
            return unavailable(request);
        }
    }
    Frame frame(esp_camera_fb_get());
    if (!frame || frame->len == 0 || frame->format != PIXFORMAT_JPEG) {
        return unavailable(request);
    }

    char width[16];
    char height[16];
    snprintf(width, sizeof(width), "%u", static_cast<unsigned>(frame->width));
    snprintf(height, sizeof(height), "%u", static_cast<unsigned>(frame->height));
    httpd_resp_set_type(request, "image/jpeg");
    httpd_resp_set_hdr(request, "Cache-Control", "no-store, max-age=0");
    httpd_resp_set_hdr(request, "X-Frame-Width", width);
    httpd_resp_set_hdr(request, "X-Frame-Height", height);
    // O buffer e devolvido mesmo se a conexao cair durante o envio.
    return httpd_resp_send(request, reinterpret_cast<const char*>(frame->buf), frame->len);
}
}  // namespace

namespace camera_server {
bool begin() {
    if (server) {
        return true;
    }
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = CAMERA_HTTP_PORT;
    config.stack_size = 8192;
    config.recv_wait_timeout = 2;
    config.send_wait_timeout = 2;
    config.lru_purge_enable = true;
    esp_err_t result = httpd_start(&server, &config);
    if (result != ESP_OK) {
        server = nullptr;
        Serial.printf("Falha ao iniciar HTTP: %s.\n", esp_err_to_name(result));
        return false;
    }
    httpd_uri_t capture = {};
    capture.uri = "/capture";
    capture.method = HTTP_GET;
    capture.handler = capture_handler;
    httpd_uri_t health = {};
    health.uri = "/health";
    health.method = HTTP_GET;
    health.handler = health_handler;
    result = httpd_register_uri_handler(server, &capture);
    if (result == ESP_OK) {
        result = httpd_register_uri_handler(server, &health);
    }
    if (result != ESP_OK) {
        httpd_stop(server);
        server = nullptr;
        Serial.printf("Falha ao registrar rotas HTTP: %s.\n", esp_err_to_name(result));
        return false;
    }
    Serial.printf("Servidor HTTP iniciado na porta %d.\n", CAMERA_HTTP_PORT);
    return true;
}
}  // namespace camera_server
