# Vídeo contínuo e teste de ocupação

O painel usa a câmera já gravada: solicita JPEGs continuamente e entrega um fluxo
MJPEG ao navegador. Todo o detector roda no computador com OpenCV tradicional.
Não é necessário novo upload nem alterar o Wi-Fi do firmware para este teste.

## 1. Conferir a rede

O computador precisa acessar o endereço da câmera. No .env local foi configurado:

```dotenv
ESP32_BASE_URL=http://192.168.93.205
```

Esse foi o endereço informado pelo usuário; não é um IP fixo obrigatório.
Se o roteador atribuir outro IP, atualizar somente ESP32_BASE_URL e reiniciar o
backend. O arquivo config.local.h continua com as credenciais anteriores da placa.

Na verificação do agente, o computador tinha 192.168.15.5 e a requisição ao IP
informado da câmera deu timeout. Para o ensaio físico, conectar o computador
à rede da ESP32 ou fornecer uma rota válida entre as redes. Primeiro conferir
no próprio navegador do computador se http://192.168.93.205/capture abre a imagem.

## 2. Iniciar

Na raiz, executar iniciar-monitor.bat e manter a janela aberta. Abrir:

```text
http://127.0.0.1:8000
```

O mesmo processo serve a página, a API e o vídeo. Para encerrar, usar Ctrl+C na
janela do servidor. O painel é local ao computador por padrão.

Em um ambiente ainda não preparado:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev]"
.\.venv\Scripts\python.exe -m uvicorn parking_monitor.app:app --host 127.0.0.1 --port 8000
```

O vídeo do computador está em /api/video. O /capture da placa continua sendo
uma fotografia individual; abrir o painel em vez de recarregar essa fotografia.
O vídeo usa uma única aquisição compartilhada, inclusive com vários espectadores.
Não iniciar vários workers/instâncias do backend sobre os mesmos arquivos.

## 3. Calibrar pelo menos uma vaga

1. Fixar câmera, enquadramento, foco e iluminação.
2. Escolher V01 no painel e clicar em Selecionar região na imagem.
3. A imagem congela. Clicar em quatro cantos distintos da vaga; o painel organiza o contorno automaticamente.
4. Clicar em Salvar região. Usar Remover último ponto se houver engano.
5. Repetir nas demais vagas desejadas.

Regiões devem ser convexas, sem cruzar lados, e representar a vaga inteira.
Se houver ponto repetido, interior ou uma região pequena demais, o painel explica
o erro e mantém a seleção para corrigir com Remover último ponto.
Deixar parte do fundo fora das regiões ajuda a estimar variações de iluminação.
Uma vaga sem região continua desconhecida. É possível testar só V01; as outras
nove ficam desconhecidas. Não são necessárias coordenadas fictícias.

O cadastro é salvo em config/parking.json, com pontos normalizados e dimensões da
imagem. Posições do mapa são independentes e não mudam. Alterar regiões pausa a
análise e invalida a referência anterior. Mudar resolução exige nova calibração;
salvar a primeira ROI na resolução nova limpa as ROIs antigas das demais vagas.

## 4. Capturar a referência vazia

Retirar os carros das regiões calibradas, marcar a confirmação de que estão vazias
e clicar em Capturar referência vazia. A imagem JPEG e seus metadados ficam em
data/reference/. Não são versionados e não são criados automaticamente no boot.

Os metadados incluem hash da imagem e da calibração/endereço. Referência alterada,
calibração diferente ou outro endereço impedem reutilizar um arquivo incompatível.
Não capturar referência com o carro estacionado: isso ensinaria o estado errado
ao comparador, que não conhece semanticamente o que é carro.

## 5. Rodar o ensaio

Clicar em Iniciar análise. A vaga deve ficar livre após capturas consecutivas.
Colocar o carro dentro da região e observar a mudança para ocupada; retirar e
verificar o retorno a livre. As cores aparecem no vídeo e na lista.
Contadores incluem vagas desconhecidas, e os LEDs ficam somente em simulação.

A imagem é atualizada sem recarregar a página. O número de quadros por segundo
mostrado é medido pelo backend. preview_interval_seconds=0.1 é uma pausa entre
aquisições, não garantia de 10 ou 30 FPS. A análise tem cadência própria de 0.3 s;
confirmação de 4 capturas não é uma medição do tempo de resposta físico.

Em Ajustar a sensibilidade é possível editar intensidade, porcentagens livre/
ocupada e número de confirmações. Livre deve ter limiar menor que ocupado.
Reduzir limiares aumenta sensibilidade e pode aumentar falsos positivos.

## Como o detector funciona

- Suavização gaussiana e diferença em relação à referência.
- Compensação de luminosidade estimada no fundo fora das ROIs.
- Diferenças de intensidade e de cromaticidade normalizada.
- Abertura/fechamento morfológicos para reduzir ruído.
- Evidência adicional de cor ou novos contornos antes de confirmar ocupação.
- Limiar separado para livre/ocupado e capturas consecutivas.

Sombras uniformes não bastam como evidência; mudanças fortes de iluminação,
imagem escura/saturada, resolução diferente ou deslocamento global estimável
produzem estado desconhecido. Câmera desconectada invalida estados imediatamente;
uma imagem vencida também não pode ser tratada como vaga livre.

Ainda podem ocorrer erros por sombras complexas, reflexos, pouca textura,
movimentos pequenos da câmera ou carros parecidos com o piso. Outros objetos
também podem ocupar a região. Este é um detector de ocupação, sem classificação
semântica de veículos ou identificação de modelo/placa.

## Testes e limites da validação

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

O ensaio de navegador usa Chrome e o extra opcional ui:

```powershell
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev,ui]"
.\.venv\Scripts\python.exe tests/ui_smoke.py
```

Esse ensaio usa fonte sintética, configurações temporárias e HTTP em loopback.
Testa vídeo, quatro pontos, referência, estados e perda/reconexão. Não usa a
câmera real nem altera a calibração do projeto. Imagens de QA ficam em data/qa/.

O usuário confirmou a captura física da câmera anteriormente. A detecção de
carros da maquete e sua precisão ainda precisam ser testadas pelo usuário.
Registrar diferentes posições de carros, iluminação, sombras e tempo de resposta.

## API implementada

| Método | Caminho | Uso |
| --- | --- | --- |
| GET | /api/status | Imagem recente, FPS, estados, contadores e LED simulado |
| GET | /api/video | Fluxo MJPEG compartilhado |
| GET | /api/frame.jpg | Última imagem recente para selecionar regiões |
| PUT | /api/spots/{id}/roi | Salvar região e dimensões da câmera |
| POST | /api/reference | Capturar referência, com confirm_empty=true explícito |
| PUT | /api/detection | Pausar/iniciar análise e ajustar limiares permitidos |

## Referências

- [StreamingResponse no FastAPI](https://fastapi.tiangolo.com/advanced/custom-response/)
- [Ciclo de vida do aplicativo](https://fastapi.tiangolo.com/advanced/events/)
- [Limiarização no OpenCV](https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html)
- [Morfologia no OpenCV](https://docs.opencv.org/4.x/d9/d61/tutorial_py_morphological_ops.html)
- [Contornos com Canny](https://docs.opencv.org/4.x/da/d22/tutorial_py_canny.html)
