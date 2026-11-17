# Etapa 2 — Configurar e testar a câmera

A implementação está pronta para validação com o equipamento. Compilação e
testes no computador não confirmam captura real, estabilidade do Wi-Fi ou
alimentação da placa. Não há detecção de vagas ou acionamento de LEDs nesta etapa.

## 1. Configurar Wi-Fi

Abra um terminal PowerShell e volte à raiz, mesmo se o VS Code estiver aberto
somente na pasta firmware:

```powershell
Set-Location 'C:\Users\isaqu\Documents\picagrande'
if (!(Test-Path firmware/EstacionamentoCam/config.local.h)) {
    Copy-Item firmware/EstacionamentoCam/config.example.h firmware/EstacionamentoCam/config.local.h
}
```

Edite firmware/EstacionamentoCam/config.local.h e preencha estas duas linhas localmente:

```cpp
#define WIFI_SSID "NOME_DA_SUA_REDE"
#define WIFI_PASSWORD "SUA_SENHA"
```

Use uma rede Wi-Fi de 2,4 GHz acessível ao computador e sem isolamento entre
clientes. Não preencher o arquivo config.example.h com dados reais, nem enviar
a senha pelo chat. config.local.h é ignorado pelo Git.
Se a senha tiver aspas ou barras invertidas, escape esses caracteres como
literal C++: aspas com \" e barra com \\.

Sem arquivo local ou com SSID vazio, o Build funciona, mas o dispositivo informa
a configuração ausente no serial e não conecta. Defaults: HTTP porta 80, VGA
640x480 com PSRAM, JPEG qualidade 12. Sem PSRAM, tenta QVGA 320x240 e registra isso.

## 2. Compilar e gravar manualmente

Na Arduino IDE, abra firmware/EstacionamentoCam/EstacionamentoCam.ino:

1. Selecione AI Thinker ESP32-CAM no pacote esp32 by Espressif Systems 2.0.17.
2. Configure Flash Mode DIO, Flash Frequency 40MHz e Huge APP.
3. Selecione a porta USB da placa (última observada: COM8).
4. Clique em Verificar (✓) e depois Carregar (→).
5. Abra Ferramentas > Monitor Serial a 115200 baud.

Veja [arduino-ide.md](arduino-ide.md) para instalação e detalhes. Os módulos C++
ficam ao lado do .ino e são compilados pela IDE, sem copiar/colar todo o código.

A AI-Thinker não tem USB nativo: a ligação depende de usar base ESP32-CAM-MB ou
adaptador USB-serial. Confira o esquema do seu conjunto antes de alimentar.
Em ligação manual, sinais UART devem ter nível de 3,3 V; alimentação de 5 V na
placa não significa que os GPIOs aceitem 5 V.

