#include <Arduino.h>
#include <WiFi.h>

#include "app_config.h"
#include "camera.h"
#include "camera_server.h"
#include "parking_app.h"

namespace {
bool configured = false;
bool was_connected = false;
bool server_started = false;
unsigned long last_wifi_attempt = 0;
unsigned long last_server_attempt = 0;
unsigned long last_status_report = 0;
bool first_server_attempt = true;

void connect_wifi() {
    last_wifi_attempt = millis();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.println("Conectando ao Wi-Fi (rede 2,4 GHz)...");
}

void report_status(bool connected) {
    const char* wifi_state = !configured ? "nao configurado"
                                        : (connected ? "conectado" : "desconectado");
    Serial.printf("Status: camera=%s; Wi-Fi=%s; HTTP=%s; uptime=%lu s\n",
                  parking_camera::ready() ? "inicializada" : "falha",
                  wifi_state, server_started ? "iniciado" : "aguardando",
                  millis() / 1000UL);
    if (connected) {
        Serial.printf("Captura: http://%s:%d/capture\n",
                      WiFi.localIP().toString().c_str(), CAMERA_HTTP_PORT);
    }
}
}

namespace parking_app {
void begin() {
    Serial.begin(115200);
    delay(300);
    Serial.println("\nMonitoramento de estacionamento - Etapa 2.");
    Serial.println("Inicializando camera; diagnostico periodico de 5 s apos o setup.");
    Serial.flush();
    // Sem SD, flash branco ou LEDs WS2812B nesta etapa.
    parking_camera::begin();
    if (WIFI_SSID[0] == '\0') {
        Serial.println("SSID vazio. Configure config.local.h na pasta EstacionamentoCam.");
        return;
    }
    configured = true;
    WiFi.persistent(false);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    connect_wifi();
}

void update() {
    const bool connected = configured && WiFi.status() == WL_CONNECTED;
    if (millis() - last_status_report >= 5000) {
        last_status_report = millis();
        report_status(connected);
    }
    if (!configured) {
        delay(100);
        return;
    }
    if (connected && !was_connected) {
        Serial.printf("Wi-Fi conectado. IP: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("Captura: http://%s:%d/capture\n",
                      WiFi.localIP().toString().c_str(), CAMERA_HTTP_PORT);
    } else if (!connected && was_connected) {
        Serial.println("Wi-Fi desconectado; tentando reconectar.");
    }
    was_connected = connected;
    if (!connected && millis() - last_wifi_attempt >= WIFI_RETRY_INTERVAL_MS) {
        WiFi.disconnect(false, false);
        connect_wifi();
    }
    if (connected && !server_started &&
        (first_server_attempt || millis() - last_server_attempt >= 5000)) {
        first_server_attempt = false;
        last_server_attempt = millis();
        server_started = camera_server::begin();
    }
    delay(20);
}
}  // namespace parking_app
