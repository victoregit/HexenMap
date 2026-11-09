# Fotos no cartão do marcador

Com o mapa M aberto, segure Ctrl e clique em um ícone desenhado pelo Hexen Map.
O cartão mantém a ação de marcar/desmarcar e exibe as fotos do ponto dentro
do próprio overlay. **Anterior/Próxima** percorre as imagens encontradas.
Não há lista de comentários no cartão.

As imagens são obtidas dos anexos das contribuições da comunidade AppSample.
São consultadas até 50 contribuições da primeira página, ordenadas por votos;
registros sem foto são ignorados na galeria e imagens repetidas são removidas.
As fotos mantêm a proporção, sem corte, dentro do cartão. **Abrir ponto no
AppSample** continua disponível como consulta opcional no navegador.

As consultas são feitas em segundo plano, sem login, somente quando o cartão
é aberto. Usa-se o ID nativo do AppSample e o tipo do marcador, sem aproximação
por coordenadas. Os cinco tipos de baús e categorias `as-o…` são reconhecidos.
Marcadores de outras fontes não recebem fotos por coincidência de ID.

O serviço público consultado é
`https://cache-proxy.lemonapi.com/skywise/comment/v1`, com `action=get`, `app=gim`,
`categoryId`, `docId` e primeira página de 50 contribuições. Consulta real
confirmada em 9 de novembro de 2026. É uma interface externa sem garantia de
estabilidade. Erros de rede ou formato exibem uma mensagem e mantêm as ações
de coleta disponíveis. **Atualizar** tenta uma nova consulta.

O cache pessoal fica em `userData/cache/marker-hints`, tem validade de sete
dias e limite de 128 pontos. Uma cópia antiga pode ser exibida quando a rede
falhar, com identificação. Apenas texto, nome público, votos e caminho da imagem
são guardados; contas, tokens e IDs de usuários da resposta são descartados.
O tempo limite de rede é oito segundos; há no máximo duas consultas pendentes.
As fotos vêm de `game-cdn.appsample.com`, são decodificadas em segundo plano
e reduzidas a até 960×640. Cada resposta admite até 8 MiB e 16 milhões de pixels.
O cache `photos` contém até 128 imagens e 32 MiB; fotos inválidas ou falhas
de rede mostram uma mensagem sem bloquear as ações de coleta ou navegação.
Sem anexos na página consultada, o cartão informa que não encontrou fotos.
O cartão permanece aberto por até dois minutos, ou até ser fechado pelas
condições normais do overlay. Fechar ou trocar o ponto invalida atualizações
visuais antigas; uma consulta iniciada pode concluir o cache em segundo plano.

Verificação automatizada: parsing, tradução, HTML sem execução, imagens,
identidade da fonte, cache, falha de conexão, limite/deduplicação de consultas,
layout Tk com origem negativa, exibição real de PhotoImage, seleção de pontos
sobrepostos e fechamento durante leitura. Download, decodificação e cache de
foto real conferidos. Aceite dentro do Genshin ainda pendente.
