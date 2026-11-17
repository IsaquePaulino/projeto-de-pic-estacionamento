# Projeto de PIC Estacionamento

Sistema local para uma maquete com 10 vagas iniciais, expansível por configuração.
A ESP32-CAM AI-Thinker com OV2640 captura imagens. O computador executa o painel
e processa as imagens com Python e OpenCV tradicional, sem IA. LEDs físicos
ainda não são controlados; o estado deles fica somente em simulação.

## Primeira instalação em outro computador (Windows)

Este roteiro prepara a placa pela **Arduino IDE** e o painel pelo **Python**.
O frontend é servido pelo próprio backend: não precisa de Node.js, npm,
PlatformIO ou Live Server. A Arduino IDE grava o programa na placa; o computador
precisa continuar executando o servidor para mostrar vídeo e analisar as vagas.

### 1. O que instalar e o que receber

- Arduino IDE 2.x.
- Python **3.12**, com o Python Launcher (`py`) disponível no Windows.
- Navegador atualizado e internet para baixar as dependências na instalação.
- ESP32-CAM AI Thinker com câmera OV2640, cabo USB de dados e base/programador
  compatível, como ESP32-CAM-MB.
- A pasta completa do projeto, incluindo `firmware`, `backend`, `frontend`,
  `config`, `.env.example` e `iniciar-monitor.bat`.

Se recebeu um ZIP, extraia antes de começar. Nos comandos abaixo usamos
`C:\Projetos\picagrande` como exemplo: substitua pelo local onde você extraiu.
Não copie a `.venv` de outro computador: ela será criada no passo 5.

### 2. Instalar a placa na Arduino IDE

1. Abra **Arquivo > Preferências** e acrescente esta URL em **URLs adicionais
   para Gerenciadores de Placas**:

   ```text
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```

2. Abra o **Gerenciador de Placas**, procure **esp32 by Espressif Systems** e
   instale a versão **2.0.17**, base usada por este projeto.
3. Em **Arquivo > Abrir**, abra:

   ```text
   firmware/EstacionamentoCam/EstacionamentoCam.ino
   ```

Mantenha todos os `.cpp` e `.h` na mesma pasta do `.ino`. Não copie apenas o
conteúdo do `.ino` para um sketch vazio. Wi-Fi, câmera e servidor HTTP já vêm
com o pacote ESP32; não é preciso instalar bibliotecas adicionais para o sketch.

### 3. Configurar o Wi-Fi da ESP32

Na pasta `firmware/EstacionamentoCam`, faça uma cópia de `config.example.h`
com o nome **`config.local.h`**. Edite somente o arquivo local:

```cpp
#define WIFI_SSID "NOME_DA_SUA_REDE"
#define WIFI_PASSWORD "SUA_SENHA"
```

O nome é o SSID da rede, respeitando maiúsculas e minúsculas. A ESP32-CAM
precisa de Wi-Fi **2,4 GHz**, e o computador precisa alcançar a placa pela rede.
Evite redes de visitantes com isolamento entre dispositivos. O computador pode
usar 5 GHz se o roteador permitir comunicação com a rede de 2,4 GHz.

Se o arquivo local já veio na cópia recebida, confira e troque as credenciais
para as da sua rede. Não altere o exemplo nem compartilhe o arquivo com a senha.
No Windows, confirme que o nome não ficou `config.local.h.txt`.

### 4. Compilar, fazer upload e descobrir o IP

Conecte a placa ao computador e configure na Arduino IDE:

| Opção | Valor |
| --- | --- |
| Placa | **AI Thinker ESP32-CAM** |
| Porta | COM correspondente à sua base/adaptador USB |
| CPU Frequency | 240MHz (WiFi/BT) |
| Flash Mode | DIO |
| Flash Frequency | 40MHz |
| Partition Scheme | Huge APP (3MB No OTA/1MB SPIFFS) |
| Monitor Serial | 115200 baud |

A porta varia conforme o computador; não precisa ser COM8. Algumas opções já
vêm definidas pela placa selecionada.

1. Clique em **Verificar (✓)** e aguarde a compilação.
2. Feche outros monitores seriais que usem a mesma porta.
3. Clique em **Carregar (→)** e aguarde a conclusão do upload.
4. Abra **Ferramentas > Monitor Serial**, selecione **115200** e pressione
   **RST/RESET** na placa, se necessário.
5. Procure a mensagem de conexão Wi-Fi e anote o endereço de captura.

Exemplo ilustrativo, para substituir pelo IP mostrado na sua placa:

```text
http://192.168.1.50:80/capture
```

Abra esse endereço no navegador do computador. Deve aparecer uma **foto**.
O vídeo contínuo e os botões de delimitação ficam no painel do próximo passo.

Se o upload ficar em `Connecting...` ou apresentar `No serial data received`,
confira porta, cabo e modo de gravação da sua base. Em programadores sem boot
automático, GPIO0 ligado a GND durante o reset seleciona gravação; depois do
upload, solte essa ligação e reinicie para executar. A sequência dos botões
depende do programador. Veja [o guia da câmera](docs/camera.md) antes de alterar
ligações ou alimentação.

