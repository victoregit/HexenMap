# Task Specification: Remodelagem do Genshin Gem Wish — Marco C: Integração Windows Live e Superfícies Transparentes

## Contexto e Objetivo
Implementar o **Marco C** do roadmap de remodelagem estabelecido em `ANTIGRAVITY_REMODELAR_OVERLAY_GENSHIN.md` e `docs/REMODEL_ROADMAP.md`:
Unir os projetores ópticos dos Marcos A e B em uma arquitetura de sobreposição transparente externa real para Windows (modo Sem Bordas / Borderless Windowed):
1. **Gerenciador de Múltiplas Superfícies (`MultiSurfaceOverlayManager`)**: Alterna automaticamente entre a superfície do **Minimapa** (durante a exploração normal) e a do **Mapa Expandido** (quando o mapa nativo é aberto com a tecla M).
2. **Anti-Contaminação da Captura (`SetWindowDisplayAffinity`)**: Exclui a janela do overlay da captura de tela do DWM (`WDA_EXCLUDEFROMCAPTURE = 0x00000011`) para que o OpenCV não capture os próprios ícones de sobreposição.
3. **Hotkeys Globais no Windows (`RegisterHotKey`)**: Listener em thread de baixo nível para capturar teclas de atalho (`F11`, `F12`) mesmo com o Genshin Impact em foco total.
4. **Rastreador da Janela do Jogo (`GameWindowTracker`)**: Acompanha movimentação, redimensionamento e resolução do Genshin Impact, realinhando o overlay automaticamente.
5. **Preservação de Click-Through Total**: O jogo continua recebendo 100% dos cliques do mouse, rolagem de zoom e teclas sem qualquer interferência do overlay.

---

## Workspace Root
Caminho absoluto: `/mnt/d/Projects/GenshinGemWish`

---

## Entregáveis Desta Execução

### 1. Módulos em `src/overlay/`
Criar / Expandir:
- `src/overlay/capture_exclusion.py`:
  - Função `set_capture_exclusion(hwnd: int, exclude: bool = True) -> bool`:
    - Chama `SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)` via `ctypes.windll.user32`.
    - Verifica build do Windows ($\ge 19041$ para exclusão DWM; fallback gracioso).
    - Camada mock segura para Linux/CI.
- `src/overlay/global_hotkeys.py`:
  - Classe `GlobalHotkeyListener`:
    - Thread daemon dedicada executando `RegisterHotKey` e `GetMessageW` no Windows.
    - Suporta registro de atalhos (ex.: `F11` para alternar HUD/Configurações, `F12` para Ocultar/Exibir).
    - Despacho assíncrono de callbacks sem bloquear a fila de mensagens do sistema operacional.
    - Suporte mock em ambientes não-Windows.
- `src/overlay/window_tracker.py`:
  - Classe `GameWindowTracker`:
    - Monitora o estado e as dimensões da janela do jogo via `FindWindowW(None, "Genshin Impact")` e `GetClientRect` / `ClientToScreen`.
    - Detecta mudanças de coordenadas $(X, Y, W, H)$ e minimização.
    - Emite callbacks `on_window_moved(rect)` para ajuste em tempo real.
- `src/overlay/multi_surface_manager.py`:
  - Enum `ActiveSurfaceState`: `GAMEPLAY_MINIMAP`, `NATIVE_MAP_OPEN`, `MENU_OR_LOADING`, `NO_GAME`.
  - Classe `MultiSurfaceOverlayManager`:
    - Coordena os projetores `MinimapProjector` (Marco B) e `ExpandedMapProjector` (Marco A).
    - Alterna dinamicamente a superfície visível com base no estado do jogo detectado (`GameStateDetector`).
    - Garante estilos estendidos `WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST`.

### 2. Integração no `src/app.py`
- Conectar o `MultiSurfaceOverlayManager`, `GlobalHotkeyListener` e `GameWindowTracker` no ciclo de vida da aplicação.
- Separar o painel flutuante de Configurações / Seleção de Marcadores (onde o jogador escolhe quais categorias deseja buscar) das superfícies transparentes do jogo.
- Aplicar `set_capture_exclusion` na janela raiz para proteção anti-contaminação.

### 3. Testes Automatizados de Regressão e Validação
Criar `tests/test_multi_surface_overlay.py`:
- `test_surface_state_transitions`: Verifica transição correta entre `GAMEPLAY_MINIMAP`, `NATIVE_MAP_OPEN`, `MENU_OR_LOADING` e `NO_GAME`.
- `test_capture_exclusion_api`: Testa chamada de exclusão de captura no Windows com fallback mock.
- `test_global_hotkeys_dispatch`: Testa registro e acionamento de atalhos globais.
- `test_window_tracker_bounds_detection`: Testa cálculo de coordenadas da janela e disparo de eventos de redimensionamento.
- Executar `pytest tests/` garantindo que todos os 91 testes anteriores continuem passando + novos testes do Marco C (totalizando 95+ testes).

### 4. Atualização de Documentação e Recompilação do Executável
- Atualizar `docs/REMODEL_ROADMAP.md` registrando o Marco C como concluído.
- Recompilar `GenshinOverlay.exe` usando o Python 3.12 do Windows.
- Atualizar `README.md`.

Ao concluir, envie um relatório completo com os caminhos dos arquivos criados, evidências dos testes de superfície e status do executável.
