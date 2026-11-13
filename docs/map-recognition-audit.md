# Auditoria Técnica do Pipeline de Reconhecimento Visual e Multimapa — HexenMap

## 1. Visão Geral e Escopo da Investigação

Esta auditoria técnica documenta a investigação aprofundada, os diagnósticos quantitativos e a identificação de causa-raiz realizada sobre o subsistema de visão computacional, roteamento geográfico, projeção de coordenadas e gerenciamento de marcadores do **HexenMap**.

O objetivo primário foi determinar por que o sistema original operava adequadamente apenas em **Teyvat Surface**, falhando de forma generalizada na identificação automática e no rastreamento dos demais mapas e camadas subterrâneas do jogo (*Enkanomiya*, *The Chasm: Underground Mines*, *Sea of Bygone Eras*, *Ancient Sacred Mountain*, *Temple of Space*, *Frost Moon* e subcamadas subterrâneas).

---

## 2. Auditoria dos 12 Módulos do Pipeline Existente

A investigação percorreu o fluxo real de dados sem presunções nominais, mapeando cada componente e seu comportamento:

1. **Captura da Janela do Genshin Impact (`src/capture/win32_capture.py`, `src/live/graphics_capture.py`)**:
   - Captura via `PrintWindow` (GDI) ou Windows Graphics Capture (WGC DirectX), entregando frames BGR à fila `latest`.
   - Funcionamento íntegro e independente da região ou mapa exibido.

2. **Identificação da Interface do Mapa M e Minimapa (`src/live/vision.py`, `confirmed_circle`, `template_visible`)**:
   - Detecta o Mapa M pelo template do cabeçalho da UI (`map_ui` e `map_ui_roi: [0.85, 0.0, 0.15, 0.15]`) e o Minimapa pelo círculo com ponteiro ciano.
   - Funcionamento estável para ambos os modos.

3. **Reconhecimento da Imagem do Mapa (`src/live/budget_vision.py`, `BudgetRecognizer`)**:
   - Avalia a query SIFT contra rasters de referência usando votação coarse e correspondência detalhada RANSAC.
   - **Falha identificada**: Em mapas compactos, a subamostragem coarse destruía detalhes visuais; e blocos detalhados eram ignorados no Mapa M por falta de flag `map_compatible`.

4. **Seleção da Região ou Mapa Ativo (`src/live/automatic_maps.py`, `src/live/desktop.py`)**:
   - `AutomaticMapSearch` roda em thread de fundo sob perda de alinhamento; `DesktopApp.accept_discovered_map()` aplica o mapa descoberto.
   - **Falha identificada**: `MapRouter` sofria autocompetição entre subcamadas e inanição de descritores SIFT em mapas com múltiplos andares.

5. **Identificação de Superfície e Camadas (`src/live/budget_vision.py`, `src/live/session.py`)**:
   - **Falha identificada**: No jogo, abrir uma camada subterrânea no Mapa M renderiza o andar sobre a superfície esmaecida. Tanto a superfície quanto a subcamada geravam inliers válidos, acionando a rejeição `"Camada ambígua"` que descartava ambas. Além disso, `AutomaticMapSearch` não monitorava mudanças de camada enquanto a superfície permanecia válida.

6. **Carregamento de Imagens e Templates de Referência (`src/live/reference_store.py`, `ReferenceStore`)**:
   - Lê `manifest.json`, carrega imagens de terreno e mantém cache particionado LRU com limite de 256 MiB.
   - Funcionamento íntegro, porém dependente da integridade dos metadados dos manifestos.

7. **Correspondência de Características Visuais (`src/live/vision.py`, `TerrainMatcher.match`)**:
   - Correspondência SIFT com filtragem por razão de Lowe (0.68) e RANSAC com `estimateAffinePartial2D`.
   - **Falha identificada**: A validação de área de casco convexo exigia `area >= usable_area * 0.08` contra todo o viewport do Mapa M (~81.600 px² em 1080p). Camadas subterrâneas compactas (como cavernas de 248×246 px com área total de 61.000 px²) eram rejeitadas mesmo com 400+ inliers e 99% de confiança!

8. **Conversão de Coordenadas do Mapa para a Tela (`src/live/budget_vision.py`, `TerrainMatcher`)**:
   - Mapeia pixels da tela para coordenadas globais via matriz afim `world_to_screen = matrix @ world_to_image`.
   - Cada mapa possui origem e escala próprias; a geometria matemática é rigorosa quando o alinhamento é encontrado.

9. **Acompanhamento de Arrasto e Zoom (`src/live/motion.py`, `MotionRecognizer`, `src/live/display_motion.py`)**:
   - Fluxo óptico Lucas-Kanade com suavização temporal e ancoragem periódica em frames absolutos.
   - Funcionamento íntegro, preservado sem sobrecarga.

