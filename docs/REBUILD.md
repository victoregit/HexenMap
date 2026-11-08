# Hexen Map — referência única

Atualizado em 7 de novembro de 2026. **Versão integrada para revisão; expansão completa ainda não aprovada.**

## Experiência atual

O executável procura o Genshin automaticamente e desenha ícones sobre o minimapa e o mapa M nativos. O painel de 360×540 px inicia como janela independente, com barra de título do Windows, sem ficar sempre por cima e sem desaparecer ao alternar para outro aplicativo. Pode ser movido para fora do jogo, inclusive a monitores com coordenadas negativas. “Fixar ao jogo” restaura o modo compacto vinculado ao foco do jogo; “Destacar” retorna à janela independente. No modo fixado pode ser recolhido a um botão de 40×40 px. Modo e posição são salvos. O tema usa azul profundo, marfim e dourado discreto. A nação permanece fixa durante viagens. Não há filtro ou busca de áreas/localidades. Categorias novas começam desmarcadas; o botão Todos seleciona categorias revisadas (as seções técnicas/sem tradução entram somente quando expandidas ou pesquisadas), e Limpar retira inclusive seleções escondidas; seleção vazia não produz ícones. Preferências são restauradas por região.

O modo **Todos os mapas · camada automática** reconhece referências dos mapas e andares da região escolhida. O seletor de nações é uma faixa horizontal com os oito emblemas visíveis, sem seta ou lista suspensa. Clicar em um ícone seleciona a nação, destaca a opção e mostra seu nome abaixo; passar o mouse permite identificar as demais. Setas esquerda/direita e Enter/Espaço também funcionam. Os oito arquivos são carregados localmente e mantidos em memória, com origem e hashes em `data/assets/nations/SOURCE.json` e atribuição própria no NOTICE dessa pasta. O botão de camadas permanece ao lado da faixa. Não há download durante a interação. A prévia isolada conferiu os oito ícones e seleção por teclado; o pacote Windows contém os oito arquivos com SHA-256 correspondente ao manifesto e passou no diagnóstico de Liyue. Atualização de emblemas instalada na raiz, conferida por SHA-256 contra o build, com progresso e preferências intactos. Backup: `backups/nation-emblems-20261106-181831`. Dois processos sem janela mantiveram a imagem anterior em uso após fechar o painel; o executável antigo foi preservado também como `GenshinOverlay-held.exe`, sem encerrar processos.

O botão de camadas abre um painel com Automático e os mapas/andares disponíveis, busca e indicação da escolha ativa. Ele controla apenas o overlay. Os metadados territoriais continuam internos, sem filtrar áreas na interface. O mesmo recorte vale para desenho, revelação com Ctrl, cartão, coleta, desfazer e contadores. Categorias com o mesmo nome original e grupo são reunidas na lista, conservando todos os IDs de seleção e deduplicando os marcadores físicos nos contadores. Textos traduzidos iguais, por si só, nunca unem categorias diferentes. Os rótulos em português pertencem à apresentação; os nomes originais ficam nos pacotes. Categorias usuais têm traduções locais; as restantes ficam explicitamente na seção “Sem tradução revisada”. Não há alegação de tradução completa. Etiquetas técnicas da fonte ficam em uma seção secundária. A classificação fina de toda a superfície ainda não está disponível; não são inventados limites por proximidade de nomes.

A lista compacta usa um único Canvas virtual: só as linhas visíveis têm primitivas desenhadas, sem criar centenas de Checkbuttons ou StringVars. Ícones, nomes e contadores ficam em colunas; seções por finalidade têm seleção e limpeza próprias, busca sem distinguir acentos e operação por teclado. Destaques e baús começam abertos; demais grupos podem ser expandidos. Ajustes e atalhos ficam no botão de engrenagem. Os filtros incluem baús, oculi, desafios, seelies, puzzles, santuários, recursos e outros grupos da fonte. Os cinco tipos de baú têm desenhos vetoriais originais com materiais e ornamentos distintos. Os demais grupos têm símbolos próprios. A entrada normal não usa mapa fictício, simulação, posição manual nem dados demonstrativos. A implementação anterior permanece em `src/legacy_app.py`, fora do executável.

**Ctrl + clique** abre um cartão com uma única ação reversível: marcar como pego ou desmarcar. Itens coletados ficam ocultos normalmente e em cinza enquanto Ctrl estiver pressionado. A área clicável é invisível, sem quadrado de destaque. Fora dos ícones, os cliques continuam chegando ao jogo. Com o cartão aberto, os desenhos no mapa são ocultados para não conservar coordenadas antigas; mudar filtros fecha o cartão sem tirar o foco do painel. Clicar fora do cartão, concluir a ação ou pressionar Esc fecha a interação e permite continuar jogando. O painel de configurações não é ativado para confirmar coleta.

Atalhos padrão: **F8** mostra/minimiza a janela independente ou abre/recolhe o painel fixado; **Ctrl+Alt+F12** mostra/oculta; **F9** coleta o candidato próximo sem ambiguidade; **F10** desfaz a última alteração do recorte nesta sessão. São configuráveis. O atalho de visibilidade continua disponível quando o alinhamento falha. Candidatos próximos usam o minimapa reconhecido; vários candidatos exigem seleção explícita no painel, válida por 30 segundos. Proximidade sozinha nunca confirma coleta.

Neste computador, o usuário inicia o overlay como administrador para manter a interação com o Genshin elevado. O programa não automatiza elevação de privilégios.

## Dados e cobertura

A fotografia Kongying Tavern contém **126.200 marcadores utilizáveis em oito regiões**, 14 combinações região/mapa e 478 nós territoriais, incluindo 322 localidades explícitas de cavernas. Os pacotes são carregados por região. A versão é a fotografia da fonte adotada, não uma garantia independente de conteúdo de determinada versão do jogo.

**29 pontos com associação a mais de uma região estão separados**, pois algumas associações representam contagem de conquistas, e não localização física. Associações de área ambíguas não entram em localidades específicas. Pontos sem andar confiável permanecem sem camada confirmada. Árvores de plugins repetem cavernas em menus de áreas diferentes; cinco vínculos de grupos foram corrigidos pelos vínculos explícitos dos pontos. Grupos compartilhados ficam na raiz regional, sem atribuição arbitrária a uma área. O inventário conserva essa auditoria. Mapas temporários de eventos identificados pela fonte são excluídos.

O catálogo anterior de Mondstadt, com 561 posições reais Teyvat.moe, permanece como opção de compatibilidade. Os IDs existentes só são reutilizados mediante correspondência explícita de `markerStamp` com `importIds.yuanshen`. Não há transferência por proximidade. Registros sem associação são preservados.

Origem, versão, licença, atribuição e hashes acompanham cada pacote. Os dados Kongying Tavern mantêm **CC-BY-NC-SA-4.0**; os dados anteriores mantêm sua própria licença. A licença MIT do aplicativo não substitui essas condições. Créditos:

- `data/community/kongying/NOTICE.md`;
- `data/community/mondstadt/NOTICE.md`.

O inventário detalhado, os critérios da importação e as fontes estão em [REGIONAL_COVERAGE.md](REGIONAL_COVERAGE.md). Esse arquivo é um relatório de evidências, não outro plano conflitante.

## Referências pessoais

Imagens ficam em `userData/references`, fora do executável e do Git. A arte original pertence aos respectivos titulares; não foi estabelecida uma autorização independente para redistribuí-la. Uma instalação limpa sem referências compatíveis não está pronta para abrir e jogar: informa a ausência e não substitui o mapa por demonstração.

Cada manifesto associa imagem, hash, origem, permissão de uso, CRS, região, mapa, camada e transformação. Os sistemas de coordenadas Kongying e Teyvat.moe não são misturados. Hash alterado, imagem ausente, transformação inválida ou caminho externo ao pacote impedem o carregamento.

