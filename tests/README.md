# Plano de testes

Existem testes automatizados de aquisição, configuração e teste de ocupação:

- test_camera.py: JPEG válido, pixels/dimensões, timeout, recuperação, HTTP de erro,
  redirecionamento, resposta inválida, tamanho excedente e fechamento do stream.
- test_capture.py: ambiente/.env, configurações inválidas e comando de gravação.
- test_camera_http.py: transferência real em loopback e corpo HTTP incompleto.
- test_detection.py: referência, confirmações, ruído, sombras, luz, cor, movimento
  de câmera, imagens inválidas, calibração e limiares.
- test_monitor.py: persistência, metadados, estados, simulação, vencimento e MJPEG.
- test_app.py: fluxo de calibração/referência/análise e erros da API.

Executar da raiz, com o pacote e o extra dev instalados:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Esses testes geram imagens sintéticas em memória e arquivos somente nas pastas
temporárias do pytest. Não consultam ESP32-CAM real nem gravam na placa.

O ensaio de navegador é separado:

```powershell
.\.venv\Scripts\python.exe -m pip install -e "./backend[dev,ui]"
.\.venv\Scripts\python.exe tests/ui_smoke.py
```

Usa Chrome instalado, fonte sintética e configuração temporária. Verifica vídeo,
calibração, referência, estados, reconexão e layout desktop/mobile. Capturas de
QA ficam em data/qa/, ignoradas pelo Git. Não exige placa ou credenciais reais.

Cobertura física a acrescentar:

- Variação real de carros, ângulos, iluminação, sombras e reflexos.
- Precisão por vaga e tempo de resposta, com resultados esperados anotados.
- Efeito da luz de LEDs físicos sobre a imagem, quando forem conectados.

fixtures/ receberá apenas imagens sintéticas ou autorizadas para versionamento.
Capturas reais e referências locais deverão ficar em data/, ignorado pelo Git.
Os testes do detector precisarão de resultados esperados definidos antes de medir
precisão. Registrar ensaios físicos com data, montagem e condições.
