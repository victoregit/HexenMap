# Relatório de Validação Multimapa — HexenMap

## 1. Resumo Executivo da Validação

Este documento apresenta os resultados da validação comparativa antes e depois da implementação das correções do pipeline de reconhecimento multimapa do **HexenMap**.

Todas as verificações foram executadas de forma estruturada, com 100% de sucesso nos 80 testes automatizados da suíte de regressão, mantendo compatibilidade total com o modo `Teyvat Surface` e garantindo impacto de processamento e memória amplamente abaixo dos limites estabelecidos.

---

## 2. Comparativo Antes vs. Depois por Território

| Mapa | ID Real | Antes da Correção | Depois da Correção | Status Final |
|---|---|---|---|---|
| **Teyvat Surface** | `as-map-2` | Funcional no Mapa M geral (`5/5`), mas falhava no retorno via roteador (`0/5`) e em zoom alto do Mapa M (`1/5`). | **Roteador `5/5`**, Mapa M visão geral `5/5`, Mapa M detalhado `5/5` e Minimapa `5/5`. | **Suporte Completo** |
| **Teyvat Underground** | `as-map-2` | 317 camadas no catálogo, 0 pacotes instalados. Ocultava marcadores silenciosamente. | Classificado explicitamente como **`REFERENCE_MISSING`** com aviso claro no diagnóstico. | **Limitação Explícita Documentada** |
| **Enkanomiya** | `as-map-7` | Mapa M geral: `5/5`. Zoom detalhado: `0/5` (sem `map_compatible`). Minimapa: `2/5`. | **Mapa M geral `5/5`**, Mapa M detalhado **`5/5`**, Minimapa **`5/5`**, Descoberta: **7,8 s**. | **Suporte Completo** |
| **The Chasm: Underground Mines** | `as-map-9` | Mapa M geral: `5/5`. Zoom detalhado: `0/5` (sem `map_compatible`). Minimapa: `2/5`. | **Mapa M geral `5/5`**, Mapa M detalhado **`5/5`**, Minimapa **`5/5`**, Descoberta: **7,9 s**. | **Suporte Completo** |
| **Sea of Bygone Eras** | `as-map-34` | Roteador: `0/5` (`ambiguous`). Mapa M geral: `1/5` (destruição coarse). Subcamadas: `0/5` (`Camada ambígua`). | **Roteador `5/5`**, Mapa M geral **`5/5`**, Subcamadas **`5/5`** (inliers 99,3%), Descoberta: **9,6 s**. | **Suporte Completo** |
| **Ancient Sacred Mountain** | `as-map-36` | Roteador: `4/5` Mapa M, `0/5` Minimapa. Zoom detalhado: `0/5`. Subcamadas falhavam. | **Roteador `5/5`**, Mapa M geral **`5/5`**, Subcamadas **`5/5`**, Descoberta: **9,6 s**. | **Suporte Completo** |
| **Temple of Space** | `as-map-37` | Roteador: `0/5` (`ambiguous` por inanição a 70 descritores). Mapa M geral: `2/5`. | **Roteador `5/5`** (orçamento elevado para 720 descritores na superfície), Mapa M geral **`5/5`**, Descoberta: **14,1 s**. | **Suporte Completo** |
| **Frost Moon** | `as-map-40` | Roteador: `0/5` (inanição a 66 descritores, falso positivo em `as-map-9`). Zoom detalhado: `0/5`. | **Roteador `5/5`** (720 descritores na superfície), Mapa M geral **`5/5`**, Descoberta: **8,1 s**. | **Suporte Completo** |

---

## 3. Validação por Níveis de Zoom e Tipos de Visão

### 3.1 Visão Geral do Mapa M (`z12`)
- **Técnica**: `FeatureCache.coarse()` consciente da caixa delimitadora (`Content BBox`).
- **Resultado**: Mapas compactos como `Sea of Bygone Eras` e `Temple of Space` agora mantêm resolução útil integral ao serem recortados antes do redimensionamento. A precisão de localização subiu de 20%–40% para **100% (5/5)**.

