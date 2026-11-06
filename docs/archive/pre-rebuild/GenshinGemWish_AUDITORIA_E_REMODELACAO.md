# GenshinGemWish — auditoria do ZIP e plano de remodelação

Data da revisão: 2026-11-02. Fonte: ZIP `GenshinGemWish.zip` fornecido pelo usuário. Análise estática do código extraído; execução de `python -m pytest tests -q` em Linux (Python 3.13.5), com **78 testes aprovados**. Não foi executado o `.exe` Windows nem feito teste com o Genshin aberto.

## Objetivo corrigido

O aplicativo não deve apresentar um **segundo mapa independente**. Deve desenhar **ícones geograficamente ancorados** em uma janela externa transparente e click-through, alinhada visualmente a duas interfaces que já existem no Genshin Impact:

1. **Minimapa circular da jogabilidade:** marcadores que pertençam à região visível do minimapa, projetados e recortados dentro do círculo, acompanhando o personagem, zoom/escala e eventual rotação.
2. **Mapa expandido nativo (tecla M):** os mesmos marcadores selecionados, sobrepostos em posições corretas no próprio mapa original, acompanhando pan e zoom do Genshin, sem substituir, desenhar outra base cartográfica ou bloquear a navegação do jogo.

Mostrar **somente marcadores das categorias ou resultados de busca explicitamente selecionados**. Com zero selecionados, mostrar zero. Os baús são fixos em coordenadas do mundo, nunca em pixels estáticos da tela; suas coordenadas na tela mudam quando a câmera ou o mapa se movem.

## Evidências no código entregue

| Evidência | Arquivos | Impacto |
|---|---|---|
| Janela própria com grade e marcadores desenhados no `Tkinter Canvas` | `src/app.py`, método `redraw_map()` | Não há textura/mapa visual do Genshin nem projeção sobre a interface do jogo |
| O compacto é um HUD textual de 420×48 | `src/app.py`, `_build_gui_widgets()` e `_update_gui_layout_for_mode()` | Não coloca marcadores no minimapa nativo |
| O modo expandido cria a janela própria 1000×700 | `src/app.py`, `_update_gui_layout_for_mode()` | Não acompanha a abertura e o movimento do mapa nativo (M) |
| Rastreador CV começa sem mapa de referência | `src/tracking/autotracker_service.py` cria `MinimapTemplateTracker()`; `src/tracking/position_tracker.py` requer `_reference_map` | Sem fornecer referência, `estimate_position()` retorna inválido; live tracking não está comprovado |
| Coordenadas transformadas relativamente apenas à câmera própria | `src/map/map_renderer.py` | Não existe calibração entre coordenadas do dataset, pixels do minimapa e pixels do mapa expandido do jogo |
| Demo de 50 marcadores em Mondstadt/Liyue etc. | `data/demo_markers.json` | Não corresponde ao mapa gelado exemplificado; não pode ser apresentado como localizações verificadas |
| Atalhos vinculados ao foco da janela Tk | `src/app.py`, `root.bind('<F11>')`, `root.bind('<F12>')` | Não são hotkeys globais confiáveis durante o foco no Genshin |
| Todas as categorias desmarcadas viram filtro `None` | `src/app.py`, `get_filtered_markers()` | **Bug funcional:** zero seleção passa a significar exibir todas as categorias |
| Crop do minimapa com retângulo proporcional fixo | `src/capture/base.py` | Pode falhar com variações do HUD, UI scale, resoluções e layouts |
| Captura por GDI BitBlt de desktop | `src/capture/win32_capture.py` | Precisa validar com modo sem bordas e evitar capturar os ícones do próprio overlay |
| Texto afirma risco zero/compatibilidade garantida | `README.md`, `docs/OSS_AUDIT.md` | Alegações não demonstradas; não é possível garantir aprovação pelo anti-cheat ou ausência de sanções |
| Benchmarks sobre operações e dados de teste | `docs/BENCHMARKS.md` | Não medem alinhamento geográfico real, exibição Windows, impacto em FPS do jogo nem latência ponta a ponta no cenário real |

## O que preservar

