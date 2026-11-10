# 0.4.1-beta.1 — HUD em janela e AutoMark

- A faixa de mapa/camada foi retirada da aba Itens. Seus controles estão
  em Ajustes → Painel e compartilhamento, sem modificar a seleção salva.
- O botão de mapa geral usa agora o símbolo de globo, sem os anéis.
- O reconhecedor das duas superfícies passou a comparar as escalas exatas
  da área cliente, além das variantes anteriores. A resolução do monitor
  não é usada como substituto das dimensões da janela do jogo.
- A recuperação do minimapa também considera o HUD limitado pela largura
  em janelas 16:10, exigindo confirmação visual do símbolo nativo. Formatos
  não padronizados preservam a recuperação pela circunferência.
- Os sinais do AutoMark podem confirmar a escala limitada pela largura
  pela própria imagem; essa escala permanece estável durante a recompensa.
- O AutoMark usa a mesma evidência positiva de HUD do rastreador. Ele não
  descarta a abertura só por faltar a seta central por um instante. Menus,
  mapa M e perda de foco continuam invalidando a sequência, e nenhuma
  coleta é gravada sem posição e candidato espacial comprovados.

## Conferências

Testes sintéticos cobrem 1366×768, 1920×1080, 1920×1200 e área cliente
1904×1161. As gravações qualificadas anteriores de 1366×768 mantiveram as
aberturas positivas e zero eventos na sequência negativa; versões
redimensionadas continuam identificadas como sintéticas.

No teste ao vivo desta correção, em cliente 1366×768, houve recuperação
verificada da posição, evento de abertura e resultado `marked / saved`.
O único candidato foi o ponto `appsample:marker:103785`, classificado no
catálogo como baú extraordinário, com distância projetada de 2,7 pixels.
O registro permanente foi conferido no arquivo de progresso. Não foram
gravadas novas imagens nesta conferência.

Isso não declara conferidos os PCs remotos: ainda faltam os diagnósticos
reais de 1920×1080 e 1920×1200. Falta de pontos pode também decorrer de
seleção vazia, captura uniforme/preta, pacote ausente ou alinhamento.

## Suporte sem terminal

No PC afetado: Ajustes → Diagnóstico → Copiar diagnóstico para suporte.
O texto informa versão, tamanho real da área cliente, DPI, filtros,
referências, estado de localização e AutoMark e estatística do último
quadro em foco. Não inclui screenshots, conta, cookies ou credenciais.
O aplicativo não envia o diagnóstico; o jogador decide se vai compartilhá-lo.