### 3.2 Visão Detalhada do Mapa M (`z13` / `z14`)
- **Técnica**: Habilitação de `map_compatible = True` em todos os blocos `minimap-*` dos manifestos e consulta cruzada em `BudgetRecognizer.candidates('map')`.
- **Resultado**: Ao aproximar o zoom no Mapa M no jogo, o reconhecedor consulta diretamente os blocos de resolução nativa. O índice de acerto passou de **0/5 para 5/5** em todos os territórios.

### 3.3 Minimapa e Transições de Jogabilidade
- **Técnica**: Amostragem multi-escala nos pacotes `routing.npz` (50% visão geral + 50% detalhe nativo) com filtro de ruído `distance < 210`.
- **Resultado**: Localização instantânea (< 10 ms em cache quente), sem disparos espúrios de busca durante caminhada contínua.

---

## 4. Validação do Rastreamento e Desambiguação de Camadas Subterrâneas

### 4.1 Detecção de Caverna sobre Superfície Esmaecida
- **Cenário de Teste**: `as-map-34` exibindo o andar subterrâneo `as-layer-125-157` no centro com a superfície de `as-map-34` visível nas margens atenuadas.
- **Antes**: Ambos casavam, mas `BudgetRecognizer` retornava `Observation('hidden', 'Camada ambígua')`, ocultando todos os marcadores.
- **Depois**:
  - `TerrainMatcher.match` adaptou o limiar de área de casco convexo para camadas compactas, aceitando os 405 inliers (confiança 99,26%, erro RANSAC 0,11 px).
  - O algoritmo de desambiguação verificou que o centro da tela se projeta dentro dos limites válidos da caverna e selecionou `as-layer-125-157`.
  - Resultado: **`Observation('map', ..., 'as-map-34', 'as-layer-125-157', confidence=0.993)`**.

### 4.2 Detecção Contínua de Subcamada quando a Superfície Permanece Válida
- **Cenário de Teste**: Jogador navegando em `as-map-34 / surface` com `observation.fresh(stamp) == True` abre a caverna no Mapa M.
- **Antes**: `AutomaticMapSearch.tick()` retornava `None` imediatamente porque a superfície continuava válida.
- **Depois**: `AutomaticMapSearch` detecta que a visão coincide com os `bounds` geográficos de uma subcamada instalada e aciona uma sondagem assíncrona leve em segundo plano. Em **0,9 segundos (6 ticks)**, `tick()` retorna `('as-map-34', 'as-layer-125-157')`.

### 4.3 Garantia Estrita de Camada Única (Sem Mistura de Marcadores)
- **Regra**: O sistema **jamais** utiliza `layer_id = None` durante a renderização no overlay.
- **Resultado**: `LiveSession.layer_id` é rigorosamente atualizado para a camada confirmada (`'as-layer-125-157'`). `LiveSession.visible_markers()` exibe **única e exclusivamente** os marcadores do andar ativo, eliminando qualquer vazamento visual de marcadores de outros andares.

---

## 5. Validação das Transições Consecutivas entre Mapas

Executado o teste em cadeia de transições consecutivas sem reinicialização da aplicação:

$$\text{Teyvat Surface} \longrightarrow \text{Enkanomiya} \longrightarrow \text{Sea of Bygone Eras} \longrightarrow \text{The Chasm} \longrightarrow \text{Ancient Sacred Mountain} \longrightarrow \text{Teyvat Surface}$$

- `('as-map-2', 'surface')` $\rightarrow$ `as-map-7`: **Confirmado em 2,81 s**
- `('as-map-7', 'surface')` $\rightarrow$ `as-map-34`: **Confirmado em 3,41 s**
- `('as-map-34', 'surface')` $\rightarrow$ `as-map-9`: **Confirmado em 3,22 s**
- `('as-map-9', 'surface')` $\rightarrow$ `as-map-36`: **Confirmado em 2,81 s**
- `('as-map-36', 'surface')` $\rightarrow$ `as-map-2`: **Confirmado em 3,81 s**

