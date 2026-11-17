# Planejamento do hardware

Documento de projeto; não houve ligação, gravação de firmware ou teste físico
pelo agente. Na Etapa 2 a implementação da câmera/Wi-Fi foi compilada.

## ESP32-CAM AI-Thinker

A câmera ocupa GPIOs 0, 5, 18, 19, 21, 22, 23, 25, 26, 27, 32, 34, 35, 36 e 39,
conforme o bloco AI-Thinker do [exemplo oficial da Espressif](https://github.com/espressif/arduino-esp32/blob/master/libraries/ESP32/examples/Camera/CameraWebServer/camera_pins.h).
Esses sinais não devem ser usados para LEDs. GPIO0 também participa do boot.

O [guia de hardware da Espressif](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32/schematic-checklist.html)
mostra o compartilhamento do SDMMC com GPIOs 2, 4, 12, 13, 14 e 15.
Planejamos manter o microSD desativado e armazenar imagens no computador.

| Recurso | Restrição de projeto |
| --- | --- |
| Câmera | Preservar todos os sinais listados acima |
| Flash/PSRAM | Reservar sinais de memória; não reutilizar GPIO16/17 |
| microSD | Não inicializar SD/SD_MMC ao usar GPIOs compartilhados |
| GPIO4 | Reservar para o flash branco da placa |
| GPIO1 e GPIO3 | Preservar UART/programação e diagnóstico |
| GPIO0, 2, 12 e 15 | Evitar para LEDs por funções de boot/strapping |
| GPIO13 | Candidato ao sinal WS2812B, com microSD desativado |

GPIO13 é uma escolha inferida da ausência de conflito com a câmera e da
desativação do SD, não uma validação elétrica da placa real. Confirmar revisão,
esquema e marcações antes da ligação. A configuração mantém GPIO=-1 e simulação.
GPIO12 tem outra restrição: seu nível no boot seleciona a tensão VDD_SDIO,
conforme os [requisitos de pull-up da Espressif](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/sd_pullup_requirements.html).
Não alterar eFuses para contornar a escolha de GPIO.

## Cadeia WS2812B proposta

Um único GPIO atende a cadeia: ESP32 -> conversor de nível -> DIN do LED 0;
DOUT do LED 0 -> DIN do LED 1, e assim por diante. led_index identifica a posição
física a partir de zero. Confirmar a ordem de cor exigida pelo dispositivo
(frequentemente GRB); a API trabalhará sempre com RGB.

O plano segue as [boas práticas da Adafruit para NeoPixels](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices):
fonte regulada adequada, terra comum, conversão do sinal de 3,3 V para o nível
exigido pelos LEDs a 5 V, resistor de 300 a 500 ohms no sinal junto ao primeiro LED
e capacitor de 500 a 1000 microfarads na alimentação da cadeia. Usar conversor
compatível com o sinal, como 74AHCT125.

Dimensionar a fonte pelo datasheet do lote e pela quantidade de LEDs. Não alimentar
a cadeia pelo pino de 3,3 V da ESP32-CAM. Conferir queda de tensão ao expandir.
O brilho será conservador até os ensaios; não presumir corrente pelo brilho médio.

Primeiro validar captura estável. Depois testar cadeia curta, índices e
interferência na alimentação e imagem. A luz dos LEDs pode afetar a ROI:
posicionar LEDs fora da região analisada ou criar máscaras na calibração.

## Simulação e estado desconhecido

Na Etapa 4, o backend começará em LED_MODE=simulation e apenas registrará comandos.
O firmware terá LED_SIMULATION=1 como proteção adicional e não inicializará o pino.
Modo hardware exigirá configuração explícita em ambos os lados.
Ao iniciar em hardware ou perder comandos por 5 s, deverá indicar amarelo.

Não há transporte simulado nem controle físico de LEDs implementado na Etapa 2.

## Referências da base de firmware

- [Board esp32cam no PlatformIO](https://docs.platformio.org/en/stable/boards/espressif32/esp32cam.html)
- [Release espressif32 6.13.0 e frameworks incluídos](https://github.com/platformio/platform-espressif32/releases/tag/v6.13.0)
- [Biblioteca candidata Adafruit NeoPixel](https://github.com/adafruit/Adafruit_NeoPixel)

O endereço antigo de esquema no site AI-Thinker redirecionou ao portal durante
a consulta. Não foi possível confirmar por ele a revisão da placa. Essa
conferência permanece pendente antes da ligação física.
