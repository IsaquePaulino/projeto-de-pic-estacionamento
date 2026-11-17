# Configurações versionadas

- `system.json`: captura, cadência do vídeo e parâmetros do detector/LEDs simulados.
- `parking.json`: 10 vagas, geometria do mapa e associação dos LEDs.
- `../.env.example`: modelo para valores locais de rede e modo dos LEDs.
- `../firmware/EstacionamentoCam/config.example.h`: modelo de configuração do dispositivo.

O painel usa ESP32_BASE_URL de .env, camera/detection de system.json e as regiões
de parking.json. Referência e metadados ficam em data/reference/, ignorados pelo Git.
Os valores de detecção são iniciais e precisam de ensaios com a maquete.
LEDs físicos e a configuração de polling de uma interface futura são reservados;
o painel atual consulta o estado a cada 500 ms.
Leia `../docs/configuracao.md` para unidades, precedência e regras de validação.
