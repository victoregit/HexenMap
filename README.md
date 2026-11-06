# Genshin Gem Wish

Overlay externo de exploração para os mapas nativos do Genshin Impact, em reconstrução e validação real no Windows.

Abra **GenshinOverlay.exe** ou **Iniciar_Overlay.bat**, selecione o que procurar no painel e volte ao jogo. O aplicativo desenha somente ícones sobre o minimapa e o mapa M; não abre outro mapa nem simula o personagem. Use o jogo em janela ou sem bordas.

- **Ctrl+Alt+F12:** mostrar/ocultar overlay.
- **F9:** marcar o item próximo como coletado; se houver mais de um, selecionar no painel.
- **F10:** desfazer a última coleta da sessão.
- **Ctrl + clique esquerdo no ícone:** abrir o menu para marcar como pego ou desmarcar. Segurar Ctrl revela os itens já pegos em cinza.

Os atalhos são configuráveis. Sem seleção ou localização confiável, nenhum ícone aparece. A cobertura inicial é a superfície de Mondstadt, com posições comunitárias de baús e anemoculi.

**Estado atual:** há integração real e confirmação do usuário de ícones no minimapa. A validação completa de exploração, posições e desempenho ainda está pendente. A instalação local usa um pacote pessoal de referências em `userData/references/mondstadt`; ele não acompanha o executável. Em outro computador, sem referências, o painel informa que elas estão ausentes. Ainda não é uma distribuição pública pronta para abrir e jogar em uma instalação limpa.

[Estado, evidências, limitações e próximos critérios de aceite](docs/REBUILD.md) · [Créditos dos dados comunitários](data/community/mondstadt/NOTICE.md)

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