Se o programador não tiver boot automático, GPIO0 em GND durante o reset seleciona
gravação. Depois do upload, solte GPIO0 de GND e reinicie para executar. Esse
comportamento está descrito na [documentação da Espressif](https://docs.espressif.com/projects/esptool/en/latest/esp32/advanced-topics/boot-mode-selection.html).
A sequência dos botões depende da base/programador utilizado.

No serial, procure:

```text
Camera inicializada em JPEG; sem processamento de imagem.
Wi-Fi conectado. IP: <IP atribuido pelo roteador>
Captura: http://<IP>:80/capture
Servidor HTTP iniciado na porta 80.
```

São mensagens esperadas, não um log obtido da placa deste projeto.
Na versão com diagnóstico periódico, após concluir setup(), aparece uma linha
Status a cada 5 segundos; se o Wi-Fi estiver conectado, o endereço Captura também
é repetido. Abrir o monitor depois do boot e aguardar até 10 segundos permite
ver esse status sem depender de apertar RST. A atualização exige novo upload
manual do firmware. Se a inicialização travar antes de entrar em loop(), o status
periódico não será emitido.

## 3. Testar a imagem no navegador

No computador, abra os endereços abaixo, substituindo o IP pelo informado
no serial:

- http://192.168.1.50/health deve retornar {"camera_ready":true}.
- http://192.168.1.50/capture deve mostrar uma fotografia JPEG.

Atualize /capture enquanto movimenta um objeto para verificar que recebe novas
imagens. Confira se o estacionamento inteiro aparece, se o foco permite ver
os veículos e se a orientação está correta. Não calibrar vagas ainda.

HTTP 503 indica falha de inicialização ou captura, não vaga livre.
Reveja o serial, o encaixe da câmera e a alimentação antes de tentar novamente.
Se a câmera não inicializou no boot, corrigir a causa e reiniciar a placa;
o firmware não tenta reinicializar o sensor automaticamente.

## 4. Capturar pelo computador

Na raiz do projeto, atualize o pacote no ambiente:

```powershell
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"
.\.venv\Scripts\python.exe -m pip check
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Se o ambiente ainda não existir, siga [ambiente.md](ambiente.md) primeiro.
Edite .env com o IP real:

```dotenv
ESP32_BASE_URL=http://192.168.1.50
LED_MODE=simulation
```

Não colocar /capture no endereço: o caminho já está em config/system.json.
Se você alterou CAMERA_HTTP_PORT no firmware, inclua a porta na URL.
Variáveis definidas no processo prevalecem sobre .env.

Execute:

```powershell
.\.venv\Scripts\python.exe -m parking_monitor.capture --count 3
```

Cada captura válida cria um JPEG com nome UTC único em data/captures/. A saída
mostra dimensões, bytes, duração e caminho. Esses arquivos não entram no Git.
O código apenas decodifica para validar: não compara referência nem classifica.
O intervalo de 0,5 s é uma pausa após cada aquisição, não uma taxa garantida.

Para escolher outra pasta:

```powershell
.\.venv\Scripts\python.exe -m parking_monitor.capture --count 5 --output-dir data/ensaio-camera
```

Caminhos relativos são resolvidos a partir da raiz. O comando encerra com código 1
na primeira falha, sem salvar a resposta inválida. Capturas anteriores válidas
permanecem na pasta. Nenhuma captura vira referência vazia automaticamente.

## 5. Validar perdas e reconexão

Depois de obter imagens reais:

1. Faça uma sequência com o objeto mudando de posição; confira os JPEGs salvos.
2. Desligue a câmera e rode uma captura: deve falhar com timeout/erro de rede,
   sem gerar uma nova imagem válida.
3. Religue e confira no serial a conexão. O IP pode mudar; atualize .env.
4. Rode a captura novamente e confirme que voltou a funcionar.
5. Teste desligar/religar o ponto de acesso mantendo a placa ligada para verificar
   as tentativas de reconexão do firmware a cada 10 s.

Registre resolução, orientação, problemas de iluminação/foco e reconexão.
Nenhum desses testes físicos foi executado pelo agente.

## Verificação automatizada

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Há testes com transporte simulado e HTTP em loopback, sem usar a placa.
Eles não medem qualidade da imagem, estabilidade elétrica ou desempenho do Wi-Fi.

## Monitor abre, mas não mostra mensagens

Forçar monitor_dtr=0 e monitor_rts=0 foi testado como hipótese para evitar reset
mantido pelo adaptador, mas não produziu saída nas leituras realizadas.
O projeto voltou ao padrão, sem forçar essas opções. O comportamento depende
do circuito da base, conforme a [documentação da Espressif](https://docs.espressif.com/projects/esptool/en/latest/esp32/advanced-topics/boot-mode-selection.html).
Não foi confirmada uma causa para o silêncio do monitor.

Depois de alterar opções de controle serial, fechar o monitor e abri-lo novamente.
Apertar e soltar RST sem segurar BOOT/IO0. Se foi usado jumper GPIO0-GND para
upload, desligar a alimentação, retirar o jumper, reconectar e reiniciar.
Não é necessário novo upload para aplicar opções do monitor.

Se continuar totalmente em branco, conferir o modelo da base/adaptador e as
ligações físicas antes de alterar firmware ou tentar gravar novamente.

### Teste isolado de CPU e UART

Foi preparado o ambiente esp32cam-serial-check para diagnosticar ausência de saída
serial mesmo após upload verificado. Ele usa apenas Arduino/Serial, sem iniciar
câmera, Wi-Fi, PSRAM, microSD ou LEDs. Compila em separado da aplicação da câmera.
Os testes anteriores de leitura com DTR/RTS e reset automático não receberam bytes;
isso não permite afirmar qual componente está falhando.

O diagnóstico agora também existe como firmware/SerialCheck/SerialCheck.ino.
Na Arduino IDE, abrir esse arquivo e carregar manualmente na placa.
Depois abrir Monitor Serial a 115200 e aguardar
até 5 segundos, com os botões soltos. A saída esperada se a aplicação executar é:

```text
SERIAL_CHECK seq=0 uptime_ms=...
SERIAL_CHECK seq=1 uptime_ms=...
```

Esse texto é um exemplo esperado, não resultado já observado na placa. Se o teste
produzir linhas, investigar em seguida a inicialização dos componentes da aplicação
principal. Se ficar em branco, o próximo diagnóstico será boot, base USB, sinais de
controle e conexão UART, sem atribuir a falha à câmera pelo silêncio do monitor.

Para voltar à câmera, abrir EstacionamentoCam.ino e carregar esse sketch novamente.
O teste isolado não fornece /capture ou /health e não usa credenciais locais.

## Referências técnicas

- [Exemplo de câmera da Espressif, versão 2.0.17](https://github.com/espressif/arduino-esp32/blob/2.0.17/libraries/ESP32/examples/Camera/CameraWebServer/CameraWebServer.ino)
- [Pinagem AI-Thinker na mesma versão](https://github.com/espressif/arduino-esp32/blob/2.0.17/libraries/ESP32/examples/Camera/CameraWebServer/camera_pins.h)
- [Decodificação de imagens no OpenCV](https://docs.opencv.org/4.x/d4/da8/group__imgcodecs.html)
- [Timeouts do HTTPX](https://www.python-httpx.org/advanced/timeouts/)
