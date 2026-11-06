# Inventário e verificação regional — 2026-11-06

Este documento registra evidências e lacunas da implementação; o estado principal
continua em [REBUILD.md](REBUILD.md). Importação não significa aprovação no jogo.

## Fonte e cobertura dos dados

Fonte: Kongying Tavern, condições CC-BY-NC-SA-4.0 conferidas no disclaimer publicado.
Créditos e restrições em `data/community/kongying/NOTICE.md`; arte original fica
somente em referências pessoais de `userData`, fora do executável e do Git.
Os pontos foram lidos por rotas públicas anônimas, sem conta, cookies ou comandos
de escrita. Tokens transitórios não são gravados. A versão da fonte é a fotografia
da exportação, não uma garantia independente de conteúdo de uma versão do jogo.

| Região da fonte | Marcadores únicos importados |
|---|---:|
| Mondstadt | 15.356 |
| Liyue | 20.692 |
| Inazuma | 13.229 |
| Sumeru | 21.446 |
| Fontaine | 18.940 |
| Natlan | 18.674 |
| Nod-Krai | 7.772 |
| Snezhnaya | 10.091 |
| Total | 126.200 |

O inventário contém 14 combinações região/mapa e 478 nós territoriais, dos quais
322 são localidades explícitas da hierarquia de cavernas da fonte. São tratados
separadamente Teyvat, Despenhadeiro subterrâneo, Enkanomiya, Mar das Eras Passadas,
Templo do Céu, Montanha Sagrada Antiga e Lua Gélida, conforme os códigos da fonte.
Mapas temporários de eventos são excluídos da seleção de raízes permanentes.

29 pontos com associação a mais de uma região foram separados em
`unclassified-points.json`. A auditoria confirmou que algumas associações são
contagem de conquistas (um baú de Natlan também conta para Liyue), sem comprovar
a posição territorial. Esses pontos não aparecem em nenhum pacote utilizável
até terem classificação física conferida. Associações ambíguas dentro de uma
região ficam em Área não confirmada e não entram nos recortes específicos.

As áreas gerais vêm da associação explícita das consultas da fonte. Localidades
e andares vêm de `extra.underground.region_levels` e da árvore correspondente da
configuração publicada. A associação não usa proximidade de nomes. Não existe
classificação fina conferida para toda a superfície, como Reino dos Lobos e
Origem do Vento. Nomes sem tradução conferida conservam o nome da fonte.
Andares ausentes ficam como `Subterrâneo · camada não confirmada`.

O catálogo anterior de Mondstadt permanece como opção de compatibilidade, com
suas referências e IDs originais. Ele não recebe coordenadas da nova fonte por
uma transformação aproximada. Os IDs da nova importação só reutilizam um ID
antigo quando `markerStamp` coincide com o identificador `importIds.yuanshen`.
Registros antigos sem associação continuam no progresso e no backup.

## Referências e reconhecimento

A projeção foi conferida em `src/api/map.js` do frontend fixado:
`pixel = 2**zoom * (latitude + center[0], longitude + center[1])`.
Não se troca x por y nem se reaproveita o CRS do catálogo antigo.
Tiles usam `tiles_{code}/{zoom+13}/{x}_{y}.{extension}`. Centros e códigos são
preservados em `source-map-config.json`, sem imagens.

`scripts/prepare_regional_reference.py` prepara candidatos pessoais. Um tile
ausente aborta a preparação; não há terreno de demonstração como substituto.
Cada manifesto identifica região, mapa, camada, CRS, hashes e permissão.
Somente referências da região/recorte atual entram no reconhecedor. O modo
Todos os mapas reconhece também mapas separados e camadas da mesma região, sem
alterar o território escolhido. Um índice visual identifica candidatos e refina
até três deles; o cache mantém no máximo três reconhecedores completos. A
camada automática rejeita duas correspondências simultâneas. Resultados de uma seleção anterior
são descartados por geração, inclusive após um teletransporte/troca de região.

Teste em duas capturas locais previamente obtidas em Mondstadt, usando a nova
referência de tiles 18..23 / 10..15, zoom nativo 0:

| Captura | Resultado | Erro p95 do ajuste | Reconhecimento isolado |
|---|---|---:|---:|
| Mapa M | reconhecido | 0,54 px | 319 ms |
| Minimap | reconhecido | 0,69 px | 74 ms |

