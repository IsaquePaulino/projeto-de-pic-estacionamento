# Orientações para contribuições

## Escopo e sequência

- Escopo atual: vídeo contínuo e teste local de ocupação com OpenCV, autorizado pelo usuário após confirmar a câmera.
- Etapa 2 autorizada pelo usuário após confirmar a compilação da estrutura inicial.
- Arduino IDE é o fluxo principal de firmware, por escolha do usuário.
- Sketch principal: firmware/EstacionamentoCam/EstacionamentoCam.ino.
- Código C++ e configuração local ficam na mesma pasta do sketch.
- PlatformIO permanece apenas como compatibilidade; não usá-lo como fluxo padrão.
- O pedido autoriza a interface de teste, API local, seleção de ROIs, referência vazia e detecção tradicional necessários ao ensaio.
- Não expandir para controle físico de LEDs, publicação ou outras etapas sem solicitação.
- Atualizar README e docs/etapas.md quando uma etapa for efetivamente concluída.
- Distinguir planejamento, implementação, teste automatizado e teste físico.

## Arquitetura obrigatória

- ESP32-CAM: captura/transmissão e LEDs. Processamento de imagem no computador.
- Não usar IA, modelos treinados, serviços pagos ou nuvem para detecção.
- Usar OpenCV tradicional, FastAPI, HTML/CSS/JavaScript e HTTP na rede local.
- Manter coordenadas da câmera independentes das coordenadas visuais do mapa.
- Configurar vagas e associação de LEDs em arquivos, sem fixar 10 vagas no código.
- Estados canônicos: free, occupied, unknown. Estado inicial sempre unknown.
- Falhas de câmera, ausência de referência e regiões inválidas não significam livre.
- Manter LEDs em simulação como padrão. Não pressupor hardware conectado.

## Organização e qualidade

- Documentação e textos da interface em português; identificadores consistentes.
- Separar aquisição, detecção, estado, API, configuração e transporte de LEDs.
- Não instalar opencv-python e opencv-python-headless no mesmo ambiente.
- Não criar testes fictícios nem afirmar validação física sem evidência.
- Rodar verificações adequadas à alteração e registrar limitações observadas.
- Conferir docs/hardware.md antes de definir GPIO.
- Nunca versionar senhas, .env, config.local.h, capturas reais ou builds.
- Não publicar no GitHub, gravar firmware ou avançar etapas por conta própria.
