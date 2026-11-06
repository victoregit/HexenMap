# Overlay de exploração — referência única

Atualizado em 6 de novembro de 2026. **Versão integrada para revisão; expansão completa ainda não aprovada.**

## Experiência atual

O executável procura o Genshin automaticamente e desenha ícones sobre o minimapa e o mapa M nativos. O painel permite selecionar região, caminho territorial pesquisável, mapa/camada e categorias. A seleção territorial permanece fixa durante viagens. Categorias novas começam desmarcadas; seleção vazia não produz ícones. Preferências são restauradas por região.

O modo **Todos os mapas · camada automática** reconhece referências dos mapas e andares da região escolhida. Há seleção manual de mapa/camada. Áreas maiores incluem descendentes sem duplicar marcadores. O mesmo recorte vale para desenho, revelação com Ctrl, cartão, coleta, desfazer e contadores. Nomes sem tradução conferida conservam o nome da fonte. A classificação fina de toda a superfície ainda não está disponível; não são inventados limites por proximidade de nomes.

Os filtros incluem baús, oculi, desafios, seelies, puzzles, santuários, recursos e outros grupos da fonte. Os cinco tipos de baú têm desenhos vetoriais originais com materiais e ornamentos distintos. Os demais grupos têm símbolos próprios. A entrada normal não usa mapa fictício, simulação, posição manual nem dados demonstrativos. A implementação anterior permanece em `src/legacy_app.py`, fora do executável.

**Ctrl + clique** abre um cartão com uma única ação reversível: marcar como pego ou desmarcar. Itens coletados ficam ocultos normalmente e em cinza enquanto Ctrl estiver pressionado. A área clicável é invisível, sem quadrado de destaque. Fora dos ícones, os cliques continuam chegando ao jogo. Com o cartão aberto, os desenhos no mapa são ocultados para não conservar coordenadas antigas; mudar filtros fecha o cartão sem tirar o foco do painel. Clicar fora do cartão, concluir a ação ou pressionar Esc fecha a interação e permite continuar jogando. O painel de configurações não é ativado para confirmar coleta.

Atalhos padrão: **Ctrl+Alt+F12** mostra/oculta; **F9** coleta o candidato próximo sem ambiguidade; **F10** desfaz a última alteração do recorte nesta sessão. São configuráveis. O atalho de visibilidade continua disponível quando o alinhamento falha. Candidatos próximos usam o minimapa reconhecido; vários candidatos exigem seleção explícita no painel, válida por 30 segundos. Proximidade sozinha nunca confirma coleta.

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

Os contadores usam o recorte territorial, independentemente das categorias visíveis, e deduplicam marcadores físicos. Progresso permanente e indisponibilidade de recursos ficam separados.

Os arquivos ficam ao lado do executável em `userData/progress.json` e `settings.json`. A gravação é atômica; falhas restauram o registro anterior em memória. A migração v1→v2 cria `progress.json.pre-v2.bak`, que não é sobrescrito pelas gravações seguintes. `.bak` continua como recuperação da gravação anterior. Executável, progresso e preferências anteriores também foram preservados em `backups/regional-expansion-*`. Após o teste real de coleta/desmarcação, todos os IDs anteriores continuavam preservados.

## Reconhecimento e integração

`src/live` separa catálogo territorial, reposição, referências, captura Windows, reconhecimento, acompanhamento, sessão e desenho. O aplicativo usa captura externa; não lê memória do jogo nem envia comandos ao personagem.

O índice visual contém apenas referências do recorte/região selecionados. A busca inicial aponta candidatos e o refinamento mantém no máximo três reconhecedores completos em cache. Instalar outras regiões não coloca todas as referências no ciclo de cada captura. A construção das referências ocorre fora da thread Tk e resultados de seleções antigas são descartados por geração.

O ajuste visual usa SIFT e RANSAC com consenso, distribuição espacial e erro residual controlados. O minimapa exige evidência visual da interface e da seta; o círculo útil é conservador diante da oclusão do HUD. Amostragem adicional do raster mantém a transformação geográfica exata e os mesmos critérios geométricos.

Fluxo óptico LK acompanha movimento entre registros absolutos, com verificação de ida/volta. Resultados absolutos são atualizados para o quadro atual antes de desenhar. Uma âncora não é prolongada por mais de 1,5 s. Capturas vencidas, troca de janela/região, menus, perda de foco ou alinhamento incerto ocultam os ícones. O desenho exige observação válida com idade de até 650 ms. Mapas e andares diferentes não compartilham a projeção dos seus marcadores.

A superfície visual permanece click-through. Uma superfície de entrada separada usa alfa e regiões Win32 apenas nos ícones enquanto Ctrl estiver pressionado. O leitor de Ctrl observa somente suas transições, sem bloquear ou gravar outras teclas. Atalhos entram por fila; somente Tk altera widgets. O cartão não usa grab global e só solicita retorno de foco se ele ainda pertencer ao jogo ou ao overlay.

## Evidências atuais e limites

**164 testes automatizados aprovados**, cobrindo regressões, filtros descendentes, seleção vazia, deduplicação, mapa/camada, dados e hashes, aliases explícitos, UTC, vencimento exato, reinício, mudança de fuso, desconhecidos, permanentes, desfazer com prazo original, migração e rollback.

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
- classificação fina de toda a superfície e traduções ainda ausentes;
- referências indisponíveis e tratamento de mapas grandes;
- qualificação das demais políticas de reposição, códigos de reset e exceções;
- disponibilidade de arte com direitos de redistribuição para instalação pública limpa.

O inventário mantém `coverage_complete=false` e mapas como não aprovados. A expansão está autorizada, mas **não está declarada concluída**.

## Diagnóstico e desenvolvimento

`userData/live-session-v2.csv` registra superfície, região/mapa/camada reconhecidos, geração, latência de processamento, confiança e erro de ajuste. Não contém screenshots. `overlay.log` registra diagnóstico e interação. O custo de apresentação e o impacto no FPS ainda exigem medição; tempo sem foco não conta como exploração. Capturas de pesquisa ficam em `build`, fora do pacote.

```powershell
python src/app.py
python src/app.py --diagnose
python -m pytest -q
python scripts/build_exe.py
python scripts/live_report.py
python scripts/coverage_report.py --output build/regional-audit/local-coverage.json
```

`--diagnose` usa a seleção salva, não abre UI e retorna 2 se faltarem dados/referências. O build não encerra processos do usuário para substituir um executável bloqueado. `scripts/import_kongying.py` importa somente por rotas de leitura, sem conta ou cookies do usuário; `--offline` reconstrói a partir da exportação auditada. Tokens transitórios não são persistidos. Os preparadores de referências mantêm imagens pessoais em `userData`, conferem formato/projeção e não fabricam terreno para downloads ausentes.

O histórico anterior fica em `docs/archive/pre-rebuild`.
