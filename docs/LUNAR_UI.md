# Tema Lunar compacto

O painel usa fundo índigo `#171923`, superfícies `#202330`, texto pérola
`#F0EDF7` e seleção lavanda `#B8A2EE`. Os controles reutilizam imagens
arredondadas em memória; não há blur ou animação nova por captura.

Itens e Ajustes ficam sempre acessíveis. Categorias começam recolhidas;
baús e oculi usam quatro colunas. Ajustes tem seis seções, com apenas uma
aberta por vez. Estado, visibilidade, desfazer e Jogar ficam no rodapé.
Cartão de coleta, prévia de importação e ajuda seguem a mesma paleta.

## Verificação de layout

O verificador Tk isolado `scripts/preview_lunar.py --check` exercita
seleção por mouse/teclado, recolhimento, exclusividade das seções, rodapé,
tooltips e reutilização das imagens. As resoluções são áreas simuladas
para dimensionamento, não capturas de seis monitores físicos.

| Tela | Escala | Painel em pixels |
| --- | --- | --- |
| 1366 × 768 | 100% | 360 × 540 |
| 1366 × 768 | 125% | 450 × 668 |
| 1366 × 768 | 150% | 540 × 656 |
| 1920 × 1080 | 100% | 360 × 540 |
| 1920 × 1080 | 125% | 450 × 675 |
| 1920 × 1080 | 150% | 540 × 810 |

A altura se ajusta à área útil, mantendo a lista rolável. A aparência real
de Itens e Ajustes foi inspecionada em uma janela Tk de prévia, sem jogo.
Os testes cobrem também importação explícita, cartão, fotos, foco,
persistência e interação existente. O cartão reduz a área de foto se
precisar caber na janela do jogo.

Regressão final: **398 testes passaram**, em dois processos (389 da suíte
principal e nove de fotos/cartão). Os módulos de tema, Ajustes e lista
foram conferidos no arquivo empacotado do executável.

## Medição isolada de interface

`scripts/benchmark_lunar_ui.py` compara o commit `6edf222` com o Lunar,
usando o mesmo catálogo ilustrativo, painel 360 × 540 e redesenhos da lista.

| Medida | Anterior | Lunar |
| --- | --- | --- |
| CPU mediana por redesenho | 3,18 ms | 3,44 ms |
| Memória residente do processo | 75,16 MiB | 67,49 MiB |

São medições pontuais da interface, sem captura nem reconhecedor. Não
comprovam redução de memória ou CPU da aplicação completa durante o jogo.
O acréscimo medido no redesenho foi de aproximadamente 0,26 ms. A lista
continua virtualizada e os recursos gráficos são reutilizados.

Rastreamento, AutoMark, coordenadas, progresso e contratos de importação
não foram alterados. O aceite visual e de foco da build durante uma
sessão real permanece separado dos testes automáticos; não foi repetido
o aceite manual das regiões antigas.

A limpeza dos Ajustes foi recuperada seletivamente do stash do GitHub
Desktop. O stash e os READMEs bilíngues publicados foram preservados.

## Correção de fluidez

A primeira medição de redesenho da lista acima não cobria a troca de abas.
O teste ampliado `scripts/benchmark_panel_response.py` reproduziu travadas
nessa operação mesmo sem jogo ou reconhecimento. O centro de apenas alguns
pixels dos fundos arredondados era repetido pelo Tk milhares de vezes.
O atlas agora tem centros maiores e dimensões mínimas explícitas nos
controles, preservando os cantos e evitando esse excesso de composição.

Na comparação local isolada, a mediana da ida e volta Itens/Ajustes passou
de aproximadamente 1,2 segundo para 55 ms; abrir/recolher uma seção ficou
em 8 ms. Esses números incluem processamento de eventos e desenho Tk de
uma prévia, não são uma garantia de latência durante o jogo.

Também foram eliminados a varredura do catálogo no ciclo sem confirmações
pendentes, o redesenho de listas ocultas, recontagens por seleção e pedidos
de layout idênticos nos Ajustes. A busca agrupa teclas por 65 ms antes de
reconstruir a lista. Seleção, coleta e gravação continuam funcionando sem
esperar a busca. Os quatro testes de responsividade verificam essas filas
e atualizações, além da regressão existente.

## Aproximação à composição aprovada

Após comparar a instalação com a proposta, foram ajustados o símbolo e
subtítulo do cabeçalho, a faixa única de navegação, mapa e camada em uma
linha, a lupa e o texto da busca, separadores e símbolos dos grupos e o
nome completo do baú extraordinário. Os controles de seleção em lote
continuam identificados. A lista inicia recolhida, conforme a preferência
definida para o aplicativo; a proposta ilustrativa mostrava Baús aberto.

A revisão visual foi feita na janela Tk real de prévia. Os 25 testes
diretamente relacionados à composição, DPI e interação passaram após os
ajustes. A nova medição isolada manteve cerca de 52 ms na ida e volta de
abas e 7 ms na seção dos Ajustes. Isso não substitui o aceite visual do
usuário nem mede o reconhecedor durante o jogo.
