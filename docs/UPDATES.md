# Launcher e instalador Windows

## Diagnostico do minimapa

- Separa a observacao visivel da ultima pose verificada e registra rejeicoes.
- Grava o canto do minimapa mediante inicio explicito, com limites de duracao e espaco, e permite exportacao manual.

## AutoMark — recompensas e recuperacao de mapas

- Perdas de alinhamento com o minimapa ainda visível não iniciam buscas pesadas
  em outros mapas. Após uma posição confirmada, a busca requer evidência de
  carregamento/menu ou mapa M e cinco segundos sem localização válida.
- A busca fica pausada durante a sequência de abertura/recompensa e não desativa
  nem reinicia o AutoMark. A troca de mapa realmente confirmada mantém a
  invalidação do contexto, dos candidatos e das aberturas anteriores.
- Confirmação alternativa por dois ícones distintos entre EXP, gema e Mora.
  Não depende de Obtido/Obtained ou dos nomes traduzidos das recompensas.
  A abertura, a posição comprovada e a ausência de ambiguidade continuam exigidas.
- Pacote adicional `icon-signals.json`, com nomes próprios de arquivos, preserva
  as referências textuais existentes. Se estiver inválido, o pacote anterior
  continua funcionando. Não há redução dos limiares de reconhecimento.
- Replays positivos/negativos, com textos desconsiderados e sem gemas ou sem EXP,
  passaram em 1366×768 e redimensionamentos sintéticos FHD/QHD. O funcionamento
  no HUD real em inglês foi confirmado localmente pelo jogador.

## Em desenvolvimento — mapas separados e mapa global

- Registro compartilhado dos sete mapas permanentes, com nomes PT/EN, limites
  publicados e 44 camadas próprias dos mapas separados. IDs e coletas permanecem
  no catálogo AppSample original; cavernas de Teyvat não foram ampliadas.
- Modo Automático recupera mapas pelo minimapa e pelo M. Após cinco segundos sem
  localização válida e evidência de transição, busca em segundo plano, no máximo um candidato por segundo,
  e exige três quadros válidos e distintos. Resultados de contextos antigos são
  rejeitados e AutoMark é ressicronizado nas transições.
- O caminho estável de Teyvat continua usando o mesmo reconhecedor. Índices de
  recuperação são limitados a 1.200 descritores por mapa, incluindo seus andares;
  somente o mapa ativo e um candidato usam reconhecimento detalhado simultâneo.
- Mapa global permite escolher mapa/camada independentemente do jogo. Coletas e
  Desfazer usam o escopo consultado; Área atual volta ao contexto reconhecido.
  Imagens e índices do mapa anterior são liberados ao trocar de área.
- Preparação reproduzível: `scripts/prepare_separate_maps.py` e
  `scripts/prepare_map_layers.py`. Auditoria: `scripts/audit_map_expansion.py`.
  Capturas, logs e caches de reconhecimento não entram nos pacotes.
- Medição local de 55 quadros estáveis de Teyvat: acréscimo médio de 0,0055 ms
  (0,07%). Índice de recuperação: aproximadamente 15 MiB. Esses números não
  representam validação em todas as áreas, resoluções ou condições de jogo.
- Aceite em jogo dos mapas novos, em janela/fullscreen, permanece pendente.
  A release pública anterior não foi substituída.

## Em desenvolvimento — português e inglês

- Instalador oferece seleção de idioma. Ajustes do painel principal mostram
  `Idioma / Language`; alterações passam a valer ao reabrir o aplicativo.
- Interface, mensagens de inicialização e nomes revisados do catálogo recebem
  apresentação em inglês. IDs, grupos internos, regras, coordenadas, nomes de
  perfis existentes e progresso continuam preservados. Busca aceita os aliases
  nos dois idiomas.
- Preferência em `%LOCALAPPDATA%\HexenMap\language.json`, fora da pasta `state`.
  Instalações com `state-dir.txt` usam a pasta pessoal apontada pela instalação,
  inclusive quando abertas com outra conta de administrador. Atualizações
  silenciosas preservam a escolha do aplicativo.
- O idioma da interface é independente do HUD do jogo. O pacote adicional de
  ícones permite confirmar recompensas sem depender dos textos traduzidos.

## Versão 1.0.7 — óculis, interação e painel

- AutoMark de baús fica acima do rodapé, com interruptor estilizado,
  status quando ligado e botão compacto para sincronizar novamente. Report,
  Apoiar e Jogar ficam alinhados na linha inferior, com menos espaço vazio.
  A seção sai dos Ajustes; detalhes das referências continuam no Diagnóstico.
- Óculis usam halo sombreado escuro/violeta graduado no lugar da borda branca;
  a região clicável continua limitada à arte original.
- Superfícies de clique, cartões e controles internos tratam WM_MOUSEACTIVATE
  com MA_NOACTIVATE: recebem o clique sem solicitar ativação da janela.
  A proteção só é instalada em janelas do próprio processo e é removida ao
  destruir os controles ou encerrar o aplicativo.
