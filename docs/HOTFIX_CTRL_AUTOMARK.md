# Hotfix — Ctrl e AutoMark

## Ctrl

O renderizador enumerava todos os elementos do Canvas antes e depois de
criar cada pin. A revelação em massa tinha custo quadrático. Agora cada
primitiva é registrada na criação; movimento e remoção usam IDs diretos.
Novos pins são criados com orçamento de 6 ms por atualização, e só os já
desenhados entram na interação.

A máscara exata de cliques é preparada em um único executor, com descarte
de trabalhos substituídos e sem chamadas Tk/GDI no worker. Formatos são
armazenados em cache, combinados em uma máscara raster e convertidos em
faixas não sobrepostas. O bitmap de trabalho tem limite de 16 milhões de
pixels; acima disso usa-se a montagem por retângulos. Áreas transparentes
continuam deixando os cliques passar.

Uma máscara parcial só pode ser reutilizada se todas as suas formas
continuarem desenhadas nas mesmas posições. Troca de contexto ou soltura
de Ctrl cancela os trabalhos. A janela de entrada recebe configuração,
posicionamento e ativação somente quando necessário. A preparação pode
começar antes de Ctrl, usando apenas os pontos visíveis do recorte atual.

### Ensaio controlado

`scripts/benchmark_ctrl.py`: 1.000 pins em Tk, 20 repetições, imagens em
cache e novos elementos do Canvas em cada repetição. Não mede composição
do monitor, chamadas GDI de aplicação nem captura/reconhecimento do jogo.

| Medida | Antes | Depois |
| --- | --- | --- |
| Desenho, mediana | 111,55 ms | 10,07 ms |
| Desenho, maior amostra | 148,95 ms | 12,52 ms |
| Construção da máscara | 40,79 ms | 23,10 ms, no worker |

No fluxo em lotes, o percentil 95 até a primeira máscara interativa foi
31,63 ms e a maior tarefa medida na interface foi 8,21 ms. Todos os pins
foram submetidos em mediana de 75,93 ms. A primeira interação não significa
que todas as formas já terminaram de entrar na máscara. O resultado não
garante esses tempos em toda máquina; o teste em jogo pelos testadores
continua necessário.

## AutoMark

Os sinais de recompensa já usavam a altura real da área cliente e âncoras
esquerda/centro. Uma etapa anterior, a confirmação de gameplay/mapa,
comparava o HUD em apenas alguns fatores aproximados de escala. Agora o
serviço normaliza essa imagem para a altura de origem do pacote qualificado
antes de comparar os sinais da interface. Os pixels originais são mantidos
para localização e recuperação do minimapa.

A resolução da janela e a referência usada são registradas no log a cada
troca de contexto. Não houve redução de limiares, alteração de candidatos,
IDs, progresso ou regras de gravação. O pacote instalado é PT-BR e suas
referências de HUD e sinais foram capturadas em 1366×768.

### Evidências disponíveis e pendências

`scripts/replay_automark_hotfix.py` reproduziu duas sequências reais de
abertura e uma negativa (474 quadros, todos originalmente 1366×768).
Cada sequência positiva produziu um evento; a negativa não produziu nenhum.
O resultado foi preservado nas versões sintéticas 1920×1080 e 2560×1440.
O replay fornece posições conhecidas e não grava coletas; não é um aceite
de localização ou associação espacial em jogo.

As aberturas reais disponíveis são de baús sofisticados. A associação aos
cinco tipos, recuperação, ambiguidade e deduplicação têm cobertura automática.
Capturas reais de 1080p/1440p e aberturas de outras raridades ainda precisam
ser conferidas pelos testadores; não se declara compatibilidade real
completa nessas resoluções a partir de imagens redimensionadas.

## Entrega

Regressão de desenho, máscara, Ctrl, foco, progresso e AutoMark. A região
binária também foi aceita pelo GDI do Windows em teste, preservando os
buracos transparentes. Executável e ZIP portátil recebem o hotfix;
instalação usa backup e confere o hash do progresso antes/depois.
Nenhuma migração de progresso ou API pública nova.