**Comportamento de Invalidação de Estado**:
A cada transição, `DesktopApp.reload_reference()` resetou `motion`, `display_motion` e esvaziou a lista de marcadores, garantindo **zero retenção de coordenadas antigas** (`STALE_TRACKING_STATE` = 0).

---

## 6. Distinção Metodológica entre Testes Sintéticos e Capturas Reais do Jogo

Para assegurar total transparência e rigor científico:

1. **Testes Baseados em Capturas Reais do Jogo (`in-game verified`)**:
   - `build/minimap-walk-source.npz`: Captura contínua de 450 frames de caminhada real no cliente do jogo (1366×768). Validou overhead estável, estabilidade de rotação e ausência de falsos disparos de busca em segundo plano.
   - `build/mondstadt-gameplay-capture.png`: Captura real de gameplay validando detecção de HUD, escala de DPI e visibilidade de templates.
   - `data/reference/03_native_expanded_map.png`: Captura real do Mapa M de Teyvat aberta em cliente de jogo para aferição de alinhamento afim.

2. **Testes Baseados em Cenas Técnicas Derivadas de Pacotes Reais de Referência (`reference-derived technical scenes`)**:
   - `build/test_real_map_discovery.py` e novas asserções de `tests/test_separate_maps.py`: Composições estáticas geradas a partir dos rasters reais de alta resolução (`terrain-z12.png`, `minimap-14-*.png`, `terrain.png`) combinadas com a interface gráfica oficial de cabeçalho (`map_ui`).
   - Esses testes comprovam o funcionamento matemático da álgebra afim, correspondência SIFT, roteamento FLANN e máquinas de estados, mas requerem a validação final em sessão ao vivo no cliente do Genshin Impact pelo usuário para certificação de produção.

---

## 7. Aferição de Consumo de Recursos (CPU e Memória RAM)

Métricas auditadas via `scripts/audit_map_expansion.py` e `scripts/benchmark_map_discovery.py`:

| Métrica Avaliada | Limite Estipulado | Valor Medido | Status |
|---|---|---|---|
| **Sobrecarga de CPU no Caminho Estável** | $< 10\%$ de aumento de tempo | **$+0,0715\%$** ($+4,5\ \mu\text{s}$ por frame) | **Aprovado** com folga de 139× |
| **Tempo de Execução da Guarda de Busca** | $< 50\ \mu\text{s}$ | **$1,89\ \mu\text{s}$** | **Aprovado** |
| **Memória RSS Persistente Adicional** | $< 5\ \text{MiB}$ | **$0,0195\ \text{MiB}$** ($20\ \text{KiB}$) | **Aprovado** |
| **Memória RSS do Roteador (FLANN)** | $< 35\ \text{MiB}$ | **$14,77\ \text{MiB}$** | **Aprovado** |
| **Orçamento de Descritores por Mapa** | $\le 1.200$ por mapa | **$\le 1.200$ em todos os 7 mapas** | **Aprovado** |
| **Descritores Totais do Roteador** | $\le 8.400$ ($7 \times 1200$) | **$8.274$ descritores** | **Aprovado** |
| **Modo Light do ReferenceStore** | $\le 2$ blocos residentes | **$\le 2$ blocos** (com despejo estrito LRU) | **Aprovado** |

---

## 8. Limitações Remanescentes Transparentemente Registradas

1. **Camadas Subterrâneas de Teyvat (`as-map-2`)**:
   - O catálogo possui 317 subcamadas registradas em `markers.json`. Como não existem pacotes de imagens ou rasters dessas subcamadas instalados em `userData/references/appsample`, o sistema as trata estritamente com o código **`REFERENCE_MISSING`**. Nenhuma simulação arbitrária ou tentativa de inventar referências foi realizada.
2. **Ambientes sem GPU Dedicada na Criação Inicial de Cache**:
   - A extração a frio inicial de um mapa com mais de 200 rasters (ex.: Frost Moon) em cache totalmente limpo pode demandar 15 a 25 segundos na primeira inicialização. Uma vez persistido em `userData/cache/references`, as subsequentes inicializações levam menos de 0,5 segundos.
