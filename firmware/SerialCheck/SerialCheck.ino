#include <Arduino.h>

// Sketch independente para abrir na Arduino IDE.
// Sem inicializacao de camera, Wi-Fi, microSD ou acionamento de LEDs.
namespace {
unsigned long sequence = 0;
}

void setup() {
    Serial.begin(115200);
    delay(300);
    Serial.println("SERIAL_CHECK: diagnostico UART iniciado.");
}

void loop() {
    Serial.printf("SERIAL_CHECK seq=%lu uptime_ms=%lu\n", sequence++, millis());
    Serial.flush();
    delay(1000);
}