- Seleção de itens sobrepostos usa botões sem janela suspensa. Fotos ampliadas
  abertas pelo cartão passam a ser janelas pertencentes ao jogo e sem ativação,
  com botão explícito para fechar. Mapa independente mantém o fluxo normal.
- Testes Win32/Tk verificam a resposta de ativação nos controles. A preservação
  do fullscreen durante cliques ainda precisa de validação real no Genshin.

## Versão 1.0.6 — compatibilidade e interação

- Preservadas as correções recentes de captura gráfica em Windows sem
  `MinimumUpdateInterval` e de ancoragem do botão recolhido à área do jogo.
- AutoMark procura também escalas de HUD entre 80% e 120% em passos de 10%,
  uma escala adicional por amostra, mantendo os limiares e a confirmação de
  abertura/recompensa. Diagnóstico diferencia referências ausentes e inválidas.
- Ao ativar AutoMark, sincroniza captura/HUD e posição atual; exige três
  amostras localizadas para indicar tela/posição sincronizadas. A escala final
  continua sendo confirmada visualmente ao aparecer o sinal de baú. Ajustes
  mostram o andamento e oferecem Sincronizar novamente. Ressincronizar descarta
  calibração e aberturas anteriores; eventos carregam a geração correspondente.
- Report fecha após recebimento confirmado; falhas mantêm o texto.
- Launcher aparece na barra de tarefas e no Alt+Tab, recebendo foco ao abrir.
- Fixar/desprender fica acessível no início dos Ajustes. Leve/Global sai da
  interface; preferências antigas passam ao backend limitado sob demanda.
- Ctrl prepara somente regiões de clique a até 120 pixels lógicos do cursor,
  sem limitar quais baús são desenhados. Não prepara máscaras com Ctrl solto.
- O mapa não herda previsão de movimento de uma localização anterior após
  mudança de continuidade. Captura gráfica libera recursos do AutoMark inativo
  e pode reiniciar com a mesma geometria; removida uma cópia temporária de frame.
- Investigação de instabilidade do minimapa: cache sob demanda preserva o último
  bloco de terreno reconhecido durante buscas alternativas, mantendo o limite
  de dois blocos e o orçamento de memória. Se necessário para respeitar esse
  orçamento, a referência protegida também pode ser liberada. Testes cobrem
  buscas repetidas e troca de referência; eficácia sobre os relatos de perda
  visual ainda requer validação em jogo.
- Corrigido o erro de incerteza após suavizar uma pequena correção do minimapa:
  o ponto intermediário considera metade da discrepância mais o erro da
  referência absoluta. Quando essa combinação excede 2,5 pixels, mantém a
  referência absoluta verificada em vez de criar uma combinação inviável para
  o próximo frame. Limites de fluxo, validade e comportamento do mapa M
  permanecem iguais. Regressão reproduzida com LK/RANSAC real em imagem parada;
  78 testes relevantes passaram. Cadência da captura não foi alterada nesta etapa.

Validação local: replay de duas sessões positivas e uma negativa, cada uma em
1366×768, 1920×1080 e 2560×1440, mantém os eventos esperados e nenhum evento
negativo. Redimensionamentos são sintéticos, não validação em outros PCs.
Benchmark sintético de 1.000 ícones: construção da máscara passa de 26,12 ms
para 3,22 ms e o tamanho da região de 339.872 para 27.232 bytes com 78 ícones
próximos. Esses números não medem latência total nem RAM do jogo/app.

Pendentes de validação real: fullscreen exclusivo/sem bordas, AutoMark nos PCs
dos testadores e comparação da RAM total em exploração prolongada. A captura
gráfica existente continua como recuperação de GDI; não há garantia de
sobreposição externa em fullscreen exclusivo.

Implementação inicial de 10/11/2026. Artefatos locais de teste; publicação de
release e autorização para redistribuir o conjunto de mapas/arte continuam separadas.

## Uso

O instalador por usuário cria **Hexen Map** no menu Iniciar, na busca do Windows
e em Aplicativos instalados. O atalho abre `HexenMapLauncher.exe`. A pasta padrão
é `%LOCALAPPDATA%\Programs\Hexen Map`, sem exigir administrador para instalar.
Ao abrir o launcher, o Windows pede administrador antes da verificação de
atualizações. Depois de autorizado, o launcher inicia o overlay herdando essa
permissão, sem novo pedido. A continuação após atualização também herda a
elevação do instalador. Cancelar a autorização impede a abertura.

