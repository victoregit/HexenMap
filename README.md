# Hexen Map

**Hexen Map** é um overlay externo de exploração para os mapas nativos do Genshin Impact, em reconstrução e validação real no Windows.

Abra **HexenMap.exe** ou **Iniciar_HexenMap.bat**, selecione o que procurar no painel e volte ao jogo. O aplicativo desenha somente ícones sobre o minimapa e o mapa M; não abre outro mapa nem simula o personagem. Use o jogo em janela ou sem bordas.

- **F8:** abrir/recolher o painel em um botão animado e arrastável (configurável). Clique no GIF para reabrir; a janela independente e suas funções são preservadas.
- **Ctrl+Alt+F12:** mostrar/ocultar overlay.
- **F9:** marcar o item próximo como coletado; se houver mais de um, selecionar no painel.
- **F10:** desfazer a última coleta da sessão.
- **Buscar itens:** a bússola guia até o item disponível mais próximo entre as categorias selecionadas (baús, flores, minérios, oculi etc.). Recalcula o mais próximo conforme você anda, sem precisar confirmar coleta; seleção vazia não gera alvo. Atalhos padrão: **Ctrl+Alt+F9** iniciar/parar e **Ctrl+Alt+F10** pular.
- **Ctrl + clique esquerdo no ícone:** abrir o cartão para marcar/desmarcar e ver as fotos do local dentro do overlay, com Anterior/Próxima. Segurar Ctrl revela os itens já pegos em cinza. [Como funcionam as fotos](docs/MARKER_HINTS.md).

O painel abre como janela independente e pode ser recolhido em um botão animado. Categorias têm ícones, busca e contadores; Recursos reúne seis subgrupos recolhíveis, com nomes e aliases em português (ver [revisão do catálogo](docs/LOCALIZATION.md)); o botão de camadas seleciona mapas/andares. AppSample é a única fonte operacional. A seleção usa seus mapas e camadas nativos; não há divisão por nações inferida de outro catálogo. Referências pessoais ficam fora do executável. Mapas sem referência válida não recebem ícones de demonstração.

[Estado e aceite](docs/REBUILD.md) · [Cobertura efetiva](docs/REGIONAL_COVERAGE.md)

## Desempenho

Em **Ajustes → Desempenho**, **Leve** é o padrão: carrega o entorno sob demanda e pode precisar recuperar a localização após viagens longas. **Global** mantém prontas as referências do mapa escolhido e suas camadas; consome mais memória e pode aumentar CPU e tempo de carregamento. Em seleção automática, Global prepara apenas o mapa identificado. A troca dispensa reinício; se faltar memória no Global, o aplicativo retorna ao Leve.

[Como foi medido e o que falta validar](docs/PERFORMANCE.md). Os índices gerados são cache local descartável; as referências originais e o progresso são preservados.

## Desenvolvimento

```powershell
python -m pip install -r requirements.txt
python src/app.py
# Após instalar o pacote: hexenmap
python -m pytest -q
python -m pip install pyinstaller
python scripts/build_exe.py
```

Dados e referências podem ser verificados sem abrir a interface com `python src/app.py --diagnose`. O progresso antigo é preservado em `userData`; os dados reais usam IDs próprios para não confundir itens de demonstração com coletáveis reais.

O aplicativo usa captura de tela e uma janela transparente do Windows. Não lê memória do jogo nem envia comandos. Genshin Impact pertence à HoYoverse; este projeto é independente. Código original sob MIT; dados comunitários mantêm a licença de sua fonte.
