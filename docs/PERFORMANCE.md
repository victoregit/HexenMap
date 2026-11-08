# Desempenho — modos Leve e Global

Atualizado em 8 de novembro de 2026. Sessão real de 30 minutos ainda pendente. As medições anteriores abaixo usavam o atlas parcial e não aprovam o atlas ampliado.

## Mudança de arquitetura

A captura do Gerenciador de Tarefas mostrou cerca de 1,4 GB no aplicativo. A reprodução isolada encontrou 19 reconhecedores detalhados, 561.016 pontos SIFT e aproximadamente 274 MiB em descritores, além de imagens coloridas, índices FLANN e áreas temporárias nativas.

A aplicação agora lê metadados (`Raster`/`Block`/`PackSpec`) sem descomprimir o terreno inteiro. Um índice compacto encaminha a busca para blocos locais. O modo Leve retém até dois índices detalhados, com orçamento estimado conservador de 256 MiB; imagens de terreno não permanecem residentes depois da extração. Índices persistem em `userData/cache/references`, separados dos originais, com chaves dependentes do hash, recorte, transformação, versão de esquema/OpenCV e parâmetros SIFT.

O tamanho de trabalho é **1.536 px**, abaixo do teto planejado de 2.048 px, com sobreposição de 128 px. A alteração foi motivada pelo pico do espaço de trabalho SIFT: um bloco de 2.048 px chegou a 1.009 MiB no teste frio, enquanto o de 1.536 px ficou em 575 MiB no teste equivalente isolado. O OpenCV usa dois threads. As coordenadas e os critérios de rejeição geométrica foram preservados; não houve redução cega da resolução das referências.

Global prepara os blocos do mapa/camadas selecionados. Com mapa automático, aguarda a identificação e prepara apenas aquele mapa. A opção traz aviso de maior consumo, é persistida e pode ser trocada sem reiniciar. Cargas substituídas são canceladas; o próximo carregamento pesado aguarda o descarte real da instância anterior. O processo auxiliar de catálogo termina após cinco segundos ocioso ou antes de uma preparação de referências que exigiria sobreposição de memória. Falta de memória no Global provoca retorno ao Leve.

## Outras reduções

- Captura GDI com DC/bitmap/buffer reutilizáveis e no máximo dois slots. Durante gameplay lê a faixa superior necessária ao HUD/minimapa; ao reconhecer M visualmente passa à captura completa. O modo visível em transmissão continua capturando o DC do jogo, evitando realimentação dos próprios pins.
- Filas continuam com o quadro mais recente. O rastreamento local mantém o movimento, com reconhecimento absoluto para confirmação e recuperação.
- Templates de interface são preparados uma vez por tamanho; pins só movem quando sua posição desenhada muda. Dimensões/janelas não são reconfiguradas sem necessidade.
- Busca de itens usa mínimo vetorizado, sem ordenar todos os candidatos. A máscara de disponibilidade acompanha coleta, desfazer, filtros e o instante UTC de reposição.
- Apenas um pacote de catálogo/contadores permanece em cache. Imagens PIL possuem limites por bytes, e o cache Tk conserva imagens em uso por widgets. GIF anima apenas enquanto visível.
- Captura pausa sem seleção, com overlay oculto ou fora de foco. Ctrl continua sendo sondado rapidamente durante jogo/interação. Diagnósticos têm frequência reduzida; falha do diagnóstico de desempenho não encerra o rastreador.

## Evidências reproduzíveis

Os números abaixo são de **reconhecedores isolados**, não do aplicativo completo. Os arquivos de captura e os resultados em `build` são pessoais e não entram na distribuição.

| Medida | Base anterior | Leve |
|---|---:|---:|
| RSS após sequência de caminhada | 1.343 MiB | 120 MiB |
| CPU média por amostra, cache preparado | 48,20 ms | 20,13 ms |
| Pico do processo no replay com cache preparado | 4.568 MiB | 242 MiB |
| Diferença das projeções entre versões | referência | p95 0,12 px; máximo 0,18 px |

