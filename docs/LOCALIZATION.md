# Catálogo de apresentação em português brasileiro

Revisão de 8 de novembro de 2026: **717 de 757 categorias confirmadas; 40 com identificação pendente**. Antes, 430 apareciam em “Sem tradução revisada”. O levantamento antigo perdia 339 nomes ao ler apenas o texto alternativo das imagens.

Foram conferidos os seletores PT/EN dos sete mapas permanentes importados. A coleta usa também o nome acessível do botão e mantém o grupo quando o nome falta. Correspondências entre nomes não unem IDs de origem diferentes.

## Recursos

As 347 categorias de recursos ficam em subgrupos inicialmente recolhidos:

| Subgrupo | Categorias |
| --- | ---: |
| Especialidades locais | 63 |
| Plantas e ingredientes | 43 |
| Minérios | 9 |
| Madeiras | 33 |
| Pesca e animais | 180 |
| Outros materiais | 19 |

Especialidades prevalecem sobre a forma do material. A ordenação ignora acentos. A busca considera nomes portugueses, ingleses, aliases e IDs; expande os resultados e, ao limpar, restaura os grupos recolhidos. Todos/× em um subgrupo afeta somente seus membros.

## Fontes e limites

O [catálogo versionado](../data/localization/appsample-pt-BR.json) registra nome, aliases, grupo, subgrupo, ID de origem, estado, data, URLs e fundamento de cada correspondência. A apresentação local confirmada prevalece sobre indicadores antigos de tradução não revisada, sem modificar o pacote original.

- [AppSample PT](https://genshin-impact-map.appsample.com/pt/) e [EN](https://genshin-impact-map.appsample.com/): identificação por ID de imagem e grupo, incluindo os mapas separados.
- [HoYoWiki](https://wiki.hoyolab.com/pc/genshin/entry/14?lang=pt-pt): conferência direta de Flor Doce e Lâmpada de Grama.
- [genshin-db](https://github.com/theBowja/genshin-db), revisão `8e5badd60b5d894284ccc927a56c9683529d2592`: referência comunitária de nomes localizados do jogo. Correspondência exata pelo nome inglês, pasta apropriada e mesmo ID do jogo entre os arquivos de idiomas. Não é um serviço oficial da HoYoverse. Licença e atribuição acompanham os metadados.

Os 40 tipos pendentes não estavam identificados nos seletores conferidos. Permanecem com ícone e ID em “Identificação pendente”; a ausência não foi preenchida por reconhecimento visual ou aproximação. O [relatório completo](LOCALIZATION_REPORT.json) lista seus IDs, contagem de pontos, mapas e motivo. O levantamento não afirma que todos os nomes foram conferidos diretamente no jogo.

As fontes de tradução não acrescentam posições. AppSample continua sendo a única fonte operacional de marcadores/mapas. Não há consulta de tradução pela internet durante o uso. IDs, imagens, seleção, progresso, coordenadas e políticas de reposição são preservados.

## Manutenção

`scripts/collect_appsample_labels.py` extrai nomes de HTML público salvo com `--html`, `--source-url` e `--output`; recusa extração vazia. Quando necessário, os mesmos campos podem ser coletados do DOM público renderizado, sem exportar conta, marcações ou credenciais.

`scripts/build_presentation_catalog.py` gera o catálogo offline a partir dos levantamentos PT/EN e da referência localizada pareada; registra hashes dos insumos e sua versão. `scripts/report_localization.py` audita a instalação sem ler progresso. Ausência de fonte mantém o estado pendente. A regressão cobre busca, classificação, preservação, contadores e subgrupos; revisão de nomes não equivale a validação de alinhamento no jogo.