- `src/markers/models.py` e `marker_repository.py` (corrigindo semântica de filtros e adicionando georreferenciamento e proveniência).
- `src/progress/progress_manager.py` (persistência local).
- `src/overlay/win32_overlay.py` e `overlay_manager.py` (base de janelas transparentes; é necessária revisão das superfícies e estados).
- `src/capture/` (contratos de captura e detecção da janela; calibrar HUD e capturar sem contaminar pela própria sobreposição).
- `src/tracking/` (contratos e serviços; não alegar rastreamento real até fornecer tiles/recursos de referência e validar).
- `src/performance/` (instrumentação, expandindo métricas para registro visual e sobreposição real).
- `tests/` (78 testes existentes como regressão).

## Arquitetura recomendada

```
Captura externa do frame do Genshin
       |
       +--> Detector de estado visual: gameplay / mapa nativo aberto / outro
       |       |
       |       +--> Localizador do minimapa: ROI, centro, raio, escala, rotação
       |       +--> Registrador do mapa expandido: correspondências visuais, zoom, pan
       |
       +--> Coordenadas normalizadas do jogo + confiança
                 |
Dataset autorizado --> Fonte de marcadores --> Filtro único da busca/seleção --> Marcadores ativos
                 |                                             |
                 +---------------------------------------------+
                                       |
                            Projetor por superfície
                                       |
                    +------------------+------------------+
                    |                                     |
             Overlay minimapa                   Overlay mapa expandido
          (círculo + transparência)           (ícones sobre o jogo)
```

Os dados do mundo ficam estáveis e independentes da renderização. Dois projetores convertem a mesma posição `(x,y,layer)` para pixels da tela. Para o mapa expandido usar mapeamento calibrado e atualizado (similaridade/afim/homografia quando apropriado) e mecanismos de recuperação após zoom/pan. Para minimapa centralizar no jogador, considerar direção, escala e máscara circular.

## Fases objetivas de implementação

1. **Redirecionar a UI**: uma janela de configurações para pesquisa/seleção + duas superfícies externas de renderização. Desabilitar por padrão o mapa fictício como interface principal; manter só como modo de depuração explícito.
2. **Prova de posição no mapa expandido**: escolher *uma única região* e um conjunto pequeno de marcadores conhecidos, com imagens de referência permitidas. Calibrar usando pontos de controle e validar acurácia em screenshots de diferentes pan/zoom antes de ampliar cobertura.
3. **Minimapa circular**: detector da área do minimapa, projeção dos mesmos marcadores, recorte circular, suporte a escala/rotação; não desenhar fora do círculo.
4. **Filtros e progresso**: um único conjunto `active_marker_ids` para ambas as superfícies, sem seleção = sem marcadores; coletados ocultáveis, progresso persistido por ID.
5. **Rastreamento CV e estados**: habilitar somente após referências reais, integração de posição e confiança; se perda de calibração, ocultar ícones em vez de posicioná-los erroneamente.
6. **Teste Windows + jogo**: overlays acima da janela, modos sem bordas, DPI, resoluções, multitela, modo M e gameplay, interferência no mouse, hotkeys globais, anti-contaminação da captura e estabilidade de FPS.

## Critérios de aceite

- No modo de jogo, os baús selecionados aparecem *dentro* do minimapa original, ancorados no mundo, seguindo o deslocamento da paisagem.
- Ao apertar M, os mesmos baús aparecem *sobre* o mapa nativo, com alinhamento preservado em zoom e pan; nenhum mapa paralelo é exibido.
- Filtrar por tipo de baú exibe **somente** os IDs ativos em ambas as superfícies. Zero selecionados = zero marcadores.
- Ao marcar coletado e ocultar coletados, o marcador desaparece de ambas as superfícies imediatamente e permanece oculto depois de reiniciar.
- Quando não há calibração confiável, as sobreposições ficam ocultas com indicação discreta, sem falsos posicionamentos.
- Nenhuma injeção/alteração do processo, automação de inputs, tentativa de burlar anti-cheat ou API privada não autorizada.
- Evidência com screenshots/capturas reais e medidas de erro de posicionamento e desempenho, não apenas testes sintéticos.

## Nota sobre uso de projetos open source

Antes de importar código, recursos de mapa ou datasets, revalidar URL, licença do commit/fonte exata, origem e condições de uso. Documentar `THIRD_PARTY_NOTICES` e manter código de terceiros isolado. O ZIP contém afirmações de licença e garantia de segurança que não foram aqui verificadas externamente.