10. **Renderização dos Marcadores (`src/live/session.py`, `LiveSession.visible_markers`, `src/live/presentation.py`)**:
    - Filtra marcadores pelo `map_id` ativo e por `marker.layer_id in {None, active_layer_id}`.
    - Se o sistema permanecia preso em `surface`, os marcadores de cavernas (`as-layer-*`) eram 100% filtrados (`RENDER_FILTERED`).

11. **Reinicialização do Rastreamento após Troca de Mapa (`src/live/desktop.py`, `reload_reference`)**:
    - Ao confirmar troca de território, reseta `display_motion`, `motion`, esvazia marcadores visíveis e invalida sessão (`STALE_TRACKING_STATE` prevenido).

12. **Gerenciamento de Caches e Estados (`src/live/reference_store.py`, `FeatureCache`)**:
    - Armazena descritores e pontos SIFT pré-calculados em disco (`userData/cache/references`).
    - Desempenho alto em cache quente (< 15 ms por bloco).

---

## 3. Respostas Fundamentadas às 13 Perguntas da Auditoria

| # | Pergunta da Auditoria | Resposta Técnica Verificada |
|---|---|---|
| **1** | O reconhecimento está limitado explicitamente a `Teyvat Surface`? | **Não explicitamente no código, mas sim na prática por múltiplas falhas encadeadas.** `DesktopApp` iniciava em `as-map-2 / surface`, e problemas de roteamento, escala, filtros de área e concorrência de camadas impediam a troca e a permanência nos outros mapas. |
| **2** | Existem identificadores fixos para o mapa principal? | Sim: `as-map-2` com camada `surface` é o padrão inicial em [session.py](file:///d:/Projects/GenshinGemWish/src/live/session.py), [desktop.py](file:///d:/Projects/GenshinGemWish/src/live/desktop.py) e [prepare_separate_maps.py](file:///d:/Projects/GenshinGemWish/scripts/prepare_separate_maps.py). |
| **3** | O detector tenta reconhecer outros mapas? | Sim, em modo automático (`AutomaticMapSearch`) durante perda contínua de alinhamento ou seleção manual no seletor. Contudo, o roteador falhava em classificar o mapa correto em vários cenários. |
| **4** | Os arquivos de referência dos outros mapas existem? | **Sim para todos os 6 mapas independentes do Grupo B e suas 44 subcamadas** (51 escopos instalados em `userData/references/appsample`). **Não para as 317 camadas subterrâneas de Teyvat (`as-map-2`)**, que constam em `markers.json`, mas não possuem referências visuais instaladas (`REFERENCE_MISSING`). |
| **5** | Eles são carregados corretamente? | Parcialmente: manifestos eram lidos, mas blocos `minimap-*` dos mapas separados não tinham `map_compatible=True`, tornando-os invisíveis para o Mapa M em zoom detalhado. |
| **6** | As referências estão incluídas na versão distribuída? | Sim: `scripts/package_portable.py` inclui todos os pacotes presentes em `userData/references/appsample`. |
| **7** | O reconhecimento usa uma transformação exclusiva de Teyvat? | Não na álgebra afim, mas a subamostragem coarse reduzia o canvas inteiro de 4096×4096 para 1536×1536. Em mapas onde a terra ocupa < 10% do canvas (ex.: Sea of Bygone Eras), os detalhes eram quase completamente perdidos. |
| **8** | O sistema distingue mapa e camada? | Sim nos identificadores (`map_id` vs `layer_id`), mas no `MapRouter` original todas as camadas concorriam entre si, dividindo descritores e gerando empates espúrios. |
| **9** | Os IDs correspondem aos dados de marcadores? | Sim para os 7 `map_id` e todas as 44 subcamadas dos mapas independentes. Marcadores de superfície possuem `layer_id = None`, enquanto marcadores subterrâneos possuem `layer_id = 'as-layer-*'`. |
| **10** | O mapa é reconhecido, mas a renderização rejeita marcadores? | Sim: quando o modo automático fixava `layer_id = 'surface'`, marcadores de subcamadas eram filtrados por `visible_markers()` (`RENDER_FILTERED`). |
| **11** | Existe algum filtro que descarta mapas diferentes do principal? | Em `AutomaticMapSearch`, após localizar Teyvat no minimapa, a busca exigia abertura do Mapa M ou perda contínua >= 0,75 s para evitar consultas pesadas a cada oscilação rápida do minimapa. Além disso, enquanto `surface` estivesse válida, o sistema nunca sondava camadas subterrâneas. |
| **12** | Ao alternar entre mapas, o estado anterior é invalidado? | Sim, `DesktopApp.reload_reference()` reseta `motion`, `display_motion` e limpa o renderer. Porém, antes da confirmação, o rastreador continuava no mapa anterior (`STALE_TRACKING_STATE`). |
| **13** | Os mapas adicionais utilizam o mesmo espaço de coordenadas? | Todos utilizam grade afim centrada em `(0, 0)`, mas cada `(map_id, layer_id)` possui escala física e limites próprios (`bounds`), exigindo transformações independentes. |

---

## 4. Inventário Completo dos Mapas (Grupo A e Grupo B) — Reconciliado com `markers.json`

Contagem total do catálogo auditada: **88.957 marcadores** distribuídos em 7 mapas.

| Grupo | ID Real (`map_id`) | Nome do Território | Camadas no Catálogo (`markers.json`) | Pacotes Instalados (`userData/references/appsample`) | Marcadores no Catálogo (`88.957` total) | Diagnóstico da Auditoria |
|---|---|---|---|---|---|---|
| **A** | `as-map-2` | **Teyvat** | `surface` + **317** camadas `as-layer-*` | `1` (`surface` apenas; `0` camadas subterrâneas) | **`83.144`** (`72.507` surface + `10.637` em 317 subcamadas) | `surface`: 100% funcional. Subcamadas subterrâneas de Teyvat: **`REFERENCE_MISSING`** explícito (sem pacotes instalados). |
| **B.1** | `as-map-7` | **Enkanomiya** | `surface` (`0` subcamadas) | `1` (`surface`, z12 + 121 rasters z13) | **`1.373`** (`1.373` surface) | Mapa M visão geral: OK. Zoom detalhado falhava por ausência de `map_compatible=True`. |
| **B.2** | `as-map-9` | **The Chasm: Underground Mines** | `surface` (`0` subcamadas) | `1` (`surface`, z12 + 121 rasters z13) | **`1.146`** (`1.146` surface) | Mapa M visão geral: OK. Zoom detalhado falhava por falta de `map_compatible=True`. |
| **B.3** | `as-map-34` | **Sea of Bygone Eras** | `surface` + **8** camadas `as-layer-*` | `9` (`surface` + 8 subcamadas) | **`712`** (`520` surface [73,0%] + `192` em 8 subcamadas [27,0%]) | Falhava no roteador (`ambiguous`) por autocompetição entre superfície e camadas; conteúdo ocupa apenas 5,4% do canvas. |
| **B.4** | `as-map-36` | **Ancient Sacred Mountain** | `surface` + **3** camadas `as-layer-*` | `4` (`surface` + 3 subcamadas) | **`808`** (`481` surface [59,5%] + `327` em 3 subcamadas [40,5%]) | Roteador acertava Mapa M overview, mas zoom detalhado falhava sem `map_compatible`. |
| **B.5** | `as-map-37` | **Temple of Space** | `surface` + **16** camadas `as-layer-*` | `17` (`surface` + 16 subcamadas) | **`755`** (`603` surface [79,9%] + `152` em 16 subcamadas [20,1%]) | Roteador falhava (`ambiguous`) por divisão de 1200 descritores entre 17 escopos (inanição: ~70 descritores). |
| **B.6** | `as-map-40` | **Frost Moon** | `surface` + **17** camadas `as-layer-*` | `18` (`surface` + 17 subcamadas) | **`1.019`** (`670` surface [65,8%] + `349` em 17 subcamadas [34,2%]) | Superfície recebia apenas 66 descritores (inanição); causava falso positivo em `as-map-9`. |

---

## 5. Taxonomia e Classificação Padronizada de Falhas

Foram implementados no módulo `src/live/tracking_diagnostics.py` os 10 códigos padronizados de diagnóstico exigidos pela especificação:

1. **`REFERENCE_MISSING`**: O mapa ou camada solicitada não possui arquivos de referência no diretório de instalação (ex.: 317 camadas subterrâneas de Teyvat `as-map-2`).
2. **`REFERENCE_LOAD_FAILED`**: Os arquivos de referência existem no disco, mas falharam na decodificação de imagem ou integridade de hash.
3. **`MAP_CLASSIFICATION_FAILED`**: O classificador coarse (`MapRouter`) não conseguiu atingir o limiar de votos ou empatou entre dois mapas diferentes.
4. **`LAYER_CLASSIFICATION_FAILED`**: O mapa geográfico foi identificado com certeza, mas ocorreu ambiguidade não resolvida entre dois andares subterrâneos diferentes.
5. **`LOW_MATCH_CONFIDENCE`**: Descritores visuais ou pares KNN foram insuficientes (< 12 inliers ou razão RANSAC < 0.65).
6. **`TRANSFORM_FAILED`**: O alinhamento geométrico afim parcial falhou numericamente ou calculou escala física inválida (< 0.03 ou > 20.0).
7. **`COORDINATE_SPACE_MISMATCH`**: A projeção das coordenadas na tela caiu fora dos limites geográficos válidos do território.
8. **`MARKER_DATA_MISSING`**: O território foi reconhecido, mas não há marcadores para os filtros ativos no catálogo local.
9. **`RENDER_FILTERED`**: Marcadores existem no mapa, mas foram descartados por pertencerem a camadas inativas ou estarem fora da viewport.
10. **`STALE_TRACKING_STATE`**: O rastreamento de um mapa anterior continuava retendo predições antigas sem validação do novo território.

---

## 6. Diagnóstico Técnico Detalhado das 4 Causas-Raiz

### Causa-Raiz 1 — `MapRouter`: Inanição de Descritores e Autocompetição Intra-Mapa
- **Localização**: `src/live/automatic_maps.py`, linhas 47–64 e 90–99.
- **Mecanismo da Falha**:
  1. A divisão ingênua `budget = max(1, 1200 // counts[scope[0]])` truncava a superfície de `as-map-40` para 66 descritores e `as-map-37` para 70 descritores, enquanto mapas sem subcamadas (`as-map-7`, `as-map-9`) retinham 600 descritores.
  2. O teste de ambiguidade comparava o 1º e 2º colocados nos votos gerais. Quando `('as-map-34', 'surface')` e `('as-map-34', 'as-layer-145')` empatavam, o roteador declarava `ambiguous = True`, abortando a troca de mapa mesmo sabendo que ambos pertenciam ao mesmo mapa!
  3. No teste de Lowe KNN, a busca pelo concorrente `other` ignorava descritores de ruído com distâncias euclidianas altas (> 210), permitindo que vetores aleatórios de mapas distintos gerassem votos espúrios.

### Causa-Raiz 2 — `TerrainMatcher.match`: Rejeição RANSAC de Camadas Compactas por Limiar de Área
- **Localização**: `src/live/vision.py`, linha 122.
- **Mecanismo da Falha**:
  - `usable_area` calculava a área do viewport da tela do Mapa M (~1.020.000 px²). O filtro `if area < usable_area * 0.08: return None` exigia pelo menos 81.650 px² de casco convexo dos pontos inliers.
  - Como subcamadas subterrâneas (como `as-layer-125-157`) têm dimensão nativa de apenas 248×246 px (área máxima de 61.008 px²), mesmo que 100% dos seus pixels tivessem correspondência perfeita (405 inliers, 99,3% de confiança), a área máxima possível era de ~33.900 px², sendo **sumariamente rejeitada** em 100% dos quadros!

### Causa-Raiz 3 — `BudgetRecognizer`: Rejeição por `"Camada ambígua"` e Falta de Suporte a Detalhe no Mapa M
- **Localização**: `src/live/budget_vision.py`, linhas 101–105 e 158–162.
- **Mecanismo da Falha**:
  - No jogo, ao visualizar um andar subterrâneo no Mapa M, o jogo renderiza a caverna sobreposta ao mapa de superfície esmaecido.
  - Ao avaliar simultaneamente `surface` e `as-layer-*`, ambos produziam correspondências válidas. A linha `if len({tile.raster.pack_index for tile, fit in fits}) > 1: return Observation('hidden', stamp, reason=_tr('Camada ambígua'))` descartava ambos e ocultava os marcadores!
  - Além disso, `candidates('map')` consultava apenas rasters com `surface == 'map'`, ignorando os blocos detalhados `minimap-*` dos mapas separados por não possuírem `map_compatible=True`.

### Causa-Raiz 4 — `AutomaticMapSearch`: Cegueira de Camadas Subterrâneas sob Superfície Válida
- **Localização**: `src/live/automatic_maps.py`, linha 140.
- **Mecanismo da Falha**:
  - Em modo automático, `AutomaticMapSearch.tick()` executava `if observation.fresh(stamp): return None`.
  - Quando o usuário abria uma camada subterrânea no Mapa M, a borda esmaecida da superfície continuava casando com `confidence=0.99`. Com `observation.fresh` verdadeiro, `tick()` retornava imediatamente sem verificar se uma subcamada havia sido aberta.
  - Como consequência, o sistema nunca migrava para o andar subterrâneo, e todos os marcadores da caverna permaneciam ocultos por `visible_markers()`.

---

## 7. Conclusão da Auditoria

A limitação multimapa decorria de filtros geométricos desproporcionais para camadas compactas, alocação enviesada de descritores no roteador, ausência de desambiguação geométrica entre superfícies esmaecidas e sobreposições de cavernas, e falta de sondagem de subcamadas em segundo plano. As correções arquiteturais implementadas atacaram a causa-raiz sem reconstruir o pipeline e sem adicionar dependências externas pesadas.