Nesta instalação há **14 candidatos de mapa/camada principal e 314 referências de cavernas** preparados e conferidos como arquivos. Isso não equivale a aprovação no jogo. Duas camadas explícitas de Fontaine ainda não têm referência correspondente; pontos sem classificação de andar também não ganham referência por aproximação. Há referências de maior detalhe preparadas quando necessárias; o pacote amplo de Natlan ainda exige tratamento do limite de tamanho e validação de desempenho.

## Reposição e progresso

**Não há regra universal de 72 horas.** Unidade numérica confirmada não basta para aprovar prazo do jogo. Valores positivos `refreshTime` são preservados em milissegundos, mas ficam sem temporizador até qualificação por recurso/tipo de ponto.

As políticas automáticas atualmente associadas são **investigações de artefatos de 12 h ou 24 h**, mediante valor explícito por ponto corroborado pelo guia KQM. Outros valores não recebem automaticamente uma dessas regras. Pesca permanece condicional; códigos negativos não são interpretados por suposição. Os 46 h observados na fonte para especialidades divergem da referência de 48 h: continuam como **Reposição não confirmada**, sem prazo inventado.

O motor distingue permanentes, duração após coleta, reset de servidor, condições especiais e desconhecidos. Reset América usa fronteira explícita em UTC, independente do fuso do Windows; a política foi testada, mas nenhum código negativo da fonte foi associado a ela sem verificação.

Coleta e disponibilidade prevista são persistidas em UTC. Prazos continuam correndo com o aplicativo fechado. Recursos com política qualificada voltam a aparecer ao vencer, como **disponibilidade estimada**, sem afirmar confirmação visual. Desmarcar cancela a indisponibilidade; nova coleta calcula novo prazo; desfazer restaura o registro anterior e seu prazo original. Permanentes nunca expiram. Políticas desconhecidas/condicionais não herdam automaticamente um prazo antigo não qualificado.

Os contadores usam a nação e o mapa/camada selecionados (Automático conta a nação inteira), independentemente das categorias visíveis, e deduplicam marcadores físicos. Progresso permanente e indisponibilidade de recursos ficam separados.

A primeira migração de preferências com filtros de área cria `settings.json.pre-nation-layer.bak` com os bytes originais antes de limpar esses filtros em todas as nações. Os atalhos antigos são preservados; se F8 estiver ocupado por outra ação configurada, o painel recebe a primeira opção livre entre F7, F6 e Ctrl+Alt+F8.

Os arquivos ficam ao lado do executável em `userData/progress.json` e `settings.json`. A gravação do progresso é atômica; falhas restauram o registro anterior em memória. As preferências usam uma fila separada de snapshots imutáveis: a última alteração pendente substitui as intermediárias, preservando a ordem das gravações. O fechamento aguarda a fila; falhas são reportadas no painel e no log. A indexação estática de contadores também ocorre em segundo plano; enquanto prepara, o painel mostra “Contando itens…” e traços em vez de totais inventados. A migração v1→v2 cria `progress.json.pre-v2.bak`, que não é sobrescrito pelas gravações seguintes. `.bak` continua como recuperação da gravação anterior. Executável, progresso e preferências anteriores também foram preservados em `backups/regional-expansion-*`. Após o teste real de coleta/desmarcação, todos os IDs anteriores continuavam preservados.

## Reconhecimento e integração

`src/live` separa catálogo territorial, reposição, referências, captura Windows, reconhecimento, acompanhamento, sessão e desenho. O aplicativo usa captura externa; não lê memória do jogo nem envia comandos ao personagem.

O índice visual contém apenas referências do recorte/região selecionados. A busca inicial aponta candidatos e o refinamento mantém no máximo três reconhecedores completos em cache. Instalar outras regiões não coloca todas as referências no ciclo de cada captura. A leitura/validação dos catálogos usa um processo auxiliar para não bloquear o interpretador da interface durante o JSON. Pedidos sucessivos mantêm somente o último pendente; resultados antigos são descartados e o cache guarda dois pacotes. A montagem da lista ocorre no Tk após o resultado, sem widgets por categoria. Erros restauram a seleção anterior; durante a troca, os ícones e as ações de coleta/desfazer ficam indisponíveis. A construção das referências ocorre fora da thread Tk e resultados de seleções antigas são descartados por geração, com cancelamento cooperativo entre imagens e etapas de indexação. Uma chamada OpenCV já em execução ainda precisa terminar antes do próximo teste de cancelamento.

O ajuste visual usa SIFT e RANSAC com consenso, distribuição espacial e erro residual controlados. O minimapa exige evidência visual da interface e da seta; o círculo útil é conservador diante da oclusão do HUD. Amostragem adicional do raster mantém a transformação geográfica exata e os mesmos critérios geométricos.

Fluxo óptico LK acompanha movimento entre registros absolutos, com verificação de ida/volta. As pirâmides LK são calculadas apenas no recorte do terreno; mapas largos usam meia resolução, reconvertendo coordenadas e limiares ao espaço original. Um resultado absoluto pendente é transportado pela cadeia de movimentos consecutivos verificados. Uma lacuna invalida essa cadeia; só uma nova correspondência visual pode recuperá-la. O horário original da âncora continua limitado a 1,5 s. A recuperação inicial do minimapa agora também transporta o resultado absoluto pelos movimentos intermediários, usando a geometria do HUD previamente reconhecida e descartando-a ao entrar em menus/perder contexto. O centro do jogador é recalculado a partir da projeção atual. A comparação entre registro absoluto e fluxo usa pontos dentro do círculo do minimapa, em vez de pontos espalhados pela tela inteira. Isso evita tratar uma pequena diferença angular local como um grande salto em uma região que nem foi observada. Resultados absolutos são atualizados para o quadro atual antes de desenhar. Uma âncora não é prolongada por mais de 1,5 s. Capturas vencidas, troca de janela/região, menus, perda de foco ou alinhamento incerto ocultam os ícones. O desenho exige observação válida com idade de até 650 ms. Mapas e andares diferentes não compartilham a projeção dos seus marcadores.

O desenho tem agendamento próprio de 16 ms, separado da captura de aproximadamente 50 ms; estes são intervalos solicitados, não FPS garantido. A seleção mantém um índice de coordenadas por recorte e consulta coleta/reposição apenas para os candidatos visíveis; não guarda disponibilidade vencida nesse índice. Os símbolos mantêm suas primitivas no Canvas e apenas mudam de posição ou estado. Em pan estável do mapa M, a apresentação usa previsão de até 60 ms, limitada a 8 px, desativada após 120 ms sem captura. Parada, inversão, zoom, mudança de superfície/camada e perda de validade interrompem a previsão. O minimapa continua acompanhado pelo fluxo óptico, sem essa extrapolação. Correções absolutas pequenas são amortecidas no mesmo instante de captura; discrepâncias acima de 24 px ocultam os ícones durante a recuperação, sem animar um salto.

O Ctrl+clique usa as posições efetivamente desenhadas e rejeita um quadro clicável com mais de 120 ms. A previsão não altera as coordenadas dos itens nem a localização usada para coleta próxima e não prolonga a validade da observação. O painel e o seletor de camadas também são excluídos da captura. Somente o painel fixado acompanha o foco do jogo; a janela independente usa o comportamento normal de uma janela Windows. Jogar minimiza o painel independente ou recolhe o fixado, devolvendo o foco quando apropriado. As superfícies dos marcadores não pertencem à janela do painel, para continuarem disponíveis quando ela é minimizada.

Os ícones e suas áreas de Ctrl+clique são excluídos quando o símbolo toca a área visível do painel (inclusive recolhido) ou das opções de camadas. Os limites físicos são lidos por GetWindowRect, incluindo a barra de título, e convertidos para a área cliente do jogo. A janela independente atrás do jogo não cria uma exclusão falsa. Além do filtro compartilhado por desenho e entrada, a própria superfície Win32 recebe uma região com os controles subtraídos; no modo fixado, os controles são reposicionados acima dos ícones sem ativar a janela. Essa proteção impede que baús cubram os controles do overlay.

