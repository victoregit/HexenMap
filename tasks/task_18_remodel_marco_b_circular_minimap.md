# Task Specification: Remodelagem do Genshin Gem Wish — Marco B: Minimapa Circular

## Contexto e Objetivo
Implementar o **Marco B** do roadmap de remodelagem estabelecido em `ANTIGRAVITY_REMODELAR_OVERLAY_GENSHIN.md` e `docs/REMODEL_ROADMAP.md`:
Projetar os mesmos marcadores de exploração ativos dentro do círculo do minimapa nativo do jogo, relativo à posição do jogador, aplicando máscara circular estrita (stencil) para garantir que nenhum pixel seja renderizado fora do contorno circular do minimapa.

A imagem real fornecida pelo usuário está em:
`/mnt/d/Projects/GenshinGemWish/data/reference/02_circular_minimap.png` (245x179 px).

---

## Workspace Root
Caminho absoluto: `/mnt/d/Projects/GenshinGemWish`

---

## Entregáveis Desta Execução

### 1. Módulo `MinimapProjector` (`src/map/minimap_projector.py`)
Criar `src/map/minimap_projector.py`:
- `MinimapCircle`: Dataclass contendo `center_x: float`, `center_y: float`, `radius: float`.
- `MinimapProjector`:
  - `detect_minimap_circle(image: np.ndarray) -> MinimapCircle`:
    Detecta o círculo do minimapa na imagem via `cv2.HoughCircles` com fallback calibrado (para `02_circular_minimap.png`: center=(141.5, 93.5), radius=82.0).
  - `project_markers(markers: List[Marker], player_pos: Tuple[float, float], player_heading: float = 0.0, minimap_rotation: bool = False, scale: float = 0.15) -> List[ProjectedMinimapMarker]`:
    - Calcula o deslocamento relativo: $\Delta \mathbf{x} = \mathbf{x}_{\text{marker}} - \mathbf{x}_{\text{player}}$.
    - Se `minimap_rotation` for True, aplica rotação pelo ângulo do jogador. Se False (minimapa fixo / padrão do Genshin), mantém orientação Norte.
    - Converte para coordenadas de pixel dentro do minimapa:
      $px = cx + \Delta x \cdot \text{scale}$
      $py = cy + \Delta y \cdot \text{scale}$
    - Filtra marcadores cuja distância ao centro exceda $R - r_{\text{marker}}$.
  - `render_minimap_overlay(base_image: np.ndarray, projected_markers: List[ProjectedMinimapMarker], circle: MinimapCircle) -> np.ndarray`:
    - Aplica máscara circular estrita (anti-aliased circular stencil mask).
    - Renderiza os pins dos baús com contorno nítido e halo de alto contraste.
    - Garante que nenhum pixel do overlay altere ou vaze para fora do círculo do minimapa.

### 2. Script de Validação Visual do Marco B (`scripts/verify_marco_b.py`)
Criar `scripts/verify_marco_b.py`:
- Carrega `data/reference/02_circular_minimap.png`.
- Detecta o círculo do minimapa.
- Utiliza a posição do jogador calibrada na Espinha do Dragão e projeta os baús mais próximos da região sobre o minimapa.
- Aplica máscara circular anti-aliasing.
- Gera e salva as imagens de evidência em:
  - `data/reference/marco_b_minimap_result.png`
  - `data/reference/marco_b_comparison.png` (lado a lado: original vs minimapa com marcadores sobrepostos)
- Verifica matematicamente que a contagem de pixels alterados fora do raio $R + 1$ é rigorosamente ZERO.
- Imprime e registra as métricas de alinhamento e precisão.

### 3. Testes Automatizados de Regressão e Validação (`tests/test_minimap_projection.py`)
Criar `tests/test_minimap_projection.py`:
- `test_circular_masking_strictly_bounds_markers`: Garante que nenhum marcador seja projetado além do raio do círculo.
- `test_relative_projection_translates_with_player`: Move a posição do jogador e verifica que a posição relativa dos marcadores na tela se desloca proporcionalmente.
- `test_rotation_invariance_and_angles`: Testa rotações a 0°, 90°, 180° e 270°.
- `test_zero_selected_returns_zero_rendered`: Garante que lista de marcadores vazia retorne 0 itens projetados.
- `test_circle_detection_on_reference_image`: Verifica a detecção automática do círculo em `02_circular_minimap.png`.
- Executar `pytest tests/` garantindo que todos os testes passem (86 anteriores + novos testes).

### 4. Atualização de Documentação e Recompilação do Executável
- Atualizar `docs/REMODEL_ROADMAP.md` marcando o Marco B como concluído com métricas medidas.
- Recompilar `GenshinOverlay.exe` usando o Python do Windows.

Ao finalizar, envie relatório detalhado com os caminhos absolutos dos arquivos, métricas de validação circular e evidências visuais geradas.
