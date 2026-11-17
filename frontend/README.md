# Frontend

Interface de teste em HTML, CSS e JavaScript nativos, servida pelo FastAPI.
Exibe vídeo MJPEG, contadores, regiões coloridas sobre a imagem, seleção de quatro
pontos, captura da referência vazia e ajustes do detector.

As posições do futuro mapa continuam independentes das regiões da câmera.
Este painel usa as ROIs sobre o vídeo e uma lista de vagas; o desenho real da
maquete e a edição de suas posições visuais ainda não foram implementados.
`assets/` receberá posteriormente um desenho ou imagem local da maquete;
o campo `map.background_image` indicará seu caminho público.

O backend serve os arquivos e a interface consulta a API na mesma origem, sem CDN,
bibliotecas externas ou comunicação direta do navegador com a ESP32-CAM.
Não há alteração manual dos estados de ocupação. LEDs são simulados no computador.

Cores: verde para free, vermelho para occupied, amarelo/cinza para unknown.
Além das cores, a interface exibirá rótulos para distinguir os estados.
Executar iniciar-monitor.bat e abrir http://127.0.0.1:8000.