A superfície visual permanece click-through. Uma superfície de entrada separada usa alfa e regiões Win32 apenas nos ícones enquanto Ctrl estiver pressionado. O leitor de Ctrl observa somente suas transições, sem bloquear ou gravar outras teclas. Atalhos entram por fila; somente Tk altera widgets. O cartão não usa grab global e só solicita retorno de foco se ele ainda pertencer ao jogo ou ao overlay.

## Evidências atuais e limites

**211 testes automatizados aprovados**, incluindo janela independente, persistência do modo, posição em monitor negativo, limites físicos e exclusão dos controles, cobrindo regressões, filtros descendentes, seleção vazia, deduplicação, mapa/camada, dados e hashes, aliases explícitos, UTC, vencimento exato, reinício, mudança de fuso, desconhecidos, permanentes, desfazer com prazo original, migração e rollback.

**Conferência real nesta instalação, em 1366×768:**

- Mondstadt: captura, reconhecimento de minimapa e M e testes integrados curtos;
- Liyue: captura e reconhecimento das duas superfícies; usuário confirmou os ícones no executável instalado e aprovou teste curto de caminhada, fechamento/reabertura de M, pan/zoom, Ctrl, marcar/desmarcar e retorno de foco;
- migração real do progresso com backup e preservação dos IDs anteriores;
- executável Windows instalado; diagnóstico aprovado e oito pacotes embutidos conferidos contra os arquivos revisados; referências e saves pessoais não foram embutidos.

Os ajustes p95 observados ficaram próximos de 0,41 px no M de Mondstadt, 0,38 px no minimapa do Porto de Liyue e 0,71 px no M de Liyue. **Esses valores medem o ajuste de imagens, não o erro independente de cada marcador nem o atraso ponta a ponta.** Capturas estáticas, testes geométricos e contagem de testes não aprovam a expansão.

Continuam pendentes:

- pontos independentes e precisão de marcadores em cada mapa/camada;
- exploração real de pelo menos 30 minutos, com registro de falhas e impacto no jogo;
- validação dos demais mapas, cavernas, teletransportes e resoluções/DPI;
- traduções ainda ausentes; classificação fina da superfície não é requisito da interface atual;
- referências indisponíveis e tratamento de mapas grandes;
- qualificação das demais políticas de reposição, códigos de reset e exceções;
- disponibilidade de arte com direitos de redistribuição para instalação pública limpa.

A nova apresentação foi conferida em prévia isolada do painel e em testes sintéticos. O cenário ideal de pan constante (captura 20 Hz, desenho 60 Hz) reduziu o erro médio de retenção de quadro de aproximadamente 2,68 px para próximo de zero; isso não mede movimento real, fluxo óptico, parada nem apresentação da GPU. Após a revisão do fluxo óptico, o usuário confirmou que o teste curto no mapa M de Liyue ficou estável ao arrastar, parar, inverter e aplicar zoom. Essa aprovação qualitativa não substitui medição independente de erro, atraso e desempenho nem a sessão de 30 minutos.

O inventário mantém `coverage_complete=false`; a situação técnica da fonte não substitui os aceites de Mondstadt e Liyue registrados pelo usuário. A expansão está autorizada, mas **não está declarada concluída**.

O novo build passou no diagnóstico empacotado de Liyue (20.692 itens e referência de superfície disponível). Após o usuário fechar o overlay, a instalação principal `GenshinOverlay.exe` foi substituída e conferida por SHA-256 contra o build de `dist`. Os hashes de preferências e progresso permaneceram intactos durante a instalação. Backup desta substituição: `backups/compact-install-20261106-171136`, incluindo manifesto dos hashes anteriores. A migração das preferências ocorre ao abrir a nova versão. O usuário reprovou a primeira apresentação em Liyue por saltos e desaparecimentos recorrentes. Os registros continham perdas de rastreamento com recuperação entre cerca de 0,5 e 2 s e idade mediana captura→submissão de 110 ms nos quadros desenhados. A revisão seguinte recorta o fluxo óptico e transporta resultados absolutos pelos movimentos intermediários; foi instalada após o usuário fechar o overlay, com backup em `backups/flow-chain-20261106-172454` e hashes de progresso/preferências preservados. Em 6 de novembro de 2026, o usuário respondeu “Ficou estável” ao repetir o teste no mapa M de Liyue. O teste curto de estabilidade está aprovado pelo usuário. Posteriormente o usuário confirmou o aceite de Mondstadt e Liyue, sem repetir essa etapa como bloqueio. Em cenário sintético de translação, o custo mediano LK caiu de 46,98 para 15,88 ms no mapa e de 36,72 para 4,78 ms no minimapa (12 amostras por combinação; não é medição de FPS do jogo). Não iniciar o arquivo de `dist` como instalação diária: os caminhos portáteis de progresso são relativos ao executável.

## Revisão do catálogo e responsividade

