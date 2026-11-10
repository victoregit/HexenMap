# Hexen Map 1.0.5 — Captura gráfica e bandeja do Windows

## Português

- **Captura mais compatível:** quando a captura GDI da tela ou da janela falha, o app tenta Windows Graphics Capture. Inclui recorte da área cliente em modo janela, rejeição de quadros antigos e diagnóstico do método de captura.
- **Bandeja do Windows:** abra o painel pelo ícone perto do relógio ou use o botão direito para encerrar o app.
- **Perfis locais:** mantenha coletas separadas e troque de perfil nos Ajustes, com backups e proteção contra troca após falha de gravação.
- **Primeira abertura automática:** procura saves nas pastas conhecidas e migra um progresso anterior único com backup. Uma instalação nova abre diretamente; conflitos e sinais de save ausente não geram progresso vazio.
- **Avisos em primeiro plano:** recuperação exige uma escolha; falhas fatais avisam e encerram o app.
- **Interface renovada:** ícones oficiais nas categorias, emblemas das sete nações no botão do mapa, olho inspirado na Visão Elemental e corte Electro antes de recolher.
- **Report e apoio:** limite de espera e alternativa por e-mail para reports; botão Buy Me a Coffee integrado.
- **Inicialização após atualização:** ambiente independente do launcher preparado pelo instalador.

### Instalação e dados

Baixe **HexenMap-1.0.5-Setup-x64.exe**. O launcher reconhece esta versão e oferece a atualização automaticamente. O ZIP é uma alternativa portátil: extraia a pasta completa, mantendo os recursos em `userData`.

Coletas, perfis e preferências continuam em `%LOCALAPPDATA%\HexenMap\state`; não são incluídos na distribuição nem removidos pelo instalador. Não apague seus saves ou backups.

### Validação e limites

A captura gráfica foi validada em uma janela real de teste; os testes cobrem 1920×1200, recorte de bordas e fallback. A resolução do problema no computador do tester ainda precisa ser confirmada. AutoMark permanece beta. Se os pins não aparecerem, deixe o jogo em foco e copie o diagnóstico em Ajustes → Diagnóstico · avançado.

## English

- **Capture compatibility:** automatically tries Windows Graphics Capture when desktop/window GDI capture fails, with client-area cropping, stale-frame rejection, and capture diagnostics.
- **Windows tray:** open the panel or exit the app from the notification-area icon.
- **Local profiles:** separate collection progress, manual profile switching, backups, and protection against failed writes.
- **Automatic first launch:** finds known saves and migrates a unique previous save with a backup. Clean installs open directly; conflicts or evidence of a missing save never silently create empty progress.
- **Foreground alerts:** recovery requires a choice; fatal errors display a message and close the app.
- **Updated interface:** official category artwork, cycling nation emblems, an Elemental Sight-inspired eye, and an Electro cut before collapsing.
- **Reports and support:** bounded report wait, email fallback, and an enabled Buy Me a Coffee button.
- **Post-update startup:** the installer prepares an independent launcher environment.

Download **HexenMap-1.0.5-Setup-x64.exe** for installation or automatic updates. For portable use, extract the entire ZIP and keep `userData` with the executable. Personal progress remains in `%LOCALAPPDATA%\HexenMap\state` and is excluded from release assets.

Graphics capture passed a real test-window check; the affected tester's PC still requires confirmation. AutoMark remains beta. If markers do not appear, focus the game, then copy the support diagnostics from Settings.
