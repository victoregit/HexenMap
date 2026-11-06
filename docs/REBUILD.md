# Reconstrução do overlay — referência única

Atualizado em 6 de novembro de 2026. Estado: **protótipo integrado em validação real; aceite final pendente**.

O usuário aprovou o avanço da reconstrução e priorizou a representação visual dos tipos de baú. Essa aprovação não substitui as medições pendentes listadas abaixo.

## Experiência implementada

O aplicativo abre um painel em português e procura a janela do Genshin continuamente. O painel permite selecionar cinco categorias de Mondstadt, configurar atalhos e confirmar um item quando houver ambiguidade. O mapa próprio e os modos manual/simulado foram retirados da entrada normal. A implementação anterior está em `src/legacy_app.py` para histórico e regressão; não entra no executável novo.

A superfície sobre o jogo desenha somente baús e oculi. Usa uma janela Windows transparente, sem ativação e com passagem de cliques. Reconhecimento positivo da interface e alinhamento do terreno determinam minimapa ou mapa M; nenhuma tecla do jogo é interceptada para adivinhar o estado. Movimento, escala e rotação são obtidos da transformação visual, independentemente da direção do personagem.

Os quatro tipos de baú importados (comum, sofisticado, precioso e luxuoso) têm ícones vetoriais próprios com tampa, corpo, ferragens e fechadura, materiais distintos e ornamentos nos tipos mais raros. São desenhos originais, sem copiar assets do jogo. O painel apresenta a mesma imagem usada no overlay, com quantidade restante/total por categoria; o recorte do minimapa considera o contorno inteiro do ícone. Baús extraordinários têm estilo preparado, mas não são exibidos como categoria disponível nem recebem posições inventadas: essa fonte de Mondstadt não os fornece. Formas de obtenção (puzzles, seelies, desafios) não foram confundidas com tipos de baú.

Sem seleção, sem localização válida, sem foco do jogo ou com captura vencida, não há ícones. A expiração usa o início da captura e relógio monotônico, com limite de 650 ms. Alterações de janela invalidam o resultado anterior. Não há posição inventada nem terreno procedural no caminho de produção.

Atalhos padrão: **Ctrl+Alt+F12** mostra/oculta; **F9** confirma coleta próxima; **F10** desfaz a última coleta da sessão. Todas as teclas são configuráveis entre F6–F12, com ou sem Ctrl+Alt. Conflitos de registro são informados no painel. Coleta automática por atalho exige exatamente um candidato selecionado e ainda não coletado dentro de 22 pixels do centro do minimapa. Vários candidatos exigem seleção explícita no painel, válida por 30 segundos. Nunca interpretar proximidade como coleta automática sem o atalho.

**Ctrl + clique esquerdo** em um baú ou anemoculus abre um menu com “Marcar como pego” e “Desmarcar”, com a ação aplicável habilitada. Segurar Ctrl revela temporariamente os itens coletados em cinza, permitindo restaurá-los pelo próprio mapa. O gesto funciona nas duas superfícies e não exige proximidade do personagem, pois há seleção explícita do marcador. Sobreposições oferecem uma escolha de item por categoria/ID. Sem Ctrl, os cliques continuam passando para o jogo; uma camada de entrada separada recebe o mouse no retângulo inteiro de cada ícone enquanto Ctrl está pressionado. Essa camada usa transparência alfa e regiões Win32, evitando que pixels transparentes do desenho deixem o clique atingir o seletor do jogo. Os ícones ganham um contorno e cursor de mão; a superfície visual permanece sempre click-through. Cancelar, Esc, trocar de aplicação, esconder o overlay ou perder a janela encerram a interação. O menu expira em 30 segundos. Coletar/desmarcar salva atomicamente, preserva o estado anterior se houver falha de escrita e atualiza as contagens.

## Dados, referências e armazenamento

