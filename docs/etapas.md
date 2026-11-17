# Etapas e validação

## Etapa 1 — Estrutura inicial

Entrega: diretórios, metadados de dependências, PlatformIO, exemplos sem segredos,
10 vagas não calibradas e documentação. Revisão estrutural concluída.
Em 06/11/2026, o usuário confirmou sucesso no Build pelo PlatformIO. Esse registro
é baseado no relato do usuário, sem log de compilação anexado. Não houve teste
físico nem confirmação da instalação das dependências Python.
Não começar a próxima etapa automaticamente.

Critérios para revisão:

- Confirmar fluxo computador -> câmera e computador -> LEDs por HTTP.
- Conferir separação entre ROI da câmera e coordenadas do mapa.
- Manter vagas desconhecidas, detector desativado e LEDs em simulação.
- Confirmar papéis das dependências e comandos de preparação.
- Conferir restrições de GPIO e decisões dependentes da placa real.
- Não presumir instalação, compilação ou validação física.

## Etapa 2 — Câmera (captura confirmada pelo usuário)

Em 09/11/2026, o usuário escolheu Arduino IDE como fluxo principal.
O sketch passou a ser firmware/EstacionamentoCam/EstacionamentoCam.ino, com
módulos C++ na mesma pasta e credenciais locais preservadas e ignoradas pelo Git.
O diagnóstico independente está em firmware/SerialCheck/SerialCheck.ino.
Preparação da Arduino IDE:

Verificação da migração em 09/11/2026: suporte esp32 2.0.17 instalado na Arduino
IDE e ambos os sketches compilados com o Arduino CLI incluído nela. Placa
AI Thinker ESP32-CAM, DIO, 40MHz e Huge APP. Nenhum upload foi feito pelo agente.
As verificações históricas abaixo foram executadas antes dessa migração.

Usuário autorizou a Etapa 2 após confirmar a compilação inicial.
Implementados captura JPEG HTTP, diagnóstico da câmera, conexão/reconexão Wi-Fi,
cliente Python com timeout/validação e comando para salvar capturas.
Não foi implementada detecção ou integração de LEDs.

Verificações no computador:

- Compilação PlatformIO para esp32cam concluída com sucesso.
- Testes de configuração, aquisição, falhas, CLI e HTTP em loopback passaram.
- Instalação editável do backend e pip check passaram.

O log de upload fornecido pelo usuário confirma identificação do ESP32-D0WDQ6
(revisão v1.0), gravação das imagens, verificação dos hashes e resultado SUCCESS
na COM5. Isso confirma a gravação e a comunicação serial no modo de programação;
inicialização do aplicativo, captura e conexão Wi-Fi ainda precisam ser validadas.
Foi acrescentado status serial periódico a cada 5 segundos para que o IP possa
ser consultado mesmo quando o monitor é aberto depois do boot. Essa atualização
precisa de novo upload manual e validação pelo usuário.
Como a saída serial continuou ausente, foi preparado o ambiente separado
esp32cam-serial-check para imprimir um contador, sem câmera, Wi-Fi ou PSRAM.
Sua compilação não confirma execução na placa; upload e observação desse teste
precisam ser realizados pelo usuário.

Em 09/11/2026, o usuário forneceu log de upload do ambiente esp32cam-serial-check
na COM8, com identificação do mesmo ESP32-D0WDQ6, hashes verificados e SUCCESS.
Após esse upload, a leitura do agente na COM8 a 115200 por 12 segundos recebeu
0 bytes. A tentativa de consultar o chip com reset automático também não conectou;
o comando de início por software não chegou a ser executado. Execução do programa
de diagnóstico e saída do modo de gravação continuam sem confirmação.

Pendências na placa: verificar inicialização e conexão Wi-Fi, resolução e orientação,
capturar imagens da maquete e testar queda/reconexão Wi-Fi conforme
[camera.md](camera.md). Esses ensaios não foram realizados pelo agente.
Posteriormente o usuário confirmou funcionamento da câmera, forneceu o endereço
http://192.168.93.205/capture e autorizou vídeo contínuo e teste de ocupação.
Essa confirmação não inclui medição de precisão ou os ensaios de reconexão acima.

## Etapa 3 — Frontend (painel de teste implementado)

Implementados vídeo, regiões coloridas, lista de vagas, contadores e calibração.
Desenho real da maquete, editor de posições do mapa e estados manuais permanecem
pendentes; não foram necessários ao ensaio solicitado.

## Etapa 4 — Integração (API local e simulação implementadas)

Frontend, API, aquisição e detector compartilham estado no computador. LEDs
simulados ficam em memória; o transporte e os testes físicos de LEDs não foram
implementados. Nenhum comando de LED é enviado à ESP32-CAM.

## Etapa 5 — Detecção (implementada para ensaio)

Implementados editor de ROIs convexas, referência vazia explícita e detector
tradicional com ruído/luz/cor/contornos, limiares separados e confirmação temporal.
Mudanças de calibração, resolução e origem invalidam referências incompatíveis.
Validação de precisão com os carros da maquete permanece pendente.

## Etapa 6 — Testes e ajustes (pendente)

Testar posições e tamanhos de veículos, sombras, iluminação variável, LEDs
iluminando a maquete, ruído, movimento da câmera e falhas de rede.
Medir falsos positivos, falsos negativos, precisão por vaga, tempo de resposta
e comportamento desconhecido. Registrar condições e configurações dos ensaios.

Dados sintéticos não substituem validação na maquete. Não há resultados
de precisão ou medições de latência nesta entrega.

O ensaio de navegador passou com fonte sintética, incluindo vídeo, seleção,
referência, livre/ocupada, desconexão/reconexão e telas desktop/mobile.
A tentativa do agente de capturar o IP real deu timeout; o computador estava
em 192.168.15.5 e o endereço informado da câmera era 192.168.93.205.
Não foi alterada a configuração Wi-Fi do firmware.