Desde a 1.0.1, coletas e preferências ficam em `%LOCALAPPDATA%\HexenMap\state`,
fora da pasta do programa. O caminho original é registrado em `state-dir.txt`.
`userData` continua contendo recursos e caches. Saves anteriores encontrados
são migrados com backup; sem save encontrado, o usuário escolhe importar um
arquivo antigo ou confirmar um perfil novo. Falhas não autorizam sobrescrever
progresso com uma base vazia. Veja [PROGRESS_RECOVERY.md](PROGRESS_RECOVERY.md).
Não há sincronização em nuvem: faça backup da pasta pessoal com o app fechado.
O instalador inclui dados iniciais, nunca os saves do desenvolvedor.

A instalação registra sua conta original em `installed-user.txt`. Se forem
usadas credenciais de outra conta administradora na abertura do launcher,
ele mantém a pasta e os saves originais e abre o overlay, mas não executa a
atualização por usuário naquela conta diferente. Isso evita mover atalhos e
registro para o administrador informado. Atualize pela conta que instalou.

## Atualização ao abrir

### Requisito para a próxima versão após 1.0.5

- Manter o Hexen Map identificável na barra de tarefas e no Alt+Tab durante
  verificação, download, validação e instalação da atualização.
- Exibir a etapa atual e o progresso do download, permitindo trazer a janela
  de volta à frente sem interromper a atualização.
- Durante a troca do launcher pelo instalador, manter uma janela de status
  visível até a reabertura do aplicativo, sem deixar a atualização parecer
  encerrada ou travada. Preservar o fluxo automático, sem cliques obrigatórios.
- Validar atualização real de 1.0.5 para a próxima versão: barra de tarefas,
  Alt+Tab, continuidade do status e preservação dos saves.

O launcher mostra uma abertura breve, centralizada, com animação giratória,
sem botões nem cliques no fluxo normal. Consulta até 30 Releases públicas de
`victoregit/HexenMap-Releases`.
Uma instalação beta acompanha betas e estáveis; uma estável aceita somente
estáveis. Tags usam `vMAJOR.MINOR.PATCH` ou `vMAJOR.MINOR.PATCH-beta.N`
(alpha e rc também são aceitos). Rascunhos, versões antigas e ativos inválidos
são ignorados. Sem atualização, o launcher abre o aplicativo. Se houver erro
de rede, limitação da API ou repositório privado, abre a versão instalada automaticamente.

O ativo deve chamar-se `HexenMap-VERSAO-Setup-x64.exe`, com tamanho e digest
`sha256:…` informados pela API do GitHub. O launcher baixa o arquivo, confere
tamanho, SHA-256 e cabeçalho Windows antes de executá-lo. Sem digest, não há
instalação automática. Não há tokens ou credenciais embutidos. Isso verifica
integridade; o instalador ainda não possui assinatura Authenticode própria.

A atualização automática usa o mesmo instalador por usuário em modo totalmente silencioso,
com a pasta atual explícita. O launcher sai para liberar seus arquivos e o
instalador o reabre ao concluir. Tanto o launcher quanto o instalador bloqueiam
a atualização enquanto o overlay estiver aberto. Não se encerra o jogo ou o
overlay à força. A cópia baixada fica em `updates` para diagnóstico/reinstalação.

## Recuperação

Ao trocar de versão, o instalador salva os três executáveis, `BUILD.json` e o
marcador de versão em `.previous`. Se a versão nova não funcionar, feche overlay
e launcher e execute `Restaurar versao anterior.cmd` na pasta instalada.
O script aceita somente versões 1.0.1 ou posteriores, que usam o mesmo save fixo.
Versões anteriores são bloqueadas para não reabrir dados antigos de outra pasta.
O script restaura somente os arquivos do programa e pausa a atualização automática,
evitando reinstalar imediatamente a mesma versão com falha. Nesse estado, o
launcher abre diretamente a versão restaurada. Remova o arquivo `updates-paused`
da pasta instalada para retomar as atualizações. Backups incompletos são recusados antes da
cópia; nesse caso, execute o instalador anterior. `userData` permanece intacta.

## Geração e publicação

1. Atualize as versões em `src/live/identity.py`, `pyproject.toml` e no recurso
   Windows. Gere e confira o pacote portátil com `scripts/build_release.py`.
2. Instale o compilador oficial Inno Setup 6.4+ ou 7. Execute
   `python scripts/build_installer.py --iscc "CAMINHO/ISCC.exe"`.
   O script verifica o inventário e os hashes do pacote, compila o launcher e
   produz o Setup e seu `.sha256` em `dist/installer`.
3. Confira instalação limpa, upgrade, recuperação e preservação das coletas.
   Publique o Setup e o `.sha256` numa Release com tag correspondente somente
   após revisar os arquivos e as condições de distribuição dos dados.

A primeira Release, `v1.0.0`, foi publicada em 10/11/2026 em
https://github.com/victoregit/HexenMap-Releases/releases/tag/v1.0.0 .
Os dois anexos e o digest do instalador foram conferidos na API pública;
o código do launcher detectou 1.0.0 usando 0.4.1-beta.1 como versão instalada.
O ciclo completo de instalação de uma próxima atualização ainda requer uma
versão posterior publicada.