### 5. Preparar o painel no computador

Abra o **PowerShell na raiz do projeto**, onde estão `backend`, `frontend` e
`iniciar-monitor.bat`. Execute:

```powershell
Set-Location 'C:\Projetos\picagrande'
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ./backend
.\.venv\Scripts\python.exe -m pip check
if (!(Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

No Bloco de Notas, substitua **ESP32_BASE_URL** pelo IP anotado no passo 4.
Salve e feche. Exemplo:

```dotenv
ESP32_BASE_URL=http://192.168.1.50
```

Use somente a origem: **sem `/capture` no final**. Esse IP é um exemplo;
não use o endereço antigo de outro computador ou de outra rede.
Se o IP da câmera mudar, atualize `.env` e reinicie o servidor.

Não é necessário ativar a `.venv` nem alterar a política de execução do
PowerShell. Não instale `opencv-python` junto de `opencv-python-headless`;
a instalação acima já inclui a variante usada pelo projeto.

### 6. Iniciar o frontend e o backend

Na raiz, dê dois cliques em **`iniciar-monitor.bat`** ou execute no PowerShell:

```powershell
.\iniciar-monitor.bat
```

Mantenha a janela aberta e acesse **http://127.0.0.1:8000** no navegador.
Esse é o painel com vídeo e seleção de vagas. Não abra `frontend/index.html`
diretamente nem use `/capture` da placa para procurar os botões.

Como alternativa ao `.bat`, o comando equivalente é:

```powershell
.\.venv\Scripts\python.exe -m uvicorn parking_monitor.app:app --host 127.0.0.1 --port 8000
```

Execute apenas uma instância do servidor. Para encerrar, pressione **Ctrl+C**
na janela do servidor. Nos próximos usos, ligue a câmera, confira o IP e execute
o `.bat` novamente; a instalação das dependências é feita só na preparação.
Não precisa regravar a placa a cada vez que abrir o painel.

### 7. Delimitar a vaga e testar a ocupação

1. Fixe a câmera apontando para a maquete, sem movimentá-la durante o teste.
2. No painel, aguarde **Câmera conectada** e escolha uma vaga, por exemplo **V01**.
3. Clique em **Selecionar região na imagem**. A imagem ficará congelada.
4. Clique em **quatro cantos distintos** da vaga e depois em **Salvar região**.
   O painel organiza o contorno automaticamente. Use **Remover último ponto**
   se precisar corrigir.
5. Repita nas outras vagas desejadas. Você pode começar com uma só.
6. Retire os carros de todas as regiões calibradas, marque a confirmação de que
   estão vazias e clique em **Capturar referência vazia**.
7. Clique em **Iniciar análise**. Coloque e retire um carro para observar
   **Livre**, **Ocupada** e os contadores.

As vagas sem região continuam **Desconhecidas**. Se a cópia do projeto já tiver
regiões de outra maquete, refaça as seleções antes de criar a referência e iniciar
a análise. Uma referência vazia não deve conter carros nas vagas.
Ao mover a câmera ou mudar o enquadramento, refaça a calibração e a referência.

O teste mede diferenças na região: outros objetos também podem causar ocupação.
Não há reconhecimento de placa/modelo de veículo. Veja o
[roteiro completo de ocupação](docs/teste-ocupacao.md) para ajustar a sensibilidade.

### Problemas comuns

| Sintoma | O que conferir |
| --- | --- |
| `py` não reconhecido ou Python 3.12 ausente | Instale Python 3.12 com o launcher e reabra o PowerShell. |
| `.venv` não encontrada ao abrir o `.bat` | Execute o passo 5 a partir da raiz do projeto. |
| `No module named parking_monitor` ou `uvicorn` | Refaça a instalação com `.venv\Scripts\python.exe -m pip install -e ./backend`. |
| Porta COM ausente ou acesso negado | Confira cabo de dados, driver da base e feche outros monitores seriais. |
| Sem mensagens após o upload | Monitor em 115200, reset e placa fora do modo de gravação. |
| `/capture` não abre | Confira IP atual, alimentação, Wi-Fi e comunicação entre os dispositivos. |
| Painel abre, mas mostra câmera desconectada | Confira `.env`, teste `/capture` no mesmo computador e reinicie o servidor após editar o IP. |
| Não aparecem os botões de delimitação | Abra `http://127.0.0.1:8000`, o painel do computador. |
| Não consegue salvar a região | Marque quatro cantos distintos, confira a mensagem no painel e atualize com Ctrl+F5. |
| Porta 8000 em uso | Feche a instância anterior do servidor antes de abrir outra. |

### Compartilhar o projeto sem dados locais

Ao montar um ZIP, exclua `.venv`, `.env`, todos os `config.local.h`, builds e
conteúdos de `data/` (capturas, referências e logs). O `.gitignore` evita inclusão
normal pelo Git, mas **não filtra um ZIP criado pelo Explorador de Arquivos**.
Mantenha os exemplos `.env.example` e `config.example.h`; cada pessoa cria seus
arquivos locais e a própria referência seguindo este roteiro.

