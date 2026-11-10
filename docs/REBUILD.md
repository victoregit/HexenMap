# Hexen Map — referência atual

Atualizado em 8 de novembro de 2026. Integração em validação; não declarar expansão completa.

## Fonte única e preservação

AppSample é a única fonte operacional de marcadores e referências de terreno. O catálogo pessoal mantém os IDs `appsample:marker:*`, mapas e camadas nativos e hashes de origem. Nenhum pacote de outro fornecedor entra no executável ou serve como fallback. Os pacotes, referências e scripts anteriores foram preservados em `backups/appsample-only-20261108-090437Z`, junto dos originais de progresso e preferências. Créditos históricos permanecem com os arquivos arquivados. Os registros antigos de progresso ficam intactos, sem conversão por proximidade.

A seleção é por mapa e camada do AppSample. A fonte não fornece uma divisão nacional confiável; não mostramos nações inventadas nem herdamos territórios de outra fonte. Mapas sem referência válida permanecem indisponíveis. A migração cria `settings.json.pre-appsample-only.bak`, conserva preferências AppSample e remove filtros de fornecedores retirados.

Imagens do jogo e catálogo pessoal ficam em `userData`, fora do Git e do executável. Uso pessoal local; não foi presumida licença de redistribuição de arte ou dados. O manifesto de cada pacote conserva URLs, hashes e condições.

## Reconhecimento e desempenho

Leve é o padrão; carrega no máximo dois blocos detalhados e limita seu cache a 256 MiB. Índices globais resumidos ajudam a recuperar a posição. Global é opcional e restrito ao mapa/camadas escolhidos, com aviso de memória, CPU e carregamento; falha de memória retorna ao Leve. Não se carrega um bitmap mundial em tempo de execução.

O atlas nativo AppSample da superfície usa blocos sobrepostos de até 1280 px. O relatório `build/appsample-surface-atlas-report.json` distingue arquivos preparados, recortes parciais e pontos sem cobertura. Arquivos presentes não equivalem a validação no jogo. A busca distingue cópias de um mesmo detalhe em trechos sobrepostos; só uma correspondência geométrica atual autoriza desenhar. Captura e desenho são externos, sem memória ou comandos do jogo.

A bússola e a busca guiada foram retiradas. O reconhecimento da seta central serve apenas para confirmar o minimapa; não há orientação nem alvo amarelo.

## Uso e progresso

Painel independente de 360×540, recolhível em botão animado realçado. Ctrl+clique abre uma ação reversível; fora do pin os cliques passam ao jogo. Coleta, desmarcação, desfazer e persistência usam o mesmo recorte. F8 abre/recolhe, F9 coleta/resolve candidatos, F10 desfaz; os atalhos são configuráveis.

Não há prazo universal de reposição. Permanentes não expiram; recursos sem regra AppSample qualificada mostram “Reposição não confirmada”. O motor UTC suporta duração e reset América, mas regras de outra fonte não são herdadas.

## AutoMark beta

Ajustes → Exploração contém “Marcar baús automaticamente”, BETA e desligado por padrão. Sem pacote visual conferido a opção informa o bloqueio e não captura sinais adicionais ou grava coletas. São necessárias gravações reais positivas e negativas, origem e hashes dos templates e conferência datada.

O detector usa o símbolo nativo de interação de baú, compartilhado entre os tipos; não depende do nome de uma raridade nem da quantidade de gemas. Após o aviso desaparecer, exige loot e gemas **ou** EXP de aventura na mesma sequência curta. Uma coleta genérica de plantas, sozinha, não confirma um baú. Os testes de associação cobrem comum, sofisticado, precioso, luxuoso e extraordinário, com marcação/desmarcação e desfazer. Isso não equivale a cinco raridades conferidas visualmente no jogo.

O leitor de avisos tem execução própria a até 8 Hz, independente do reconhecimento pesado do mapa. Só arma uma abertura com posição válida. Uma perda breve de alinhamento não apaga uma abertura já localizada enquanto o HUD continua confirmado; foco, menu, carregamento, troca de seleção ou resolução e vencimento descartam a sequência. O evento usa a posição registrada na interação, não a posição posterior do jogador. Os ícones continuam obedecendo à validade do rastreamento. Captura-se a faixa necessária do HUD e os recortes de interação/recompensas; desligado, o leitor não captura e libera buffers após cinco segundos ocioso.

