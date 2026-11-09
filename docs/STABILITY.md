# Estabilidade do minimapa e AutoMark

Implementação de 8 de novembro de 2026. **Aceite em jogo pendente**; esta alteração não declara concluída a meta de redução de 80% das interrupções curtas.

## Comportamento

- Bússola, alvo amarelo, busca guiada e seus atalhos foram removidos. Marcadores permanecem no minimapa e no mapa M; AutoMark não depende de navegação.
- O fluxo óptico usa máscara central e contraste local em terreno pouco contrastado. Até três quadros recentes permitem recuperação verificada de até 500 ms, com limite de deslocamento e idade da âncora. Não se conserva uma posição vencida para esconder falhas.
- Uma ausência isolada do glifo de HUD admite até 350 ms de tolerância com evidência atual do minimapa. Mapa M, perda de foco, geometria diferente e quebra de continuidade descartam o contexto.
- A primeira tentativa ao vivo revelou glifo de HUD ausente apesar de borda e seta detectáveis. A segunda revisão permite qualificar gameplay pela geometria atual do minimapa, independentemente desse glifo, e ainda exige correspondência do terreno para desenhar. Pequenas variações na detecção da borda não mudam o recorte de um HUD fixo quando a geometria recém-detectada concorda.
- Ctrl+clique continua utilizando as posições realmente desenhadas. IDs, coordenadas, seleção e persistência não foram migrados.

## Recuperação de abertura

O AutoMark independe do alvo amarelo e das categorias visíveis. Abertura e recompensas são lidas pelo fluxo próprio de HUD.

Uma abertura sem localização pode aguardar até três segundos. Um buffer de recortes do minimapa, apenas em memória e limitado a 16 MiB, permite reconstruir a posição no instante registrado. Cada passo exige correspondência geométrica; lacunas maiores que 300 ms, erro acumulado acima de 3 px e mudança de geometria rejeitam a reconstrução. A âncora localizada e sua imagem devem pertencer à mesma captura.

As recompensas da mesma sequência são preservadas durante a espera. A posição posterior do jogador não substitui a posição da abertura. Sem comprovação suficiente, nenhuma coleta é gravada; o painel orienta usar o atalho manual. Ambiguidade, baú próximo já coletado e evento repetido mantêm os bloqueios anteriores. Desfazer permanece disponível. Teletransporte/quebra de continuidade, foco, M e troca de contexto cancelam o evento.

## Evidência e limites

Os testes cobrem reconstrução reversa, precisão do instante, teto de memória, quadros sem textura, prazo, recompensas durante recuperação, marcadores junto ao jogador, atalhos migrados e troca de contexto. O replay do detector nas duas aberturas reais já gravadas produz um evento por abertura; a sessão negativa de 115 quadros produz zero. Isso não equivale a novas aberturas verificadas de todas as raridades.

O primeiro ensaio do minimapa reutilizava o estado de seleção de referências entre antes/depois; seus números são exploratórios. A comparação deve usar reconhecedores independentes e as mesmas capturas. Falhas sobre quadros em que o próprio minimapa perde o terreno não autorizam exibir coordenadas antigas. Comparar matrizes antes/depois também não substitui erro contra pontos independentes.

O aceite exige sessão de 30 minutos na região atual, registrando gaps, atraso, erro, CPU, memória e resultados das coletas. Sem sessão medida e revisão dos eventos, a build permanece em validação. Não repetir o aceite manual de Mondstadt/Liyue e não ampliar mapas durante este marco.

A tentativa inicial foi interrompida e registrada como falha de qualificação de gameplay, sem contar para o aceite. Os registros locais ficam em `build/stability-live-v1-failed.json`. Não foram gravadas novas imagens nessa tentativa.

## Hotfix de interação e proximidade

O executável solicita elevação pelo manifesto do Windows. O diagnóstico encontrou jogo elevado e overlay sem elevação, impedindo a observação/interação com Ctrl. A permissão aparece ao abrir o aplicativo.

Não existe exclusão central para esconder baús próximos. O rastreamento relativo pode continuar com âncora absoluta de até cinco segundos somente com confiança alta e erro acumulado limitado; cada posição desenhada exige uma transformação comprovada na imagem atual. Sem essa comprovação os pins se ocultam. Coordenadas mundiais não são alteradas e o clique usa os pins desenhados.

As preferências antigas recebem backup `.pre-no-compass.bak` antes de retirar apenas os atalhos da navegação. Coletas, categorias e demais atalhos permanecem.

## Seta unida à água azul

Uma amostra real em foco mostrou a seta unida à água na máscara antiga (931 pixels no recorte); a segmentação local separou o glifo de 111 pixels. A recuperação usa contraste cromático local, preservando o teste de cor já validado quando ele encontra um componente inequívoco. O tamanho de recuperação escala com o HUD, não com círculos ocasionais do terreno.

No HUD desktop largo padrão, a geometria normalizada do minimapa só é aceita com a seta nativa confirmada na captura atual. Outros layouts continuam com recuperação pela circunferência e disco inscrito. A projeção mundial ainda exige correspondência do terreno; a geometria do HUD não fabrica uma localização.

No replay de uma abertura real, os 179 quadros foram localizados e o AutoMark associou um único evento ao mesmo baú da referência anterior, usando progresso de teste separado. Isso não substitui a conferência de uma nova abertura ao vivo. A amostra auxiliar ficou somente em memória e foi descartada; não houve gravação de novos arquivos de imagem. Capturas da janela sem foco que retornaram M antigo foram excluídas da evidência. Não foi alterado o backend operacional de captura nem acrescentada dependência de captura gráfica à build.

### Nova abertura ao vivo

Em 8 de novembro, às 22:43:49 (America/Sao_Paulo), o fluxo reconheceu a interação, loot e EXP de aventura, manteve posição válida e salvou um único baú próximo sem ambiguidade. O registro permanente foi conferido no progresso. Isso valida esta abertura, não todas as raridades nem a meta geral de redução de piscadas ou a sessão de 30 minutos. Não foram gravados novos arquivos de imagem/vídeo.

O usuário confirmou a marcação e a melhora das piscadas nesse teste de baú comum. A regressão final passou em 360 testes. A conferência de longa duração permanece pendente.