A comparação usa as mesmas 60 amostras de `build/minimap-walk-source.npz`. A base reconheceu 41 e o Leve 40; a diferença fica na aquisição inicial (amostra 1). Após a amostra 7, as amostras reconhecidas e as perdas coincidem. Isso não aprova sozinho a continuidade da sessão completa. O replay frio do Leve registrou pico de 634 MiB, incluindo o carregamento da sequência pelo harness.

Uma captura existente do mapa M foi reconhecida nas 10 tentativas do teste Leve. Os testes sintéticos também conferem uma transformação conhecida em posições independentes, limites/sobreposição dos blocos, identidade das camadas, descarte por orçamento, cache corrompido, vencimento UTC, captura parcial e timers de encerramento do processo auxiliar.

A comparação final de Global com blocos de 1.536 px registrou 64 índices residentes, cerca de 1.173 MiB estabilizados e pico de 1.596 MiB no processo isolado durante preparação. Ao fechar o store, o processo retornou a aproximadamente 57 MiB. Esse é o custo da cobertura pronta do recorte atual, não uma carga de todos os mapas instalados.

Para repetir a comparação, execute `scripts/benchmark_reference_modes.py` com `--reference`, `--capture`, `--mode baseline|light|global` e `--output`. O modo baseline lê a implementação de visão do commit `b0428a6`; `--baseline-ref` permite escolher outra revisão. `--capture` aceita PNG ou a sequência NPZ local. Mantenha captura, amostragem e hardware iguais entre versões, separando preparação fria de uso com cache.

## Aceite do executável

Metas no modo Leve, nesta máquina, somando todos os processos: **600 MiB estabilizados**, **850 MiB de pico** e redução mínima de **40% de CPU** sobre capturas equivalentes. O diagnóstico interno `userData/performance.jsonl` registra RSS, working set privado, CPU normalizada pela máquina, processos, modo e blocos residentes uma vez por segundo. Picos históricos por processo não equivalem a um pico simultâneo da árvore nem devem ser atribuídos a Leve após uma passagem por Global.

Ainda é necessário registrar 30 minutos reais em primeiro plano na região atual, incluindo movimento, M, pan/zoom e teletransporte, e conferir o retorno ao orçamento após trocar de modo/mapa. Não haverá repetição obrigatória do aceite manual de Mondstadt e Liyue. A cobertura regional completa permanece sujeita ao inventário e às validações descritas em REBUILD.md.

## Pacote instalado e abertura

A versão corrigida foi instalada com backup `backups/light-global-20261108-074009Z`, com hashes de progresso/preferências preservados. A primeira tentativa de abertura revelou um nome fora do escopo no agendamento inicial do Ctrl; a abertura completa também identificou consumidores do antigo dicionário de imagens Tk. Ambos foram corrigidos. A conferência posterior abriu o DesktopApp completo, executou o event loop sem erros de callbacks e encerrou com dados isolados, preservando os arquivos pessoais. O código congelado foi inspecionado para confirmar essas correções e a ausência de testes/pytest no pacote. A sessão real de 30 minutos não foi substituída por esse smoke test.


## Atlas AppSample ampliado — hotfix em preparação

212 rasters nativos cobrem os pontos de superfície importados. Busca com 100 mil detalhes resumidos no total, dois blocos locais no Leve e tratamento de detalhes repetidos em trechos sobrepostos. A ampliação de 1,5× ocorre apenas no pequeno recorte de consulta do minimapa, preservando as coordenadas e os limites geométricos.

Na comparação isolada com a captura de gelo existente: cerca de 269 MiB após localizar e atualizações subsequentes de 14–16 ms. A captura antiga de gameplay de Mondstadt foi reconhecida nas dez amostras após essa mudança, sem pedir novo aceite manual; o mapa M foi reconhecido nas cinco amostras. Os relatórios locais em `build/appsample-global-*-image*.json` mantêm matrizes e erros por amostra. A sequência de caminhada tem aquisições/perdas registradas individualmente; não representa uma sessão inteira aprovada.

Esses valores são do reconhecedor isolado, não do aplicativo completo. Não declaram cumprimento das metas de memória total, CPU ou 30 minutos.
