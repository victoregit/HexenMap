# Task Specification: Remodelagem do Genshin Gem Wish para Overlay Georreferenciado — Marco A

## Contexto e Objetivo
O usuário forneceu duas diretrizes essenciais:
- `ANTIGRAVITY_REMODELAR_OVERLAY_GENSHIN.md`
- `GenshinGemWish_AUDITORIA_E_REMODELACAO.md`

### Correção Crítica da Visão do Produto
O aplicativo **NÃO DEVE** desenhar um segundo mapa independente com fundo próprio ou grade artificial.
O objetivo é desenhar marcadores como **uma camada externa transparente e alinhada com precisão cirúrgica sobre as duas interfaces do próprio Genshin Impact**:
1. **Minimapa Circular da Jogabilidade**: marcadores projetados e recortados dentro do círculo nativo da tela do jogo.
2. **Mapa Expandido Nativo (tecla M do jogo)**: os mesmos marcadores sobrepostos exatamente nos pontos corretos do terreno no mapa original do jogo, acompanhando pan e zoom nativos do Genshin.

As três capturas de referência fornecidas pelo usuário foram localizadas e copiadas para:
- `data/reference/01_interactive_map_chests.png` (Mapa interativo de referência com baús na região da Espinha do Dragão / Dragonspine)
- `data/reference/02_circular_minimap.png` (Minimapa circular in-game da jogabilidade na Espinha do Dragão)
- `data/reference/03_native_expanded_map.png` (Mapa expandido nativo in-game tecla M na Espinha do Dragão)

---

## Workspace Root
Caminho absoluto: `/mnt/d/Projects/GenshinGemWish`

---

## Entregáveis Desta Execução

### 1. Documentação Técnica Obrigatória
Criar em `docs/`:
- `/mnt/d/Projects/GenshinGemWish/docs/CURRENT_GAP_ANALYSIS.md`:
  - Diagnóstico detalhado do código atual vs a visão remodelada.
  - Links exatos para arquivos e funções (`src/app.py::redraw_map`, `_update_gui_layout_for_mode`, `get_filtered_markers`, `src/map/map_renderer.py`, `src/capture/`, `src/tracking/`).
  - Lista franca do que funciona, o que era fictício/simulado e os bloqueios técnicos reais.
- `/mnt/d/Projects/GenshinGemWish/docs/GAME_MAP_REGISTRATION.md`:
  - Pipeline matemático e de visão computacional de registro:
    * Espaço de coordenadas canônicas de Teyvat $\leftrightarrow$ Espaço de pixels do mapa nativo da tela.
    * Resolução de transformação afim / similaridade ($x_{screen} = s \cdot R \cdot x_{world} + t$).
    * Detecção dos estados da UI (`GAMEPLAY_MINIMAP`, `NATIVE_MAP_OPEN`, `MENU_OR_LOADING`, `NO_GAME`).
    * Critérios de rejeição por baixa confiança (se alinhamento não for confiável, não desenhar marcadores em locais falsos).
- `/mnt/d/Projects/GenshinGemWish/docs/REMODEL_ROADMAP.md`:
  - Marcos formais A, B, C e D com critérios de aceite objetivos e métricas de erro em pixels.

### 2. Correções no Núcleo de Domínio
- Em `src/app.py` e `src/markers/models.py`:
  - Corrigir a lógica de filtro de categorias: **se nenhuma categoria for selecionada (`selected_categories == set()`), o resultado deve ser rigorosamente ZERO marcadores**, e NUNCA exibir todos.
  - Garantir que `active_marker_ids` seja a fonte única da verdade para qualquer superfície de renderização.

### 3. Implementação do Marco A: Prova de Conceito no Mapa Expandido
Criar módulos em `src/map/`:
- `src/map/registration.py`:
  - Classe `MapRegistration`:
    - Estima e armazena matriz de transformação afim / similaridade com pontos de controle de referência.
    - Método `register_from_control_points(src_pts, dst_pts) -> TransformResult`.
    - Método `compute_reprojection_error(src_pts, dst_pts) -> float`.
- `src/map/expanded_projector.py`:
  - Classe `ExpandedMapProjector`:
    - Projeta coordenadas mundiais de marcadores para coordenadas de pixel $(px, py)$ da tela sobre o mapa expandido nativo.
    - Suporta pan e zoom do mapa original.
    - Aplica frustum culling nos limites da viewport do jogo.
- Script de Validação Visual do Marco A:
  - `scripts/verify_marco_a.py`:
    - Carrega `data/reference/03_native_expanded_map.png` (1359x729).
    - Extrai marcos geográficos da Espinha do Dragão visíveis tanto em `01_interactive_map_chests.png` quanto em `03_native_expanded_map.png` (ex.: Teleport Waypoint do Acampamento de Albedo, Teleport da Estrada da Neve, Teleport do Palácio Antigo).
    - Calibra a projeção matemática de registro e projeta os baús calibrados sobre `03_native_expanded_map.png`.
    - Salva a imagem resultante em `data/reference/marco_a_overlay_result.png` e uma comparação lado a lado em `data/reference/marco_a_comparison.png`.
    - Imprime e registra o erro médio e p95 de alinhamento em pixels.

### 4. Testes Automatizados de Regressão e Validação
Criar:
- `tests/test_expanded_map_projection.py`:
  - Teste `test_zero_selected_categories_returns_zero_markers`: confirma que nenhuma categoria selecionada retorna 0 itens.
  - Teste `test_registration_control_points`: confirma precisão da matriz de calibração afim (erro médio $< 2.0$ pixels).
  - Teste `test_projection_pan_and_zoom`: confirma que translação e escala no mapa expandido deslocam os marcadores de forma coerente.
  - Teste `test_rejection_on_invalid_registration`: confirma que baixa confiança não projeta marcadores falsos.
- Executar `pytest tests/` garantindo que todos os testes passem (81+ testes).

### 5. Recompilar Executável e Atualizar Documentação
- Executar `scripts/build_exe.py` com o Python do Windows para atualizar `GenshinOverlay.exe`.
- Atualizar `README.md`.

Ao concluir, envie um relatório detalhado com os caminhos absolutos dos arquivos criados, medição de erro do Marco A em pixels e evidências das imagens geradas.