São testes em imagens; esses números não medem erro dos marcadores nem atraso
ponta a ponta no jogo. Não aprovam mapas ou localidades fora das capturas.
Houve captura real e teste integrado curtos em Mondstadt (minimapa e M) e no
Porto de Liyue (minimapa e M). No M de Mondstadt, cinco capturas tiveram ajuste p95
de aproximadamente 0,41 px; no minimapa do Porto, cinco capturas tiveram p95
próximo de 0,38 px, e no M de Liyue o p95 ficou próximo de 0,71 px.
O usuário confirmou os ícones no executável instalado e o funcionamento do
teste curto de caminhada, fechamento/reabertura de M, pan/zoom, Ctrl,
marcar/desmarcar e retorno de foco em Liyue. São locais de teste, não aprovação
de todos os pontos ou de uma sessão de 30 minutos.
Nenhum mapa regional novo tem sessão completa de aceite registrada nesta expansão.
O inventário mantém `reference_status=not_validated` e `coverage_complete=false`.

Foram preparados localmente 14 candidatos de mapa/camada principal e 314
referências de cavernas com limites explícitos da fonte; todos os 328 manifestos
passaram pela leitura e conferência de hashes. Duas camadas explícitas ainda
não têm chunks correspondentes. Pontos com andar não confirmado também não
ganham referência por aproximação. Resolução maior está sendo preparada quando
necessária; mapas grandes e falhas de download não autorizam cobertura fictícia.
`python scripts/coverage_report.py --output build/regional-audit/local-coverage.json`
registra disponibilidade local e camadas faltantes sem aprovar mapas no jogo.

## Reposição

O campo `refreshTime` positivo usa milissegundos segundo o modelo `marker.rs`
do backend fixado. Isso confirma a unidade do dado, não o prazo real de
reaparecimento no jogo. A importação conserva o valor original e mantém candidatos
não qualificados como regra desconhecida, sem criar `ready_at`.

| Valor positivo observado | Valor temporal da fonte, sem aprovação automática |
|---:|---:|
| 43.200.000 ms | 12 h |
| 64.800.000 ms | 18 h |
| 86.400.000 ms | 24 h |
| 165.600.000 ms | 46 h |
| 259.200.000 ms | 72 h |

As regras automáticas atualmente associadas são as investigações de artefatos
com 12 h ou 24 h explicitados por ponto, corroboradas pelo [guia KQM](https://keqingmains.com/misc/artifacts/).
O valor de 18 h não recebe automaticamente uma dessas regras. Pesca fica
condicional, por não comprovar esgotamento e estoque de dia/noite.

Para especialidades, os 46 h observados na fonte divergem dos 48 h do
[guia de coleta](https://www.icy-veins.com/genshin-impact/farming-guides). Esses
casos continuam sem prazo. Outros recursos sem política específica corroborada
também exibem “Reposição não confirmada”. Não é aplicada uma regra universal
por planta ou minério. Campos negativos
observados (`-1`, `-3`, `-4`, `-5`, `-8`, `-112`) não foram traduzidos em horários
semânticos: recursos nessas condições mostram “Reposição não confirmada”.
O motor suporta duração, reset de servidor, condições especiais, desconhecidos e
permanentes. Nenhum código de reset negativo está ativado como regra verificada.
Reset América usa uma fronteira UTC explícita e não o fuso do Windows; o teste
do motor cobre antes, exatamente no reset e depois. Regras reais de reset ainda
exigem fonte específica antes de sua associação a pontos.

Coleta/prazo são persistidos em UTC. O vencimento funciona após reiniciar ou
ficar offline, sem apagar o histórico. A disponibilidade é estimada. Desmarcar
cancela a indisponibilidade e desfazer restaura o registro completo, com prazo
original. Permanentes não expiram. Contadores separam progresso permanente e
recursos indisponíveis, somando cada marcador físico uma vez.

## Aceite ainda pendente

- Conferir limites de áreas pequenas da superfície ou obter classificação oficial
  da fonte; não inventar polígonos por proximidade de rótulos.
- Completar e validar referências de todas as camadas, incluindo cavernas.
- Validar pontos independentes por mapa, movimento, rotação, pan/zoom,
  teletransporte, foco, Ctrl e troca de camada no jogo.
- Medir atraso ponta a ponta, erro visual dos marcadores e sessões reais de
  30 minutos por cobertura habilitada, além do custo do reconhecedor.
- Qualificar os códigos condicionais/reset e traduzir as categorias restantes.

A suíte automatizada e a presença de dados não encerram esses itens.

A preservação dos IDs que já existiam no progresso foi conferida após o teste
real de coleta/desmarcação. O backup anterior à migração v2 foi criado.

A árvore de plugins da fonte também repete cavernas em menus de outras áreas.
A auditoria encontrou 267 vínculos afetados; cinco grupos tiveram sua filiação
corrigida por associação explícita e unânime dos pontos, ou foram mantidos em
raiz compartilhada quando não havia filiação única. `territorial_audit` preserva
a origem e a decisão. A regressão compara cada área aos vínculos explícitos
dos seus pontos, evitando inclusão por uma árvore de menu reutilizada.