Cada onda gera no máximo um evento e considera todos os baús do recorte, mesmo desmarcados nos filtros. Baú já coletado próximo não autoriza marcar o seguinte. Ambiguidade pede escolha por F9, sem abrir M; F10 desfaz. O log local distingue amostragem, falta de posição, sinais de recompensa, evento, candidato ausente, item já coletado, ambiguidade e salvamento.

A calibração pessoal inicial foi feita em português, 1366×768, com um baú sofisticado. Uma segunda abertura independente, também de sofisticado e com fundo mais claro, revelou a fragilidade do recorte por brilho absoluto. O detector passou a comparar contraste local; na reprodução, associou o novo baú correto em cópia do progresso, com um evento. Uma gravação separada de caminhada/coleta de frutas é o controle negativo. Os arquivos originais e hashes de cada recorte ficam na instalação pessoal. O conjunto ainda não cobre todos os fundos, diálogos de missão e tipos de baú em sessões reais.

Full HD (1920×1080) é a referência de desenho. A escala acompanha a altura da janela, com loot ancorado à lateral e interação ao centro. Testes sintéticos cobrem também ultrawide, 4:3, proximidade e descarte ao redimensionar durante uma abertura. Os replays redimensionados para outras resoluções são testes em imagens, não sessões reais nessas telas. A opção continua BETA e desligada por padrão; alterações do HUD/idioma precisam ser conferidas.

## Aceite restante

Conferir recuperação nas nações afetadas e V na neve, com pontos independentes. Ampliar a validação real de abertura/loot para as cinco raridades e mais cenários negativos. Completar referências das outras camadas/mapas. Medir o aplicativo inteiro por 30 minutos na região atual nos modos Leve e Global; testes isolados não aprovam memória, continuidade ou cobertura global. Não repetir o aceite manual já feito de Mondstadt e Liyue.

## Catálogo em português

A revisão versionada confirma 717 das 757 categorias; 40 permanecem em Identificação pendente com ícone e ID. Recursos contém 347 categorias em seis subgrupos recolhíveis. Busca por aliases e nomes sem acentos expande resultados sem alterar o recolhimento anterior. A mesma apresentação alimenta painel, cartão e bússola. Fontes, limites e relatório estão em [LOCALIZATION.md](LOCALIZATION.md). Não houve alteração de posições, progresso ou temporizadores.

## Estabilidade em validação

Não há mais bússola ou alvo de busca. Aberturas sem posição podem aguardar até três segundos para reconstrução geométrica do instante original, com recortes em memória limitados a 16 MiB. A posição posterior não autoriza uma coleta. [STABILITY.md](STABILITY.md) registra os contratos, os testes e os critérios ainda pendentes de aceite real.
# Pendências de distribuição — registradas em 10/11/2026

Implementação local autorizada em 10/11/2026. O instalador e o launcher estão prontos para teste; publicação no GitHub continua pendente. Detalhes em [UPDATES.md](UPDATES.md).

- [x] **Launcher com atualização ao abrir:** consulta Releases públicas, compara versões, baixa automaticamente o Setup e verifica SHA-256 antes de instalar. Bloqueia atualização com overlay aberto e mantém a versão instalada disponível quando a consulta falha. Há recuperação local da versão anterior.
- [x] **Build instalável para Windows:** instalador por usuário, atalho no menu Iniciar apontando para o launcher e registro em Aplicativos instalados. Arquivos existentes de `userData` não são sobrescritos, inclusive nas reinstalações, nem removidos na desinstalação.
- [x] **Validação automatizada e teste real isolado:** instalação limpa, atalho, registro de desinstalação, upgrade, recuperação e preservação de coletas/preferências fictícias depois da desinstalação. Falhas de download e respostas GitHub são cobertas por testes.
- [ ] **Aceite final:** conferir manualmente a busca do Windows e a experiência do launcher no PC de teste; validar o download ponta a ponta quando existir uma próxima Release publicada.

Decisões adotadas: Inno Setup, instalação em `%LOCALAPPDATA%\Programs\Hexen Map`, dados locais em `userData`, canal conforme a versão instalada (beta ou estável) e atualização automática ao abrir, consultando `victoregit/HexenMap-Releases`. O launcher é uma abertura com animação giratória, sem botões: confere, atualiza quando necessário e abre o aplicativo; falha de consulta segue com a versão instalada. O conteúdo autorizado para a release pública ainda precisa de revisão.