- 561 posições comunitárias de Mondstadt: 269 baús comuns, 209 sofisticados, 9 preciosos, 9 luxuosos e 65 anemoculi. Fonte: [Teyvat.moe](https://github.com/EliteMasterEric/Teyvat.moe/tree/e4566515800070fbc70ded91829d423a6361518c/src/data/features/mondstadt), commit fixado `e4566515800070fbc70ded91829d423a6361518c`. Os arquivos originais e a licença GPL-3.0 estão em `data/community/mondstadt`; `SOURCE.json` registra hashes e URLs. Não representam cobertura atual exaustiva ou itens individualmente conferidos.
- Projeção **Leaflet CRS.Simple**, confirmada no [código da fonte](https://github.com/EliteMasterEric/Teyvat.moe/blob/e4566515800070fbc70ded91829d423a6361518c/src/components/views/map/leaflet/LeafletMap.tsx). Em zoom 7: `x = longitude * 128`, `y = -latitude * 128`. Não é latitude/longitude terrestre nem unidade em metros.
- Referências pessoais ficam em `userData/references/mondstadt`. Nesta instalação foram preparados terreno de alta resolução da cidade, terreno regional e recortes da UI do jogo aberto pelo usuário. A arte original pertence à HoYoverse; o pacote é usado localmente para validação, **não é incluído no executável e não há autorização independente de redistribuição da arte verificada**. Instalações novas sem pacote mostram o estado de referência ausente, sem cair em demonstração.
- O pacote tem `manifest.json`, imagens, hashes, origem, uso permitido e transformações para pixels da referência. Templates da UI incluem suas áreas normalizadas de busca. Referências adicionais podem ampliar a região. O carregador rejeita hashes alterados, imagens ausentes, transformações inválidas e caminhos externos ao pacote.
- Os saves continuam em `userData/progress.json`, ao lado do executável ou na raiz do projeto ao executar Python. IDs da fonte real usam prefixo `teyvat.moe:mondstadt:`; IDs antigos da demonstração são preservados, sem associação geográfica inventada. Coleta e desfazer salvam atomicamente. Preferências ficam em `settings.json`.
- O estado original, inclusive saves e executável, foi preservado em `backups/before-rebuild-*.zip`. O histórico da documentação está em `docs/archive/pre-rebuild`.

## Arquitetura e diagnóstico

`src/live` separa catálogo, pacote de referências, reconhecimento visual, sessão, Win32 tipado e painel. O reconhecedor usa SIFT e ajuste de similaridade com RANSAC, exigindo consenso, distribuição espacial e erro residual aceitáveis. A busca é refeita em cada captura; não depende de coordenadas anteriores para recuperar um teletransporte. Isso implementa o caminho de recuperação, sem afirmar que todo teletransporte já foi validado.

O serviço de reconhecimento é separado da interface. Após a observação do usuário sobre atraso ao arrastar, foi acrescentado acompanhamento óptico entre capturas: fluxo LK com verificação de ida/volta e consenso espacial. O registro absoluto é recalculado em segundo plano; seus resultados são atualizados para o quadro atual antes de desenhar. Falhas de movimento ocultam os ícones, em vez de preservar pixels antigos, e o acompanhamento não prolonga uma âncora absoluta por mais de 1,5 segundo.

As ações de atalhos passam por fila; só a thread Tk altera widgets e desenha ícones. Capturas e resultados são associados à geometria da janela. O reconhecimento não altera o jogo, lê memória, envia teclas ou movimenta o personagem.

`userData/live-session.csv` registra superfície reconhecida, latência de captura/reconhecimento, confiança e erro residual; não contém screenshots. `overlay.log` registra erros. O custo de apresentação e impacto no FPS do jogo ainda não estão medidos. Capturas de pesquisa desta sessão ficam somente em `build`, sem entrar no pacote.

## Evidências e limites do aceite

**Verificado nesta sessão no Windows:** janela real do Genshin detectada em 1366×768; captura externa; reconhecimento do mapa de Mondstadt e do minimapa real; usuário confirmou que os ícones aparecem no minimapa e que acompanham o mapa M com o mouse funcional. O usuário relatou correção atrasada de posição durante o movimento; a correção de acompanhamento óptico ainda precisa de nova conferência no jogo. No registro inicial: erro residual p95 de aproximadamente 1,22 px no mapa M e 0,82 px no minimapa. Isso mede correspondências de terreno aceitas, não erro independente de localização de cada baú. No pacote local posterior, o mapa também apresentou p95 abaixo de 1 px.

**Verificado automaticamente:** 133 testes aprovados, incluindo seleção vazia, transformação de coordenadas, recorte completo dos ícones, rejeição de estimativas vencidas/futuras, recuperação geométrica sintética, rejeição de telas sem textura, ambiguidade, persistência, desfazer, rollback de coleta, seleção manual após voltar ao painel e integridade das referências. Os testes legados usam mocks explícitos para HWNDs fictícios; não contam como prova de integração nativa. A transformação óptica passou em 20 quadros derivados da captura real com pan/zoom conhecido (p95 de aproximadamente 34 ms de processamento); isso não é uma sessão real de arrasto.

**Ainda necessário para aprovar a primeira entrega:**

- Conferir posições de itens conhecidos com pontos independentes dos usados no ajuste, nas duas superfícies.
- Reconfirmar arrasto/zoom no mapa M após a correção do atraso; a passagem de cliques foi confirmada pelo usuário na versão inicial.
- Conferir caminhada, rotação da câmera, retorno após teletransporte e ocultação em menus/carregamento.
- Testar resoluções/DPI adicionais e movimentação da janela entre monitores.
- Completar e avaliar 30 minutos de exploração real, incluindo impacto no jogo. Tempo com o jogo sem foco não conta como exploração.
- Resolver a disponibilidade de referências com permissão de redistribuição antes de anunciar um pacote público que funcione em instalação limpa sem preparação.

Não ampliar cobertura nem declarar o produto pronto usando apenas contagem de testes, correspondências em uma imagem ou benchmarks de funções isoladas.

## Comandos de desenvolvimento

```powershell
python src/app.py
python src/app.py --diagnose
python -m pytest -q
python scripts/build_exe.py
python scripts/live_report.py
```

`--diagnose` retorna código 2 quando dados/referências não estão disponíveis e não abre UI. O build exige PyInstaller no Python utilizado, inclui somente a fonte comunitária com sua licença e não encerra processos do usuário para substituir um executável bloqueado.

Verificação nativa da interação: `python scripts/verify_input_surface.py` usa `WindowFromPoint` para conferir o destino real do mouse dentro/fora da área do ícone e após desativá-la, sem injetar cliques no jogo. A checagem de estilos isolados usada inicialmente não comprovava o destino do clique.
