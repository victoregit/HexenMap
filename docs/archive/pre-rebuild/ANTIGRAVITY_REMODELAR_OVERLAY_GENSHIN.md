# ANTIGRAVITY CLI — REMODELAR O GENSHINGEMWISH PARA OVERLAY GEORREFERENCIADO SOBRE O MAPA ORIGINAL DO GENSHIN

Você é engenheiro sênior de sistemas Windows, visão computacional, geometria de mapas, renderização de overlays e Python. Sua tarefa é continuar o projeto já existente em `D:\Projects\GenshinGemWish` (em WSL: `/mnt/d/Projects/GenshinGemWish`), **sem recomeçar do zero**, refatorando a arquitetura para alcançar o comportamento nas 3 imagens de referência que o usuário forneceu.

## 0. Leia antes de modificar

- Abra `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `src/app.py`, `src/map/map_renderer.py`, `src/markers/`, `src/progress/`, `src/overlay/`, `src/capture/`, `src/tracking/` e `tests/`.
- Consulte a auditoria `GenshinGemWish_AUDITORIA_E_REMODELACAO.md` fornecida pelo usuário.
- Analise as **três imagens do usuário**: (1) marcadores de baús sobre mapa interativo, (2) minimapa circular original do jogo, (3) mapa expandido original do Genshin.
- Preserve as funções úteis de repositório de marcadores, progresso, overlay Win32, captura, serviços CV e testes. Não faça mudanças destrutivas.

## 1. Correção da visão do produto — NÃO criar outro mapa

A versão atual apresenta uma janela Tkinter com fundo gradeado, marcadores e um HUD textual. Isso **não é o resultado desejado**.

O objetivo é desenhar ícones de baús como **uma camada externa transparente, alinhada precisamente com o mapa já desenhado pelo próprio Genshin**, em dois contextos:

**GAMEPLAY / MINIMAPA:** detectar a posição e o círculo do minimapa nativo na tela do jogo. Renderizar apenas os marcadores selecionados, projetados para coordenadas relativas ao jogador e recortados no interior do círculo. Se a posição do personagem, a orientação ou a escala mudar, recalcular. Não substituir o minimapa; apenas acrescentar ícones sobre ele.

**MAPA NATIVO EXPANDIDO (M):** detectar abertura do mapa original. Sobrepor exatamente os mesmos marcadores selecionados nos pontos corretos desse mapa nativo. Quando o jogador arrastar, mover ou aplicar zoom no mapa com o mouse, os ícones devem acompanhar visualmente os locais no terreno. Não mostrar a janela própria 1000×700 como substituta do mapa do jogo.

Os baús são **estáticos no mundo**, mas **suas coordenadas em pixels mudam** durante pan, zoom, deslocamento do personagem e eventual rotação. Essa é a semântica de "fixar no local do baú".

## 2. Problemas observados no código a resolver

1. `src/app.py::redraw_map` desenha grade, círculos e rótulos em um canvas independente. Migrar o modo principal para renderização transparente sobre o jogo. Manter esse canvas apenas para debug/simulação opcional.
2. `src/app.py::_update_gui_layout_for_mode` alterna entre HUD textual 420x48 e janela própria 1000x700. Criar estados `GAMEPLAY_MINIMAP`, `NATIVE_MAP_OPEN`, `SETTINGS`, `NO_GAME` e superfícies de overlay apropriadas.
3. `AutoTrackerService` instancia `MinimapTemplateTracker()` **sem mapa de referência**. Não anunciar rastreamento real funcional até integrar referências cartográficas apropriadas, transformação de coordenadas e validação em capturas reais.
4. `MapRenderer` possui transformações apenas da câmera interna. Criar `MinimapProjector`, `ExpandedMapProjector` e `MapRegistration` sem quebrar a API antiga enquanto os testes forem migrados.
5. `get_filtered_markers` transforma categorias vazias em filtro `None`, exibindo todas; corrigir para **zero categorias = zero resultados**. A seleção explícita da busca deve determinar os mesmos IDs visíveis nas duas superfícies.
6. `root.bind(F11/F12)` só funciona com foco na janela. Investigar hotkeys globais no Windows sem capturar/bloquear entradas do Genshin; permitir customização, detectar conflito e não sintetizar comandos do jogo.
7. `calculate_minimap_crop_rect` assume proporções fixas. Calibrar com DPI, UI scale, resolução, janelas, perfis e detecção visual; fornecer opção manual de calibragem.
8. `data/demo_markers.json` contém apenas 50 pontos demonstrativos, de regiões diferentes da área gelada das capturas. Não apresentar coordenadas fictícias como localizações reais. Sem fonte de dados autorizada, validar com poucos pontos fornecidos/calibrados manualmente.
9. Remover garantias absolutas de 'zero ban risk' do README. Não há como garantir compatibilidade com os termos ou anticheat sem autorização.

## 3. Pipeline técnico obrigatório

`GameWindowLocator -> FrameCapture -> GameUIStateDetector -> MapRegistration -> WorldToScreenProjection -> ActiveMarkerFilter -> OverlayRender`.

**Coordenadas e calibração**:
- Defina um sistema de coordenadas canônico e um mecanismo versionado para transformar coordenadas de datasets autorizados em coordenadas desse sistema.
- Não presuma que unidades de um JSON comunitário equivalem a pixels do mapa nativo ou a metros. Calibre e teste.
- Para o MAPA EXPANDIDO, detectar marcos visuais estáveis no mapa original e resolver transformação mundo->tela que reflita translação e escala; usar correspondências geométricas robustas quando apropriado. Estimar qualidade do registro e rejeitar alinhamento insuficiente. Recalcular após pan/zoom/região/camada.
- Para o MINIMAPA, obter centro/raio em coordenadas de tela, posição do jogador, escala e orientação; projetar diferença `chest - player` respeitando direção do mapa e mascarar fora do círculo. Testar minimapa com e sem rotação.
- Os elementos não devem ser desenhados em coordenadas de pixel estáticas. Use um conjunto de marcadores no mundo compartilhado pelas duas projeções.
- Impedir que os próprios ícones do overlay contaminem a captura usada para reconhecimento; testar exclusão do overlay na captura ou uma alternativa segura.
- O `confidence` deve ser real e verificado. Se não houver mapa de referência/calibração: não posicionar ícones de forma enganosa. Mostrar 'calibração necessária' num painel de configuração.

**Seleção e renderização**:
- Unificar busca, seleção de categorias, IDs de marcadores selecionados, camadas, região, estado coletado e filtros num `MarkerSelectionState` com persistência.
- O mesmo `active_marker_ids` alimenta `MinimapOverlay` e `ExpandedMapOverlay`.
- `selected_categories=[]` ou `selected_marker_ids=[]` quando seleção explícita estiver ativa significa renderizar ZERO, nunca todos.
- Suportar agrupamento/limite visual em alta densidade; não cobrir teletransportes e controles do jogo.
- Ícones com contorno nítido semelhante à referência visual, mas não usar assets protegidos sem autorização. Ajustar tamanho com zoom, clipping e tamanho mínimo/máximo legível.
- O modo normal deve ser click-through, inclusive com mapa nativo aberto, para preservar arrastar e zoom do Genshin. Um painel de configurações separado pode ser interativo.
- Atualizar quando a janela do Genshin for movida ou redimensionada, inclusive DPI escalonado. Quando não estiver ativa, ocultar ou reduzir trabalho conforme configuração.

**Captura segura e estados**:
- Não injetar DLL, ler memória do processo, alterar cliente, falsificar inputs, interceptar anticheat nem usar API privada sem autorização.
- Trabalhar com captura de tela e janela externa do sistema operacional.
- Detectar se o jogo está em gameplay, mapa nativo aberto, menus/carregamento ou ausente. Apenas as superfícies apropriadas devem aparecer.
- O modo de demonstração deve funcionar com screenshots estáticas (sem jogo aberto), para testes geométricos reproduzíveis.

## 4. Estratégia de implementação por marcos, sem escopo infinito

### Marco A — Prova de conceito MAPA EXPANDIDO em imagens estáticas

Priorize esta entrega. Use a captura real do mapa expandido fornecida pelo usuário e **um pequeno conjunto de pontos calibrados**. Construa projeção dos pontos no PNG sobre uma camada de ícones transparentes; demonstre que os ícones não alteram a imagem base. Capture também versões deslocadas/zoomadas ou use transformações sintéticas com verdade-terreno conhecida. Apresente screenshot antes/depois e erro em pixels. Não passar para B até comprovar A.

### Marco B — Minimapa circular em imagem estática

Use a captura real do minimapa fornecida pelo usuário. Calibre centro, raio e transformação. Desenhe os mesmos pontos filtrados dentro da máscara circular, sem escurecer ou substituir o minimapa. Teste movimento e rotação com casos sintéticos conhecidos. Não afirmar que há rastreamento real automático se só for estático.

### Marco C — Integração Windows/jogo sem bordas

Desenhar somente ícones sobre a interface nativa quando jogo estiver presente; alternar automaticamente entre minimapa e mapa expandido. Validar click-through, captura que não inclua o próprio overlay, hotkeys enquanto Genshin está em foco, estabilidade quando janela se move ou muda resolução. Testes precisam indicar claramente o que foi verificado no Windows e o que só foi simulado.

### Marco D — Rastreamento e datasets reais

Conectar uma fonte de marcadores cuja licença e proveniência tenham sido verificadas; integrar referências visuais autorizadas e rastreamento do jogador; melhorar registro em diferentes regiões/camadas. Revalidar precisão, latência e cobertura; manter a implementação modular.

## 5. Testes que devem ser adicionados

- `zero selected = zero rendered`.
- Busca com seleção de resultado específico aplica exatamente os mesmos IDs a ambas superfícies.
- Projeção dos baús preserva o ponto de mundo quando pan/zoom muda.
- Minimapa: recorte circular e resultado correto para 0, 90, 180 graus.
- Mapa expandido: transformação mundo->tela com pontos de controle e medição de erro.
- Estados gameplay/mapa M/menu/jogo ausente, sem mostrar ícones fora de contexto.
- Tratamento de registro inválido, não mostrar ícones em locais falsos.
- Hotkeys sob foco em outra janela; não interceptar interações do jogo.
- Persistência, IDs estáveis, coleta e exclusão de coletados.
- Testes com screenshots reais + mocks, além de regressão dos atuais (ZIP tinha 78 testes aprovados em Linux).

## 6. Medidas de sucesso

- Métrica principal: erro médio/p95 em **pixels** na posição dos ícones sobre screenshots com pontos de controle conhecidos, por superfície e resolução.
- Também medir latência de captura, reconhecimento, atualização do overlay, CPU/RAM, atraso em pan/zoom e impacto percebido em FPS quando houver teste real no Windows. Não inventar números nem anunciar 'zero FPS loss'.
- As imagens devem demonstrar visualmente que o ícone está no **mesmo local do mapa que existe no jogo**, não numa grade nem sobre outro mapa desenhado pelo aplicativo.
- A documentação deve distinguir teste sintético, teste em screenshots e teste integrado em Genshin.

## 7. Licenciamento e reutilização

Auditar novamente as licenças dos repositórios/commits `Jude-Chaer/genshin-overlay`, `EliteMasterEric/Teyvat.moe` e `kongying-tavern`. Reutilizar componentes e assets apenas quando a licença individual e termos permitirem. Não presumir que uma API/JSON acessível autoriza redistribuição. Registrar origem, atribuição e restrições de código, dados e imagens separadamente. Se não houver autorização para dados reais, usar pontos pequenos calibrados e explicitamente identificados como testes, sem prometer base completa de baús.

## 8. Entregáveis desta execução

1. `docs/CURRENT_GAP_ANALYSIS.md` — diagnóstico do código existente e dos bloqueios reais, com links de arquivos e funções.
2. `docs/GAME_MAP_REGISTRATION.md` — como detectar estado do mapa, calibrar coordenadas, aplicar zoom/pan e calcular confiança.
3. `docs/REMODEL_ROADMAP.md` — marcos A-D e testes de aceite.
4. Código e testes do **Marco A**, no mínimo (prova de conceito visual no mapa expandido a partir de imagens estáticas).
5. Imagens de resultado comparativas, com marcadores sobre o mapa expandido original e informação do erro de alinhamento.
6. Registro do que foi verificado no Windows real vs Linux/mock; lista honesta dos bloqueios.

Não implemente geografia fictícia, mapa estilizado, um segundo mapa proprietário ou animação simulada como substitutos para o alinhamento real. Não considere a tarefa completa porque o unit test passou; o aceite depende de prova visual. Não copie automaticamente todos os repositórios nem reescreva o projeto inteiro.

**Comece pela leitura dos arquivos, faça a análise de lacunas, e implemente o Marco A usando as imagens reais se estiverem disponíveis no workspace. Se as imagens não estiverem, prepare o pipeline de teste e indique exatamente onde colocá-las. Prossiga com o máximo possível sem apagar a base existente.**
