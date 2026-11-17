# Configuração local

Arquivos JSON são legíveis e suportados pela biblioteca padrão do Python.
schema_version permite reconhecer alterações de formato. O backend valida câmera,
endereço, vagas, detector e cores dos LEDs simulados antes de iniciar.

## Separação dos valores

| Local | Conteúdo |
| --- | --- |
| config/system.json | Intervalos, limiares, cores e caminhos do protocolo |
| config/parking.json | Vagas, regiões da câmera, posições do mapa e LEDs |
| .env na raiz | Endereço do dispositivo, host/porta da API, modo de LED e logs |
| firmware/EstacionamentoCam/config.local.h | Wi-Fi e parâmetros locais do dispositivo |

Caminhos de arquivos serão relativos à raiz do repositório, independentemente do
diretório de execução. Caminhos HTTP começam em /. O carregador da Etapa 2 aceita
variáveis do processo com precedência sobre .env para ESP32_BASE_URL.
Os outros campos de .env ainda não são consumidos. O painel mantém os LEDs em
simulação no computador. Não duplicar credenciais nos arquivos JSON.

ESP32_BASE_URL é obrigatório: informar somente a origem, como
http://192.168.1.50 ou http://192.168.1.50:8080, sem /capture, usuário/senha,
query ou fragmento. A seção camera é lida de config/system.json com
schema_version=1. O carregador encontra a raiz pela localização do pacote em
modo editável, sem depender do diretório de execução. Instalação em wheel isolado
sem os arquivos externos de configuração ainda não é suportada.

## Aquisição — parâmetros ativos

| Chave em camera | Valor inicial | Uso na Etapa 2 |
| --- | --- | --- |
| capture_path | /capture | Caminho solicitado ao dispositivo |
| request_timeout_seconds | 2 | Timeout por operação de rede |
| poll_interval_seconds | 0.5 | Pausa entre capturas do comando --count |
| preview_interval_seconds | 0.1 | Pausa entre aquisições do painel |
| max_frame_bytes | 2000000 | Limite do corpo, mesmo sem Content-Length |
| stale_after_seconds | 5 | Imagem vencida invalida os estados |

Intervalos devem ser finitos e positivos. O caminho não pode apontar para outro
host. max_frame_bytes deve ser positivo. O firmware mantém /capture fixo;
se mudar esse caminho no JSON, também será preciso alterar a rota do firmware.
Isso não afeta o cadastro ou as coordenadas das vagas.

## Vagas e coordenadas

Cada item de spots contém:

- id: identificador estável e único, inicialmente V01 a V10.
- label: nome apresentado ao usuário.
- camera_roi: null enquanto não calibrada; depois, lista de pelo menos três
  pontos [x, y] de um polígono convexo, sem repetir o primeiro no fim (máximo 12).
- map_rect: retângulo do mapa com x, y, width, height e rotation_degrees.
- initial_state: unknown; o estado atual será mantido pelo backend.
- led_index: índice do WS2812B na cadeia, começando em zero.

Os pontos da ROI usam coordenadas normalizadas em [0, 1], com origem no canto
superior esquerdo da imagem exibida, x para a direita e y para baixo. Exemplo
somente de formato, sem representar uma vaga real:

```json
{"camera_roi": [[0.10, 0.15], [0.20, 0.15], [0.20, 0.40], [0.10, 0.40]]}
```

camera_image.width e height registram a resolução da calibração. Inicialmente
são null e calibrated é false. O painel permite calibrar só algumas vagas;
as demais continuam desconhecidas. Uma imagem de outra resolução impede a
análise. Salvar a primeira ROI na resolução nova limpa as outras regiões antigas.

O mapa usa um sistema virtual de 1000 por 600 unidades. A UI poderá representá-lo
com SVG viewBox e redimensionar sem alterar coordenadas. map_rect.x/y indicam
o canto superior esquerdo; rotação ocorre em torno do centro do retângulo.
As 10 posições são provisórias em duas fileiras, sem afirmar correspondência
com a maquete.

map.background_image começa null. Depois poderá apontar para um recurso local
servido a partir de frontend/assets/. Ajustar o mapa não deve alterar a ROI
da câmera, e mover a câmera não deve mover vagas na UI.

Para adicionar vagas, acrescentar itens com IDs e índices únicos, sem alterar
o código do backend. No dispositivo, configurar LED_COUNT para cobrir o maior
índice mais um e conferir alimentação/quantidade física.

## Parâmetros iniciais do detector

| Chave em detection | Valor | Uso |
| --- | --- | --- |
| enabled | false | Iniciar somente após calibração e referência |
| reference_image | data/reference/empty.jpg | Arquivo local ainda inexistente |
| gaussian_blur_kernel | 5 | Lado ímpar e positivo do filtro gaussiano |
| pixel_difference_threshold | 25 | Diferença em intensidade de 8 bits, 0 a 255 |
| free_max_changed_ratio | 0.08 | Até 8% alterados: candidato livre |
| occupied_min_changed_ratio | 0.18 | A partir de 18%: candidato ocupado |
| confirmation_frames | 4 | Análises válidas consecutivas para confirmar |
| max_global_changed_ratio | 0.65 | Acima disso, rejeitar quadro por mudança global |
| max_illumination_shift | 45 | Limite da compensação de luminosidade |
| chromatic_difference_threshold | 12 | Diferença mínima de cromaticidade |
| min_color_changed_ratio | 0.06 | Evidência de cor para ocupação |
| min_new_edge_ratio | 0.012 | Evidência alternativa de novos contornos |
| max_camera_shift_pixels | 3 | Limite do deslocamento global estimado |
| analysis_interval_seconds | 0.3 | Intervalo mínimo entre análises |

A fração é calculada dentro da máscara da ROI após os filtros. A checagem
global usa o quadro inteiro e não determina sozinha ocupação. Os valores são
hipóteses iniciais, sem ensaio; precisam de ajuste com imagens reais, sombras e
diferentes posições de carros. Estão implementadas compensação de iluminação,
morfologia e evidência de cor ou novos contornos para confirmar ocupação.
O algoritmo mede ocupação por diferença, sem reconhecer semanticamente carros.

## Temporização e validação

Intervalos e prazos em JSON são segundos. LED_COMMAND_TIMEOUT_MS no firmware é
milissegundos: 5000 ms equivale aos 5 s em system.json. O heartbeat proposto é 2 s.
LED_BRIGHTNESS usa escala 0 a 255; cores RGB são nominais. A contagem de capturas
não promete tempo de resposta: aquisição e processamento introduzem atraso.

O carregador verifica IDs e índices únicos, índices não negativos,
estados válidos, dimensões positivas quando calibradas, polígonos convexos não
degenerados dentro de [0, 1], retângulos dentro do mapa, cores inteiras de 0 a 255,
intervalos positivos e free_max_changed_ratio menor que occupied_min_changed_ratio.
O painel salva alterações de forma atômica. A referência exige calibração,
endereço e hash do JPEG compatíveis. Alterar regiões pausa a análise e invalida
a referência. Mover a câmera exige nova calibração e referência. Erros não devem
produzir estado livre. Heartbeat e transporte físico de LEDs seguem planejados.

Veja [teste-ocupacao.md](teste-ocupacao.md) para calibrar e executar o ensaio.
