# Hexen Map 1.0.2

Candidata preparada na develop. Merge na main e publicação aguardam o OK do responsável.

## Mudanças

- Miniatura do overlay recolhido com fenda Electro instável e símbolo em rotação: acelera com a abertura, desacelera e desaparece no fechamento.
- Transição ao usar Jogar, recolher ou F8: corte atravessa o painel, a janela fecha em direção à fenda e encolhe para a miniatura.
- Continuidade entre a transição e a miniatura, com posição e tamanho normal preservados e janela temporária sem ativação.
- Launcher com a constelação Viator do Traveler se formando, em transparência, sem fundo de ícone e sem emblema sobreposto.
- Remoção das artes rejeitadas/substituídas e organização dos mestres aprovados.

## Base incorporada

Inclui o launcher/instalador com atualização ao abrir e os ajustes de proteção/recuperação de progresso da linha 1.0.1 que estavam pendentes de commit no repositório. Progresso e preferências permanecem fora da pasta versionada do programa. Os pacotes de distribuição não incluem progresso pessoal.

## Validação

- 482 testes automatizados aprovados na suíte completa.
- Teste real de Tk/Win32 da transição, retorno, fase da miniatura, posição e tamanho; estilo NOACTIVATE da janela temporária.
- Reconstrução das fontes aprovadas conferida contra os quadros aceitos antes da remoção das propostas anteriores.
- Assets com tempos independentes, alpha e ausência de placa/fundo no loading verificados.
- Assets aprovados conferidos dentro dos dois executáveis compilados.
- Instalador testado em instalação isolada: instalação limpa, upgrade, atalhos, registro de desinstalação, recuperação e preservação dos dados fictícios após desinstalar.

## Distribuição preparada

- `HexenMap-1.0.2-Setup-x64.exe` e SHA-256.
- `HexenMap-1.0.2-Windows-x64.zip` e SHA-256.

A autorização de merge/publicação é uma etapa separada. Estes arquivos permanecem locais até o OK solicitado.
