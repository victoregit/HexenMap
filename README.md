# Genshin Gem Wish

Overlay externo de exploração para os mapas nativos do Genshin Impact, em reconstrução e validação real no Windows.

Abra **GenshinOverlay.exe** ou **Iniciar_Overlay.bat**, selecione o que procurar no painel e volte ao jogo. O aplicativo desenha somente ícones sobre o minimapa e o mapa M; não abre outro mapa nem simula o personagem. Use o jogo em janela ou sem bordas.

- **F8:** mostrar/minimizar o painel independente ou abrir/recolher o painel fixado (configurável).
- **Ctrl+Alt+F12:** mostrar/ocultar overlay.
- **F9:** marcar o item próximo como coletado; se houver mais de um, selecionar no painel.
- **F10:** desfazer a última coleta da sessão.
- **Ctrl + clique esquerdo no ícone:** abrir o menu para marcar como pego ou desmarcar. Segurar Ctrl revela os itens já pegos em cinza.

O painel abre como janela independente, movível para fora do jogo. “Fixar ao jogo” e “Destacar” alternam os modos. Abrir o executável novamente reutiliza a instância existente. O painel compacto tem lista virtual com ícones e contadores, seções recolhíveis com seleção por grupo, busca por itens e ajustes na engrenagem. A troca de nação prepara os dados fora da interface e prioriza a última escolha. Traduções restantes ficam identificadas em uma seção própria. O seletor de nação mostra os emblemas coloridos ao lado dos nomes. O botão de camadas abre a seleção de mapas/andares. Não há busca por áreas. Os atalhos são configuráveis. Sem seleção ou localização confiável, nenhum ícone aparece. A expansão importou 126.200 marcadores em oito regiões da fonte, com seleção de nação e camadas, categorias e reposição estimada por ponto. Os mapas novos ainda dependem da validação no jogo; dados importados não equivalem a cobertura aprovada.

**Estado atual:** há integração real e confirmação do usuário de ícones no minimapa. A validação completa de exploração, posições e desempenho ainda está pendente. As referências pessoais ficam em `userData/references` e não acompanham o executável. O catálogo anterior de Mondstadt permanece disponível para compatibilidade. Na nova seleção, um mapa sem referência compatível fica sem ícones. Em outro computador, sem referências, o painel informa que elas estão ausentes. Ainda não é uma distribuição pública pronta para abrir e jogar em uma instalação limpa.

[Estado, evidências e critérios de aceite](docs/REBUILD.md) · [Inventário regional e reposição](docs/REGIONAL_COVERAGE.md) · [Créditos Kongying Tavern](data/community/kongying/NOTICE.md) · [Créditos do catálogo anterior](data/community/mondstadt/NOTICE.md)

## Desenvolvimento

```powershell
python -m pip install -r requirements.txt
python src/app.py
python -m pytest -q
python -m pip install pyinstaller
python scripts/build_exe.py
```

Dados e referências podem ser verificados sem abrir a interface com `python src/app.py --diagnose`. O progresso antigo é preservado em `userData`; os dados reais usam IDs próprios para não confundir itens de demonstração com coletáveis reais.

O aplicativo usa captura de tela e uma janela transparente do Windows. Não lê memória do jogo nem envia comandos. Genshin Impact pertence à HoYoverse; este projeto é independente. Código original sob MIT; dados comunitários mantêm a licença de sua fonte.
