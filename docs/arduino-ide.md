# Firmware com Arduino IDE

Arduino IDE é o fluxo principal do firmware. Para a primeira instalação completa,
incluindo o painel no computador, siga o [README](../README.md).
Compilar o sketch não confirma, por si só, a execução na placa.

## Instalação do suporte ESP32

Use Arduino IDE 2.x e o pacote esp32 by Espressif Systems na versão 2.0.17.
Essa versão mantém a base usada pelo código do projeto.

Se o pacote não aparecer, em Arquivo > Preferências, adicionar à lista de URLs
adicionais do Gerenciador de Placas:

```text
https://espressif.github.io/arduino-esp32/package_esp32_index.json
```

Depois abrir Ferramentas > Placa > Gerenciador de Placas, procurar esp32,
selecionar o pacote da Espressif e a versão 2.0.17. Procedimento baseado na
[documentação oficial da Espressif](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html).
Não são necessárias bibliotecas adicionais para câmera, Wi-Fi e HTTP.

## Abrir o sketch da câmera

Em Arquivo > Abrir, selecionar:

```text
firmware/EstacionamentoCam/EstacionamentoCam.ino
```

Manter o arquivo nessa pasta. Os arquivos .cpp e .h ao lado dele fazem parte
do mesmo sketch e são compilados automaticamente, conforme a
[especificação de sketches Arduino](https://arduino.github.io/arduino-cli/1.5/sketch-specification/).
O .ino apenas encaminha setup/loop para parking_app.cpp, mantendo os módulos separados.

A configuração Wi-Fi foi movida para EstacionamentoCam/config.local.h, ao lado
do .ino, sem exibir suas credenciais. Se o arquivo local não existir, copiar
config.example.h para config.local.h e preencher WIFI_SSID/WIFI_PASSWORD somente
no arquivo local. Ele é ignorado pelo Git. Usar Wi-Fi 2,4 GHz.

## Placa e opções

| Campo | Valor |
| --- | --- |
| Ferramentas > Placa | esp32 > AI Thinker ESP32-CAM |
| Porta | COM correspondente à base/adaptador USB no seu computador |
| CPU Frequency | 240MHz (WiFi/BT) |
| Flash Mode | DIO |
| Flash Frequency | 40MHz |
| Partition Scheme | Huge APP (3MB No OTA/1MB SPIFFS) |
| Core Debug Level | None |
| Erase All Flash Before Sketch Upload | Disabled |
| Monitor Serial | 115200 baud |

Essa placa já habilita PSRAM pelo pacote; não selecionar outra placa apenas para
procurar um menu PSRAM. As opções estão no
[cadastro oficial da AI Thinker ESP32-CAM na versão 2.0.17](https://github.com/espressif/arduino-esp32/blob/2.0.17/boards.txt).

## Verificar e carregar

1. Encerrar outros monitores seriais que estejam usando a mesma porta.
2. Clicar em Verificar (✓) para compilar.
3. Clicar em Carregar (→) para gravar, por ação do usuário.
4. Após concluir, abrir Ferramentas > Monitor Serial e selecionar 115200 baud.
5. Aguardar o status periódico e o endereço http://IP:80/capture.
6. Abrir esse endereço no navegador de um dispositivo na mesma rede.

O sketch inicializa a câmera e oferece /capture e /health. O vídeo contínuo e a
detecção de ocupação foram acrescentados no computador, sem alterar esse sketch,
conforme [teste-ocupacao.md](teste-ocupacao.md). Ver [camera.md](camera.md)
para validar captura no computador e reconexão.

## Diagnóstico separado

SerialCheck/SerialCheck.ino apenas imprime um contador pela UART.
Não inicializa câmera ou Wi-Fi. Na Arduino IDE, a placa AI Thinker mantém a
configuração de PSRAM do core; a desativação de BOARD_HAS_PSRAM usada no antigo
ambiente PlatformIO não é aplicada automaticamente pelo sketch Arduino.

Gravar SerialCheck substitui temporariamente a aplicação da câmera. Para voltar
à câmera, abrir EstacionamentoCam.ino e carregar esse sketch.

## Situação da validação

Em 09/11/2026, o suporte esp32 2.0.17 foi instalado e sua URL foi configurada
na instalação local da Arduino IDE 2.3.10. Os dois sketches compilaram com sucesso
usando o Arduino CLI 1.5.1 incluído na IDE, para esp32:esp32:esp32cam, DIO,
40MHz, CPU 240MHz e Huge APP. A câmera usou 836845 bytes de programa e o
diagnóstico 279041 bytes. Esses números representam compilação, não teste físico.

Foram fornecidos logs de uploads com hashes verificados usando PlatformIO.
As leituras seriais posteriores não receberam bytes. A migração para Arduino IDE
preserva esse histórico. Posteriormente o usuário confirmou que a câmera funcionou
e forneceu seu endereço HTTP. Precisão de ocupação na maquete ainda não foi medida.
