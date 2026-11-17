// Abra este arquivo na Arduino IDE.
// Os modulos C++ desta pasta sao compilados automaticamente com o sketch.
#include "parking_app.h"

void setup() {
    parking_app::begin();
}

void loop() {
    parking_app::update();
}
