# Identidade visual aprovada

## Overlay recolhido

`minimized.png`: fenda Electro instável com símbolo girando, identidade `electro-rift-spin-v3`. Atlas RGBA de 8×15 células de 192×192; 120 quadros, 24 FPS, ciclo de 5000 ms. O bloco `minimized` em `animations.json` contém os tempos individuais e a geometria.

Jogar, recolher e F8 fazem a transição curta descrita em `docs/PANEL_TRANSITION.md`; a miniatura retoma o ciclo na fase de fenda aberta.

## Inicialização do launcher

`loading.png` e `loading/00.png` a `47.png`: **somente a constelação Viator do Traveler**, com alpha transparente, sem fundo de ícone nem emblema do HexenMap. São 48 quadros de 192×192 a 24 FPS; o ciclo soma 2000 ms. O tempo está em `loading_durations_ms`, independente do overlay.

## Ícones gerais

`app.png` e `app.ico` são os ícones gerais em uso e foram preservados nesta seleção. O ICO tem tamanhos de 16 a 256 pixels.

## Recriar os recursos aprovados

Os mestres ficam em `data/source/brand`, fora do conjunto de assets empacotado no executável. Artefatos gerados e prévias ficam em `artifacts`, ignorado pelo Git.

```powershell
python -m scripts.render_electro_rift_spin
python scripts/prepare_overlay_badge.py
python -m scripts.render_traveler_constellation
python scripts/prepare_launcher_constellation.py
```

As propostas rejeitadas foram removidas. `SOURCE.json` registra os hashes dos recursos em uso. Os arquivos em `brand` são incluídos no `HexenMap.spec`; o launcher inclui apenas seus próprios quadros, metadados e ICO.