## Estado do projeto

**Vídeo contínuo e teste de ocupação implementados no computador.** O usuário
confirmou que a câmera funcionou e autorizou o ensaio de ocupação e a atualização
contínua da imagem. O firmware continua fornecendo JPEG em /capture, sem IA ou
processamento de ocupação na placa. Após configurar e gravar o firmware, abrir
o painel não exige novo upload.

FastAPI compartilha uma aquisição entre o vídeo MJPEG, o editor de regiões e o
detector OpenCV. A tela permite calibrar vagas, capturar referência vazia, ajustar
limiares e observar estados/contadores. LEDs permanecem somente em simulação.

Testes automatizados e ensaio de navegador com fonte sintética passaram. Precisão
com carros reais/maquete ainda não foi medida pelo agente.
O fluxo de firmware continua sendo a Arduino IDE.

## Abrir o painel de teste

1. Conectar o computador à mesma rede acessível pela ESP32-CAM.
2. Conferir ESP32_BASE_URL no arquivo local .env, sem /capture.
3. Executar `iniciar-monitor.bat` na raiz do projeto.
4. Abrir **http://127.0.0.1:8000** no navegador do computador.
5. Selecionar uma vaga, marcar quatro cantos, capturar referência vazia e iniciar a análise.

Em outra instalação, configure o IP atual da sua câmera conforme o roteiro acima.
O endpoint /capture continua sendo uma fotografia; o vídeo está no painel e em
/api/video do computador. A taxa depende da aquisição, do Wi-Fi e do processamento.
Leia o [roteiro do teste de ocupação](docs/teste-ocupacao.md).

## Organização

| Caminho | Responsabilidade |
| --- | --- |
| `firmware/` | Sketch Arduino IDE, módulos C++ e configuração local |
| `backend/` | Aquisição compartilhada, API, vídeo, configuração e detector OpenCV |
| `frontend/` | Tela local de vídeo, calibração e teste, em HTML/CSS/JavaScript |
| `config/` | Parâmetros, 10 vagas, coordenadas independentes e LEDs associados |
| `docs/` | Arquitetura, comunicação, configuração, ambiente, hardware e etapas |
| `tests/` | Testes de aquisição, API, detector, persistência e ensaio de navegador |
| `data/` | Referências e capturas locais, ignoradas pelo Git |
| `AGENTS.md` | Regras para futuras contribuições |

## Como os componentes se comunicam

1. O backend solicita imagens JPEG por HTTP à ESP32-CAM na rede Wi-Fi.
2. O computador compara regiões calibradas com uma referência das vagas vazias,
   filtra ruído e confirma mudanças em capturas consecutivas.
3. O frontend consulta a API local para atualizar regiões, cores e contadores.
4. Neste teste, o backend registra as cores dos LEDs em memória, sem acessar a
   placa para controlá-los. O transporte físico por HTTP continua planejado.

O frontend é servido pelo FastAPI, na mesma origem da API. O navegador
do painel não acessa diretamente a ESP32-CAM. A operação não depende de nuvem ou serviços
pagos; a preparação do ambiente precisará de internet para baixar dependências.

## Preparação e documentação

Use Python 3.12, Git e Arduino IDE 2.x com suporte esp32 by Espressif Systems 2.0.17.
Abra [EstacionamentoCam.ino](firmware/EstacionamentoCam/EstacionamentoCam.ino).
Selecione AI Thinker ESP32-CAM, Flash Mode DIO, Flash Frequency 40MHz e
Huge APP. Veja [o guia da Arduino IDE](docs/arduino-ide.md).
Os comandos para Windows estão em [docs/ambiente.md](docs/ambiente.md).
Para testar a câmera, configure o Wi-Fi do firmware e o IP em .env conforme
[docs/camera.md](docs/camera.md). A partir da raiz:

```powershell
.\.venv\Scripts\python.exe -m parking_monitor.capture --count 3
```

As imagens do comando serão salvas em data/captures/. Para o vídeo, usar o painel
local; /capture na ESP32-CAM continua disponível para fotografias individuais.

As dependências do backend estão em [backend/pyproject.toml](backend/pyproject.toml).
O frontend usa recursos nativos do navegador, sem Node.js ou CDN.

- [Arquitetura e contratos HTTP propostos](docs/arquitetura.md)
- [Configuração e teste da câmera — Etapa 2](docs/camera.md)
- [Arduino IDE: abrir, compilar e gravar](docs/arduino-ide.md)
- [Vídeo contínuo e teste de ocupação](docs/teste-ocupacao.md)
- [Configurações, coordenadas e estados](docs/configuracao.md)
- [GPIOs e planejamento dos LEDs](docs/hardware.md)
- [Preparação do ambiente](docs/ambiente.md)
- [Etapas e critérios de validação](docs/etapas.md)

Credenciais reais devem existir apenas em `.env` e
`firmware/EstacionamentoCam/config.local.h`, ambos ignorados pelo Git. Os exemplos
versionados contêm apenas valores vazios ou de demonstração.
