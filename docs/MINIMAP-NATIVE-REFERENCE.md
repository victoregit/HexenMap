# Referências nativas do minimapa — candidata local

## Problema observado

Em 12 de novembro de 2026, o usuário voltou a relatar desaparecimentos dos pins
durante o uso normal. A aprovação local anterior não encerra esta regressão.
A captura nova da cópia 2.0.0 registrou 226 quadros de 1366×768 durante caminhada
e rotação de câmera em Windrise, com AutoMark ligado. O terreno do minimapa
permaneceu visível nessa sequência; os logs registraram expirações de referência.

Uma captura do M permitiu localizar a área na referência existente. O problema
não foi resolvido simplesmente substituindo as imagens do mapa. As experiências
de contraste, resolução e roteamento na captura anterior não produziram um ganho
consistente na sequência nova e não foram incorporadas nesta candidata.

## Alteração em teste

- Mantém até três imagens nativas do minimapa, em memória, associadas ao resultado
  de uma localização independente do mapa-base. A imagem guardada corresponde ao
  quadro original dessa localização, antes da reprojeção assíncrona.
- Exige contexto identificado, confiança mínima de 0,8 e erro/incerteza de até
  1,5 px para formar uma referência nativa. Uma revalidação local nunca se torna
  sua própria referência, evitando realimentação do erro.
- Quando a referência global demora a renovar, verifica os pixels atuais contra
  essas imagens. Aplica os mesmos limites de fluxo, distribuição, RANSAC, resíduo
  e incerteza existentes. Não mantém uma posição anterior após falhar.
- Verificações incompatíveis com o rastreamento atual são rejeitadas. As imagens
  são descartadas ao perder foco, mudar de geometria, entrar em outra superfície
  ou aceitar uma correção global incompatível.
- A busca global continua funcionando. Sua idade permanece distinta da idade da
  última verificação nativa nos diagnósticos. Não aumenta os prazos do fluxo
  relativo para esconder resultados sem evidência visual.
- Não altera o detector de abertura/recompensa do AutoMark nem os IDs e coletas.
  Não salva automaticamente imagens pessoais ou substitui o atlas instalado.

## Validação e limites

Os 140 testes relevantes passaram, incluindo reprojeção atrasada, reset, contexto,
geometria, imagens sem correspondência, imagens futuras, memória limitada e
regressões do AutoMark. O conteúdo das referências é limitado a três quadros.

Uma reprodução técnica da captura nova, com uma pose de identidade injetada uma
vez e falhas globais simuladas, mostrou melhora de continuidade. Essa pose é um
artifício de teste em coordenadas de pixels: o ensaio não valida localização
absoluta no mundo, precisão independente nem a demora da primeira localização.
Não deve ser divulgado como atendimento à meta de 99,5% de quadros válidos.

O alinhamento visual com o M e os ensaios não substituem a validação real do
usuário. Esta alteração ainda é uma candidata local, sem publicação de release.