A revisão foi inspirada na organização do painel de marcadores do AppSample (https://genshin-impact-map.appsample.com/pt/), mantendo os símbolos próprios e os dados já auditados. Não importa imagens nem progresso desse site. Os emblemas das nações são arquivos de outras fontes públicas com atribuição separada; não são símbolos originais do projeto.

- Mondstadt: 478 categorias da fonte viram 259 entradas de apresentação; 36 ainda sem tradução revisada.
- Liyue: 605 categorias viram 282 entradas; 17 ainda sem tradução revisada.
- Sumeru: 642 categorias viram 295 entradas; 115 ainda sem tradução revisada.
- O teste nativo isolado de alternância rápida Mondstadt→Liyue→Sumeru aplicou somente Sumeru. No painel expandido de 360×540 px, a lista ficou em 321×288 px e desenhou 102 primitivas para as linhas visíveis, com zero widgets filhos por categoria. Não é uma medição de FPS do jogo nem garante ausência de pausas em todo hardware.
- Os 188 testes incluem snapshots ordenados das preferências, descarte de pedidos obsoletos, erro de pacote, cancelamento de índice, alias sem duplicação e preservação dos IDs.

A revisão foi instalada na raiz com SHA-256 idêntico ao build, mantendo os hashes de progresso/preferências anteriores. Backup: `backups/catalog-browser-20261106-175537`. O diagnóstico do executável em instalação isolada confirmou Liyue (20.692 itens), referência de superfície e `catalog_worker=available`, exercitando o processo auxiliar no pacote Windows.

Em 6 de novembro de 2026, o usuário aprovou a melhora de resposta do painel e a permanência na última nação escolhida, respondendo “Responde melhor e mantém a nação escolhida” após o teste solicitado de alternância, busca e rolagem. Isso registra aprovação qualitativa da responsividade e da troca de nação; não aprova automaticamente a precisão dos marcadores, todos os filtros, coleta/foco desta revisão ou desempenho em sessão longa. As sessões de 30 minutos, as traduções restantes e a expansão continuam pendentes.

## Janela independente e instância única

O usuário voltou a relatar marcadores sobre os controles após o primeiro filtro de coordenadas Tk. A investigação encontrou duas instâncias do aplicativo com janelas simultâneas. A revisão adiciona limites físicos, recorte nativo da superfície, modo independente padrão e uma trava Windows de instância única. Ao abrir outra vez, o aplicativo procura trazer o painel já existente para a frente; não inicia outra captura nem outro conjunto de ícones.

A conferência nativa isolada validou o recorte com GetWindowRgn/PtInRegion, a continuidade da superfície de marcadores após minimizar a janela e a aquisição/liberação da trava de instância única. Isso não substitui a confirmação do usuário no jogo. A revisão foi instalada na raiz com backup `backups/detached-panel-20261106-183910`, executável conferido contra o build e hashes de progresso/preferências intactos. O diagnóstico empacotado aprovou Liyue e o processo auxiliar. O teste isolado do aplicativo confirmou inicialização, minimizar/restaurar, ciclo de UI e fechamento. Em 6 de novembro de 2026, o usuário confirmou “Janela independente funciona e não há sobreposição” após o teste solicitado de mover, minimizar/restaurar e selecionar categorias. Ficam aprovados qualitativamente o funcionamento da janela independente e a ausência de marcadores sobre os controles nesta revisão. Isso não aprova a precisão dos demais mapas, desempenho em sessão longa ou traduções ainda pendentes.

## Continuidade do minimapa durante movimento

Após aprovar o painel independente, o usuário relatou piscadas ao caminhar/correr. A investigação encontrou que a recuperação por movimentos intermediários estava habilitada no bootstrap do mapa M, mas não no do minimapa, e que a comparação de correções do minimapa usava pontos da tela inteira. A revisão corrige ambos sem prolongar o limite da âncora de 1,5 s ou exibir transformações vencidas. Menus continuam descartando geometria e movimentos pendentes.

Os 197 testes incluem minimapa em movimento com resultado absoluto atrasado, rotação pequena medida apenas dentro do círculo e descarte ao abrir menu. As transições de rastreamento registram `tracking`, `anchor_expired`, `flow_lost` e `correction` no log, com idades da âncora e do pedido pendente. A revisão foi instalada após o usuário encerrar o overlay, com backup `backups/minimap-continuity-20261106-190123`, executável conferido por SHA-256 e progresso/preferências intactos. O usuário encerrou a etapa de aceite de Mondstadt e Liyue e autorizou avançar na expansão, sem repetir testes. Não há medição independente que permita afirmar eliminação total das piscadas.

## Expansão autorizada e próximos marcos

O usuário confirmou o aceite de Mondstadt e Liyue e determinou avançar até a nação mais recente da base adotada. Não repetir pedidos de aceite dessas regiões. A ausência de métricas de uma sessão longa continua registrada como limite de evidência, sem bloquear a expansão autorizada.

1. Integrar e conferir os mapas separados, Inazuma, Sumeru, Fontaine, Natlan, Nod-Krai e Snezhnaya na classificação do inventário adotado.
2. Preparar referências detalhadas faltantes e auditar hashes, CRS e associação de mapa/camada. Mapas grandes podem usar `prepare_regional_reference.py --partition --zoom -1`, preservando a referência principal e acrescentando blocos sobrepostos de no máximo 16×16 tiles.
3. Conferir a projeção offline com `scripts/check_regional_alignment.py`. O relatório testa três recortes detalhados por mapa contra a própria referência; não representa comparação com capturas do jogo, aceite de cavernas nem precisão independente dos marcadores.
4. Tratar apenas problemas concretos e validações de mapas novos, sem reiniciar o aceite das regiões aprovadas.
5. Completar traduções e regras de reposição qualificadas; regras desconhecidas ficam sem prazo.

## Diagnóstico e desenvolvimento

`userData/live-session-v2.csv` registra superfície, região/mapa/camada reconhecidos, geração, latência de processamento, confiança e erro de ajuste. Não contém screenshots. `overlay.log` registra diagnóstico e interação. `userData/display-session.csv` registra idade captura→submissão do desenho, custo de projeção/desenho, quantidade de ícones e previsão aplicada. Esse tempo não inclui a apresentação do Windows/GPU e não equivale ao atraso completo visto pelo jogador. O impacto no FPS ainda exige medição; tempo sem foco não conta como exploração. Capturas de pesquisa ficam em `build`, fora do pacote.

```powershell
python src/app.py
python src/app.py --diagnose
python -m pytest -q
python scripts/build_exe.py
python scripts/preview_panel.py
python scripts/benchmark_display.py
python scripts/live_report.py
python scripts/coverage_report.py --output build/regional-audit/local-coverage.json
```

`--diagnose` usa a seleção salva, não abre UI e retorna 2 se faltarem dados/referências. O build não encerra processos do usuário para substituir um executável bloqueado. `scripts/import_kongying.py` importa somente por rotas de leitura, sem conta ou cookies do usuário; `--offline` reconstrói a partir da exportação auditada. Tokens transitórios não são persistidos. Os preparadores de referências mantêm imagens pessoais em `userData`, conferem formato/projeção e não fabricam terreno para downloads ausentes.

O histórico anterior fica em `docs/archive/pre-rebuild`.

A faixa horizontal e a exclusão de marcadores sobre os controles foram instaladas na raiz com backup `backups/nation-strip-20261106-182449`. Executável conferido por SHA-256, progresso e preferências intactos; prévia e 18 regressões de apresentação/clique aprovadas. A aprovação posterior da janela independente confirmou a ausência de sobreposição de marcadores nos controles.


## Referências da expansão disponíveis nesta instalação

A preparação detalhada de Natlan foi concluída em seis blocos sobrepostos, preservando a referência principal. Os oito catálogos, 14 mapas principais/separados e 328 manifestos foram auditados. A checagem de recortes da própria referência passou nos 14 mapas; não equivale a teste no jogo. A implementação existente carrega esses arquivos locais ao selecionar a nação/camada, sem necessidade de reinstalar o executável. Mais detalhes e lacunas em REGIONAL_COVERAGE.md.

O diagnóstico do executável instalado também passou nos oito catálogos em uma instalação isolada, conferindo identidade regional, processo auxiliar e referências de superfície. Relatório: `build/regional-package-check/results.json`. Não abriu o jogo nem alterou preferências/progresso da instalação principal.


## Pins de baús com arte oficial

Os cinco tipos de baú usam imagens do catálogo público do mapa oficial HoYoLAB, conferidas visualmente: comum, sofisticado, precioso, luxuoso e extraordinário. Origem, URLs, IDs e SHA-256 estão em `data/assets/chests/SOURCE.json`; a atribuição e o limite de uso ficam no NOTICE do mesmo diretório. Os PNGs estão somente em `userData/assets/chests`, fora do Git e do executável. `scripts/prepare_chest_assets.py` prepara a instalação pessoal; `--check` confere hashes sem rede. Imagem ausente ou alterada conserva o símbolo anterior daquele tipo, sem substituir por outra categoria.

O pin tem cabeça arredondada, borda marfim, fundo azul e ponta curta. Mede 24×32 px no minimapa e 28×36 px no mapa M, com escala pelo DPI da janela do jogo. A ponta inferior ocupa a coordenada do item; o painel mostra a mesma imagem sem moldura de pin. Itens coletados permanecem ocultos, sendo revelados em cinza com Ctrl. Outros marcadores conservam o visual anterior.

A imagem e a geometria são compartilhadas pelo desenho, recorte no minimapa, exclusão sobre controles e Ctrl+clique. A área transparente não recebe cliques. A renderização mantém os mesmos elementos e PhotoImages entre quadros; muda apenas posição, tamanho/superfície ou estado. O alfa externo é binário para evitar franjas da cor-chave Win32. A composição das imagens e seu carregamento ocorrem uma vez por tamanho/estado, sem rede no ciclo de desenho.

A região nativa de entrada é construída por spans de pixels, unidos e normalizados antes de uma única chamada ExtCreateRegion. A conferência Win32 em janela própria verificou cada pixel da região contra o alfa do pin; também confirmou reutilização dos elementos Tk e imagens. Num cenário isolado com 100 pins, a construção/aplicação da região caiu de cerca de 139 ms para mediana de 5,45 ms; isso não é FPS nem atraso ponta a ponta do jogo. Os 211 testes incluem ponta ancorada, DPI, cantos transparentes, recorte do corpo acima da âncora, estado coletado, hashes/fallback, retenção entre quadros, união de sobreposições e liberação de handles em falhas.

Prévias locais: `build/chest-pins-preview.png` (cinco tipos, dois tamanhos, fundos claros/escuros e estado coletado) e `build/panel-preview.png` (widgets reais). A prévia do painel usa somente a própria janela, sem capturar outras aplicações. A aparência foi conferida nessas prévias; o teste no jogo desta apresentação ainda não foi registrado e não reabre o aceite das regiões anteriores.

A revisão dos pins foi instalada na raiz após confirmar o overlay fechado. Backup: `backups/chest-pins-20261107-014048Z`. SHA-256 do executável instalado conferido contra dist; preferências e progresso conservaram os hashes anteriores. O diagnóstico empacotado em instalação isolada de Snezhnaya confirmou 10.091 pontos, processo auxiliar e cinco imagens pessoais disponíveis. A inspeção do pacote confirmou o código otimizado e somente metadados dos baús, sem redistribuir seus PNGs.

## Ferramentas de preparação do AppSample

`python scripts/inspect_appsample_progress.py <arquivo.json>` arquiva os IDs e audita os vínculos explícitos entre fontes sem modificar o progresso. Com `--catalog <catalogo.json> --catalog-url <url>`, valida o formato comprimido atual e resolve os IDs no próprio namespace AppSample. A ajuda de embed descreve exibição em iframe, não exportação de progresso ou licença geral de redistribuição.

O arquivo Firestore fornecido contém 3.755 IDs únicos. A preparação extrai somente esses IDs, sem nome do documento/conta, cabeçalhos ou credenciais. `python scripts/prepare_appsample_package.py --catalog <catalogo.json> --labels <labels.json> --references` prepara o pacote pessoal e as referências. A tabela exige `code=0`, `compressionVersion=1`, deltas cumulativos de IDs e coordenadas finitas; variantes desconhecidas são rejeitadas. A referência verifica os hashes e não fabrica terreno quando um tile falta.

A URL atual fornecida pelo usuário foi `https://game-data.lemonapi.com/gim/markers_all.v5.compressed.json?ver=9f0c3fe69094909c`. O HTTP direto retornou 403; a abertura normal no navegador forneceu o catálogo público, exportado por blocos e validado: 3.109.019 bytes, SHA-256 `0d57491936253a8c0546f16c13b1bb0f7ac4c1f90754d06fd4c2f83d5e49f5cc`. Nenhum token foi solicitado, extraído ou enviado a ferramentas de terceiros.

## AppSample: fonte alternativa e importação pessoal (07/11/2026)

O painel permite alternar entre Kongying (seleção por nação) e AppSample (seleção por mapa). A troca invalida o alinhamento, esconde os marcadores anteriores e mantém preferências e IDs separados. Kongying permanece disponível; seus registros não são convertidos por aproximação.

O catálogo pessoal AppSample contém 88.957 pontos e 757 categorias da versão `2026-11-06T16:21:36.582Z`, obtida no endereço público fornecido pelo usuário. IDs são decodificados por soma cumulativa dos deltas e mantidos como `appsample:marker:<id>`. A projeção é WebMercator centrada no zoom 14, conforme o adaptador Leaflet e o esquema de tiles observados no código público. Dados, imagens e referências ficam em userData, fora do Git e do executável; esta preparação pessoal não constitui autorização de redistribuição.

A importação local resolveu exatamente 3.666 das 3.755 marcações fornecidas, incluindo 1.267 baús. Os 89 IDs ausentes permanecem no arquivo original normalizado, sem correspondência inventada. Foram adicionados 3.666 registros, preservando os dois registros preexistentes. Backup anterior à aplicação: `backups/appsample-20261107-060859Z`. Não há sincronização contínua com a conta do site. A importação não inventa horários de coleta nem prazos de reposição e registra um histórico para não reaplicar marcações manualmente desfeitas. Ajustes oferece importação de novos arquivos JSON/TXT, com confirmação dos totais e backup.

Disponível visualmente nesta entrega: Teyvat · Superfície, com referência geral no zoom 12 e referência detalhada de Snezhnaya no zoom 13. Demais mapas e camadas têm dados conservados, mas não são habilitados sem referência correspondente. A cobertura da referência detalhada usa a distribuição dos Cryoculi apenas para definir o recorte da imagem; não atribui nações aos outros pontos. Categorias sem tradução conferida conservam sua identificação de origem e ficam separadas das categorias traduzidas.

Validação: 241 testes passaram, incluindo projeção, IDs entre fontes, hash do catálogo, backup imutável, reimportação, preservação de registros e recorte dos coletados. Widgets reais do painel foram verificados em janela isolada, incluindo alternância da apresentação entre fontes. O executável empacotado confirmou 88.957 pontos, processo auxiliar, referências AppSample e cinco artes pessoais de baús. Capturas antigas do mapa M alinharam com erro p95 de ajuste entre 1,35 e 1,44 px; isso não mede precisão independente dos baús. Capturas antigas de minimapas fora da referência detalhada não foram reconhecidas. A nova fonte ainda não recebeu validação no minimapa de Snezhnaya nem sessão prolongada no jogo; a expansão completa continua pendente.

### Correção do minimapa AppSample em Snezhnaya

A troca de fonte expôs uma lacuna nas referências: o mapa M alinhava, mas a captura real do minimapa não encontrava correspondências suficientes. A referência geral e a detalhada anterior, isoladamente, não eram suficientes. Um raster global de maior resolução também descartava detalhes locais pelo limite de features.

A preparação agora acrescenta blocos sobrepostos do zoom 14, pré-amostrados em 1,25×, com geometria WebMercator preservada. O manifesto identifica esses blocos como `surface: minimap`; o carregador valida seus hashes e os mantém separados da referência do mapa M. O reconhecedor prioriza o último bloco que alinhou, volta a procurar nos demais quando necessário e ignora blocos vazios de borda. As rejeições geométricas e a validade temporal continuam as mesmas; nenhuma posição antiga é congelada para encobrir a falha.

Na mesma captura real de Snezhnaya que falhava antes, três reconhecimentos passaram com confiança 1,0 e erro p95 de ajuste de 0,45 px. Processamento: 59 ms na primeira busca e 27 ms nas seguintes, após aproximadamente 18 segundos de inicialização das referências no processo de diagnóstico. Estes números são de registro de uma captura, não atraso completo do overlay nem medição durante corrida. O relatório local fica em `build/appsample-minimap-fix-proof.json`. Os 241 testes da base passaram, e 29 testes do módulo de overlay passaram após a correção final, incluindo dois novos casos de separação por superfície, projeção e hashes. Progresso, catálogo de itens e IDs não foram alterados por esta correção.

A regressão final passou nos 243 testes. O diagnóstico empacotado carregou as referências corrigidas e os 88.957 itens. Instalação concluída com backup `backups/appsample-minimap-20261107-062302Z`; executável conferido contra dist por SHA-256 e hashes das preferências/progresso preservados. A conferência durante movimento no jogo desta revisão ainda não foi registrada.

### Continuidade do minimapa durante caminhada

Uma gravação local de 450 recortes do canto do minimapa (30,4 segundos de Snezhnaya, incluindo aberturas/fechamentos de M) revelou perdas de confirmação do HUD e de confirmação absoluta. A confirmação do símbolo branco do HUD agora aceita sua silhueta, além da comparação original, para não depender do cenário atrás do botão. Ausência do símbolo não é tratada como partida. A localização continua exigindo geometria válida, e o rastreamento externo continua sendo reiniciado ao perder foco ou mudar de superfície.

A busca absoluta extrai descritores uma vez por máscara, compartilha-os entre blocos e tenta o bloco anterior e os próximos antes dos distantes. Os blocos distantes continuam acessíveis após teletransporte. A confirmação passa a ser solicitada com maior frequência quando a âncora do minimapa se aproxima do vencimento. O prazo máximo da âncora continua em 1,5 segundo.

Uma falha curta de fluxo pode ser recuperada por nova comparação contra a última imagem validada, limitada a 250 ms e sujeita aos mesmos testes de fluxo, distribuição espacial e erro geométrico. A posição antiga não é reapresentada sem registrar a imagem atual. Teletransporte, lacuna maior, menu e âncora vencida continuam ocultando o resultado. O log identifica a última resposta absoluta junto das transições de continuidade.

Na reprodução da gravação, usando o mesmo reconhecedor absoluto otimizado nos dois casos para isolar a mudança do pipeline de movimento, houve 313 quadros classificados como partida: 39 sem alinhamento com o pipeline anterior e 31 com o novo. O restante inclui mapa M e transições; essas telas não entram no denominador. O custo p95 da etapa principal foi 24,57 ms antes e 24,21 ms depois. O resultado não mede FPS nem latência ponta a ponta, e não equivale a sessão prolongada do executável instalado. Relatório pessoal: `build/minimap-continuity-comparison.json`. A revisão passou na regressão de 249 testes e depois nos 14 testes de movimento, incluindo um caso adicional com reconhecimento pendente.

Revisão instalada com backup `backups/minimap-continuity-20261107-063346Z`. O executável passou no diagnóstico isolado, teve o módulo de movimento conferido contra o código final e conservou os hashes das preferências e do progresso. Nenhum item foi importado novamente ou remarcado nesta atualização. O teste durante a sessão do usuário com este executável ainda não foi registrado.

## Farm de baús e bússola 2D

O botão “Farmar baús” arma uma sessão local. A primeira posição válida de minimapa é registrada como origem; dessa posição escolhe o baú disponível mais próximo entre os tipos selecionados, no mapa e na camada reconhecidos. O alvo permanece fixo durante o deslocamento, para evitar alternância entre pontos próximos. Depois de confirmar sua coleta pelo fluxo existente, o próximo alvo é escolhido a partir da posição atual. “Próximo” pula o alvo somente nesta sessão, sem alterar seu progresso. Parar e iniciar novamente limpa os pulos. A aproximação nunca confirma uma coleta automaticamente.

Uma pequena bússola 2D é desenhada aproximadamente junto aos pés, na posição padrão de câmera/personagem: centro a 50% da largura e 78% da altura da janela. Ela acompanha a orientação do minimapa e mostra norte. É uma indicação planar; não estima direção da câmera 3D, relevo, caminho transitável, altura do baú ou distância em metros. Não está ancorada ao chão do cenário. O deslocamento/rotação da câmera pode mudar a posição visual dos pés. A bússola não controla o personagem e não recebe cliques.

A sessão respeita seleção de categorias, fonte, mapa, camada, progresso importado e ocultação global. Sem alinhamento fresco, durante M, menus ou perda de foco, a seta fica oculta. Trocar a fonte ou o recorte territorial encerra o farm; trocar mapa/camada reconhecidos também encerra a sessão. O farm não é retomado automaticamente ao abrir o aplicativo. Nenhum ID, coordenada ou regra de reposição foi alterado.

O desenho conserva quatro primitivas entre quadros e usa a superfície de overlay existente; a região de entrada com Ctrl continua pertencendo apenas aos pins. A bússola é ocultada quando sua área coincidir com controles. O painel reserva espaço aos avisos e botões inferiores, mantendo-os acessíveis no tamanho compacto.

Validação: 262 testes passaram, incluindo seleção do mais próximo, alvo fixo, avanço após coleta, pulos sem gravação, coletas importadas, seleção vazia, rotação/norte, mapa/camada incorretos, prazo vencido e troca de fonte. A prévia em Tk verificou retenção dos elementos e exclusão sobre controles. A experiência em jogo desta função ainda não foi aprovada; a prévia não comprova ancoragem aos pés nem orientação relativa à câmera 3D.

Instalação da primeira versão de farm concluída após o usuário encerrar o overlay, com backup `backups/chest-farm-20261107-072009Z`. SHA-256 do executável conferido contra dist e hashes de progresso/preferências preservados. O diagnóstico empacotado passou, e os módulos de farm, sessão, painel e desktop foram conferidos contra o código final. A captura real de Snezhnaya encontrou um alvo não coletado e manteve sua identidade nas atualizações seguintes; isso é teste em imagem, não aprovação da experiência no jogo.

### Identificação do alvo e atalhos do farm

O baú-alvo recebe um contorno dourado quando seu pin está visível no minimapa. O contorno é apenas visual: não amplia a região de clique, não revela itens coletados, não ultrapassa o círculo do minimapa e se oculta ao coincidir com controles. O desenho reutiliza o mesmo elemento entre quadros.

A bússola mostra o tipo em português e três faixas de proximidade: Próximo (até o limiar já usado para coleta próxima), Na vizinhança (até o raio do minimapa) e Mais distante. São indicações baseadas na escala atual do minimapa, sem converter unidades em metros nem inferir diferença de altura. Nenhuma dessas indicações confirma coleta automaticamente.

Atalhos padrão: Ctrl+Alt+F9 inicia/para o farm e Ctrl+Alt+F10 pula o alvo, com o jogo em foco. Ambos são configuráveis em Ajustes. A leitura de preferências antigas conserva os atalhos existentes e escolhe combinações livres para as ações adicionadas; a preferência antiga do painel também é preservada. Atalhos duplicados/ inválidos continuam rejeitados. Ajustes ganhou rolagem para manter acessíveis os seis seletores, o salvamento e os comandos secundários no painel compacto.

Validação: 265 testes passaram, incluindo migração com colisões, persistência dos atalhos, faixas de proximidade, retenção do contorno e exclusão fora do círculo/sobre controles. As prévias reais de Tk conferiram os seis seletores, tipo/proximidade e contorno dourado. Esta etapa não altera o rastreamento nem amplia os mapas habilitados; continuidade adicional e referências de outros mapas/cavernas permanecem etapas seguintes. A operação dos novos atalhos durante a partida ainda aguarda conferência do usuário.

Atualização instalada após encerramento do overlay, com backup `backups/farm-target-shortcuts-20261107-154701Z`. O diagnóstico empacotado passou, os módulos alterados foram comparados ao código final, o executável instalado corresponde ao dist por SHA-256 e os hashes de preferências/progresso foram preservados. Os novos atalhos são acrescentados em memória ao carregar as preferências antigas e persistem pelo fluxo normal de salvamento.

## Reconstrução visual do painel compacto

A apresentação principal foi reorganizada, mantendo 360×540 px, persistência da posição e modos independente/fixado. Cabeçalho curto, emblemas de nações, camada ativa e busca ficam no topo. A lista virtual ocupa a área central e mostra caixa de seleção explícita, arte do item e contador em colunas. O farm ocupa uma faixa inferior própria; seu aviso aparece somente quando ativo. Progresso e estado resumido ficam separados dos comandos Ocultar, Desfazer e Jogar. Avisos vazios deixam de reservar uma linha.

A fonte de dados e o controle Fixar/Destacar foram movidos para Ajustes, junto dos seis atalhos, importação, diagnóstico completo e encerramento. O estado principal mostra a mensagem essencial; o diagnóstico completo permanece disponível em Ajustes. Busca tem indicação no campo, os controles usam a mesma tipografia/paleta e foram retiradas as bordas claras herdadas do tema Tk. A camada escolhida aparece junto ao nome da nação; no AppSample o mapa/camada permanece como linha própria. O painel de Ajustes conserva a rolagem.

Validação: a regressão de 265 testes passou. Prévias reais de Tk foram conferidas com Kongying, AppSample e Ajustes, incluindo seleção de nação por teclado, troca da apresentação da fonte, camadas, recolhimento e janela independente. A prévia foi atualizada para conferir a legenda composta de nação/camada. Não foram alterados catálogo, coordenadas, regras de coleta, temporizadores nem rastreamento por esta revisão visual. Arquivos locais: `build/panel-preview.png`, `build/appsample-panel-preview.png`, `build/farm-settings-preview.png`.

Revisão visual instalada com backup `backups/panel-visual-rebuild-20261107-155624Z`. Executável conferido por SHA-256 contra dist e hashes de preferências/progresso preservados. O diagnóstico empacotado de AppSample passou; um smoke test do painel nativo isolado verificou abertura, superfícies, atualização, recolhimento/restauração e encerramento, sem captura de jogo nem registro de atalhos. As referências ausentes nessa pasta isolada foram tratadas como indisponíveis. A aprovação visual do usuário desta nova composição ainda está pendente.

## Destaques em grade com oculi oficiais

Os oculi disponíveis na seleção aparecem em caixas de quatro colunas, nesta ordem: Anemoculi, Geoculi, Electroculi, Dendroculi; Hydroculi, Pyroculi, Lunoculi, Cryoculi. Cada caixa mostra arte oficial, nome, contador e seleção. Catálogos com menos tipos mostram apenas os disponíveis, sem inventar cobertura. A busca, seleção de grupo, Limpar e contadores conservam os mesmos IDs e comportamento. Outros destaques não classificados entre esses oito recursos conservam a linha convencional.

As oito imagens foram obtidas da árvore pública do mapa HoYoLAB, identificadas pelo nome exato e conferidas visualmente. Origem, URLs e SHA-256 ficam em `data/assets/oculi/SOURCE.json`; PNGs ficam somente em `userData/assets/oculi`. A inspeção do executável confirmou apenas SOURCE e NOTICE nesse diretório de assets. `scripts/prepare_oculus_assets.py --check` verifica a instalação sem rede. Arte ausente ou alterada conserva o símbolo anterior. As imagens redimensionadas são mantidas em memória e não há downloads no desenho. Esta mudança aplica as imagens ao seletor, preservando os ícones de oculi sobre os mapas.

Os 265 testes da base passaram; dois testes adicionais conferiram a identidade dos recursos e a rejeição de arte ausente/alterada. Uma janela Tk isolada verificou os oito cliques, incluindo metade inferior das caixas, navegação por teclado, pesquisa, células vazias e reutilização das oito imagens. O diagnóstico empacotado passou. Instalação com backup `backups/official-oculi-grid-20261107-164504Z`, SHA-256 do executável conferido contra dist e hashes de preferências/progresso preservados.

## Controle de visibilidade em capturas

O olho no cabeçalho alterna a preferência de compartilhamento: aberto permite captura do painel, pins, bússola e cartões; riscado pede ao Windows sua exclusão, mantendo o comportamento anterior por padrão. O mesmo comando aparece em Ajustes como “Captura: visível/oculta”. A preferência `capture_visible` é salva e reaplicada ao iniciar e criar novas janelas. Ocultar os ícones localmente continua sendo uma ação independente.

A implementação alterna SetWindowDisplayAffinity entre WDA_NONE (0) e WDA_EXCLUDEFROMCAPTURE (17) nas janelas deste processo. Janelas encerradas ou de outros processos são descartadas do registro; uma falha interrompe a alteração, restaura as janelas já modificadas e apresenta o erro. Não altera foco, coleta ou geometria de entrada. A captura apenas da janela do Genshin pode deixar de fora as janelas externas do overlay; a interface orienta compartilhar a tela inteira para transmitir os pins. A integração com cada aplicativo de transmissão não foi testada.

Validação: 270 testes passaram. Uma janela própria do Windows confirmou a sequência de afinidade 17 → 0 → 17, inclusive numa janela criada depois de habilitar a captura. A prévia Tk verificou os dois estados do olho e o comando de Ajustes. O rastreador continua com os mesmos limites de validade; a continuidade durante transmissão com os ícones visíveis ainda precisa de observação em jogo.

Versão instalada após o usuário encerrar o overlay, com backup `backups/capture-visibility-eye-20261107-165031Z`. Diagnóstico empacotado aprovado, executável conferido por SHA-256 contra dist e hashes de preferências/progresso preservados. A validação em aplicativo de compartilhamento real ainda não foi registrada.

### Correção da regressão de captura e redetecção do minimapa

O modo de compartilhamento expôs os próprios desenhos ao caminho anterior de captura da área de trabalho. Um teste local, com pequena janela própria em camada e sem foco sobre o Genshin, confirmou: a captura da tela incluiu os 900 pixels vermelhos da janela de teste; a captura do DC cliente do jogo incluiu zero. PrintWindow foi avaliado, retornou falha/imagem preta e não foi adotado.

Com o olho aberto, o reconhecimento agora captura o DC cliente do jogo em coordenadas locais, sem os desenhos das janelas separadas do overlay. Com a exclusão de captura ativa, conserva o caminho anterior da área de trabalho. Os DCs são liberados com o mesmo proprietário usado ao adquirir. A troca do modo reinicia o acompanhamento entre quadros, para não encadear imagens de origens diferentes. Não esconde nem alterna temporariamente os desenhos durante a transmissão.

A geometria de tela do minimapa também passou a ser reutilizada quando a seta ciano nativa do jogador confirma, na imagem atual, o centro esperado. Sem essa evidência, retorna à detecção completa do círculo. O cache é apenas da geometria do HUD: não conserva a posição no mundo nem prolonga sua validade, e o alinhamento geométrico ainda é exigido a cada registro absoluto.

Na captura real de Snezhnaya, a localização passou com confiança 1,0 e erro p95 de ajuste de 0,33 px. A primeira busca levou 630 ms e as três seguintes entre 18 e 21 ms. Isso mede processamento de uma imagem, não atraso ponta a ponta ou estabilidade durante transmissão prolongada. Os 272 testes passaram, incluindo origem/limpeza do DC cliente e rejeição de geometria sem evidência atual do jogador. A verificação do compartilhamento no aplicativo usado pelo usuário ainda está pendente.

Correção instalada com backup `backups/clean-sharing-minimap-20261107-170553Z`, diagnóstico empacotado aprovado, SHA-256 do executável conferido contra dist e hashes de progresso/preferências preservados. Ainda falta a conferência do usuário com minimapa, farm e compartilhamento simultâneos.

## Bússola relativa à orientação do personagem

A seta de farm passou a indicar o alvo em relação à direção atual do personagem, lida da seta ciano nativa do minimapa. Apontar para o alvo faz a bússola apontar para cima; mudar a orientação faz a direção relativa girar, mantendo o mesmo baú selecionado. A indicação de norte também gira nessa referência. O cálculo usa o vetor do alvo projetado no minimapa e desconta o ângulo da seta nativa; portanto funciona com minimapa rotacionado sem confundir norte fixo com frente do personagem.

A leitura isola o componente ciano central, exige forma/área compatíveis e usa o recorte traseiro do símbolo para distinguir frente e trás. Glifos simétricos/ambíguos são rejeitados. A orientação é calculada novamente em cada quadro atual, incluindo os quadros acompanhados por fluxo, sem transportar um ângulo antigo junto do resultado absoluto atrasado. Sem orientação confiável, a guia aguarda nova leitura, conserva o alvo e não altera os pins nem o progresso.

Esta orientação é do personagem indicado no minimapa. Ainda não estima yaw/pitch da câmera, não é uma seta ancorada ao chão e não acrescenta direção vertical/altura. Girar apenas a câmera e mudar a orientação do personagem são movimentos distintos.

Validação: 287 testes passaram, incluindo oito direções sintéticas do símbolo, quatro direções relativas, cancelamento da rotação do mapa e preservação do alvo com orientação desconhecida. Na gravação anterior de Snezhnaya, a leitura encontrou orientação em 308 dos 313 quadros classificados como partida. Esse número mede disponibilidade da leitura, não erro angular independente. Duas capturas reais foram conferidas visualmente quanto à direção do símbolo; o aceite durante partida da bússola relativa ainda está pendente.

Versão relativa instalada com backup `backups/player-relative-compass-20261107-171233Z`, diagnóstico empacotado aprovado e executável conferido por SHA-256 contra dist. Preferências e progresso preservaram os hashes anteriores. Ainda falta conferir a experiência desta orientação durante a partida.

### Estabilização da bússola relativa

A orientação agora passa por um acompanhamento temporal separado da localização. Pequenas oscilações são suavizadas pelo arco angular mais curto, inclusive em 359°/0°. Mudanças maiores que 70° exigem uma segunda leitura compatível em até 180 ms, evitando que uma leitura isolada inverta a seta. Mudanças reais confirmadas são aceitas prontamente. Ambiguidade breve pode conservar a orientação por no máximo 180 ms somente quando o componente central do jogador continua visível e a localização atual permanece válida. Ausência do símbolo, perda de localização, menu, foco ou lacuna de quadros reinicia esse acompanhamento; não amplia o prazo do alinhamento no mundo.

Ao chegar a até seis pixels de minimapa do alvo, a indicação muda para um losango e “No local”, evitando uma seta girando em cima do ponto. Volta à direção ao afastar-se além de nove pixels; a faixa evita alternâncias junto ao limite. São pixels da escala atual do minimapa, sem alegação de metros, altura ou coleta confirmada. O progresso só muda pelo comando de coleta existente. O log passou a registrar transições do estado do farm e seu alvo, distinguindo espera por localização de espera por orientação.

A gravação pessoal contém 450 recortes em 30,45 segundos. Na comparação pareada, entre os 422 quadros reconhecidos como partida, houve cinco leituras brutas sem direção e uma sem direção após o filtro; os passos maiores que 70° passaram de 14 para sete. Esses passos incluem giros legítimos, portanto a redução não é uma medição independente de erro angular. Os 291 testes passaram, incluindo inversão isolada, giro verdadeiro, passagem por norte, limite de ambiguidade, reinício do filtro e chegada com histerese sem coleta automática. O teste na sessão do usuário com esta revisão ainda está pendente.

Revisão instalada com backup `backups/compass-stability-20261107-172410Z`. Diagnóstico empacotado aprovado, executável conferido contra dist por SHA-256 e hashes de progresso/preferências preservados. Ainda falta a conferência em partida da estabilidade percebida pelo usuário.

## Ícones de categorias restantes do AppSample

O importador `scripts/prepare_appsample_icons.py` preparou 744 imagens correspondentes aos `source_type` do catálogo pessoal, preservando as 13 artes oficiais já instaladas para baús e oculi. Isso cobre as 757 categorias do snapshot adotado; não afirma cobertura de versões posteriores do site. As 744 respostas foram validadas como imagens de 64×64 px. São 737 hashes SHA-256 distintos; alguns tipos da própria fonte compartilham a mesma imagem, sem unir seus IDs ou contadores.

URLs observadas no seletor são preferidas; tipos ausentes dos rótulos arquivados usam o esquema público confirmado `/gim/markers/o<ID>.png?v=3`, com o ID exato do catálogo e validação da resposta. Não há associação por proximidade ou semelhança de nomes. `userData/assets/appsample/SOURCE.json` conserva URL, tipo, hash, nome da fonte, data e limite de uso pessoal; as imagens e o manifesto pessoal ficam fora do Git e do executável. Não são apresentadas como arte oficial da HoYoverse sem confirmação; a origem desta importação é o AppSample.

A lista e o cartão de coleta carregam a imagem correspondente à categoria AppSample e conservam a arte anterior quando faltar um arquivo ou seu hash divergir. As imagens preparadas são mantidas em cache, sem downloads ou redimensionamento repetido ao redesenhar a mesma imagem. O cartão mantém o estado apagado de itens coletados. As artes oficiais existentes conservam prioridade. Outras fontes não recebem associação por números iguais. Os pins desenhados sobre o jogo e o rastreamento permanecem com o comportamento anterior; esta etapa trata da identificação visual no painel/cartão.

Categorias cujo nome ainda não foi traduzido continuam na seção correspondente, mesmo com uma imagem disponível. A importação não altera nomes, seleção, IDs, contadores, posições nem coletas. `--check` verificou todos os 744 hashes sem rede; não houve imagens indisponíveis nesta importação. Os 295 testes passaram, incluindo cache, categoria exata, estado coletado, arquivo alterado e rejeição de caminhos fora da pasta pessoal. A prévia real do painel e uma amostra de imagens da fonte foram conferidas visualmente.

Instalação concluída com backup `backups/appsample-category-icons-20261108-030640Z`, diagnóstico empacotado aprovado e SHA-256 conferido contra dist. Preferências e progresso conservaram os hashes anteriores. A inspeção do executável confirmou o novo carregador e a exclusão da coleção pessoal AppSample do pacote. Das 744 URLs, 652 foram observadas no seletor arquivado e 92 foram resolvidas pelo esquema exato de tipos, com todas as respostas validadas.

## Correspondência entre seletor e marcadores dos mapas

Os marcadores do minimapa e do mapa M agora usam a mesma arte da categoria selecionada no painel. Baús conservam os pins anteriores, ancorados pela ponta. Oculi usam a arte oficial já conferida; demais categorias AppSample usam a imagem pessoal exata importada por tipo. Ícones não relacionados a baús são centralizados na coordenada do ponto, em 24 px no minimapa e 28 px em M, com ajuste de DPI. Não foi adicionada uma segunda moldura ao redor de imagens da fonte que já contêm um pin.

A geometria de entrada e o recorte são derivados do alfa binário da própria imagem desenhada, inclusive segmentos separados e vazios internos. Áreas transparentes deixam os cliques passarem. O mesmo formato controla Ctrl+clique, recorte circular e exclusão sobre controles. Coletados continuam ocultos normalmente e aparecem dessaturados ao revelar com Ctrl, conservando a mesma área visível. Sem arte válida, permanece o símbolo anterior. Não há downloads no desenho; imagem e geometria são preparadas e mantidas em cache.

Validação: 297 testes passaram. Os casos novos verificam em cada pixel a correspondência do clique ao alfa, preservação de transparência no estado coletado, cache e fallback nos dois tamanhos. O teste específico de sobreposição de símbolos legados foi isolado das artes pessoais para continuar verificando seu contrato original. A prévia local `build/selector-map-icons-preview.png` foi conferida com baú, oculi, seelie, desafio, santuário e outros tipos da fonte. A mudança preserva coordenadas, IDs, filtros e progresso; a conferência visual destes novos marcadores na partida ainda não foi registrada.

Atualização instalada após o usuário encerrar o overlay, com backup `backups/matching-selector-map-icons-20261108-040411Z`. SHA-256 conferido contra dist e hashes de preferências/progresso preservados. A validação visual dos novos marcadores em partida permanece pendente.

## Identidade Hexen Map / HexenMap

O produto passou a se chamar **Hexen Map**. Executável e identificadores técnicos usam **HexenMap**: `HexenMap.exe`, `HexenMap.spec`, pacote/comando `hexenmap` e lançador `Iniciar_HexenMap.bat`. Cabeçalho, título de janela, mensagens, metadados do Windows, ferramentas de build e a implementação legada de testes foram atualizados. O lançador genérico `Iniciar_Overlay.bat` encaminha para o novo nome.

A instalação continua usando a mesma pasta `userData` ao lado do executável; não muda IDs de marcadores, nomes de catálogos, coordenadas, coletas ou referências. Registros históricos de entregas e caminhos antigos permanecem como evidência das versões anteriores. Duas constantes com a identidade antiga ficam restritas à compatibilidade de instância: a versão nova reconhece a janela anterior e mantém também seu mutex, impedindo execução duplicada ao abrir um binário antigo.

Os 299 testes passaram, incluindo o caso de uma versão anterior já aberta e a liberação dos dois mutexes. A prévia real do painel confirmou o cabeçalho Hexen Map. O build gera propriedades de arquivo com ProductName/FileDescription Hexen Map e OriginalFilename HexenMap.exe. A troca do executável será registrada com backup e preservação dos hashes de progresso e preferências.

Migração instalada com backup `backups/hexenmap-brand-20261108-041934Z`. O binário novo é `HexenMap.exe`; os executáveis antigos da raiz e de dist foram preservados no backup e retirados desses locais. SHA-256 conferido contra o novo dist e hashes de progresso/preferências preservados. O diagnóstico empacotado passou; as propriedades PE confirmaram CompanyName, FileDescription, ProductName e OriginalFilename. Um smoke test nativo confirmou o título Hexen Map, rejeição de segunda instância e liberação dos mutexes ao encerrar, com dados isolados.
