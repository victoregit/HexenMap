# Hexen Map

Overlay externo para explorar o **Genshin Impact** com marcadores sobre o minimapa e o mapa M. O painel é independente e recolhível; você escolhe os itens e continua jogando.

**Versão de teste para Windows 10/11.** O reconhecimento visual e o AutoMark continuam em validação. A cobertura depende dos pacotes e referências instalados; dados importados não significam que todos os mapas foram conferidos no jogo.

## Começar a jogar

1. Extraia o pacote portátil completo em uma pasta fixa. Não copie somente o executável: os dados pessoais e as referências ficam em `userData`.
2. Abra **HexenMap.exe** ou **Iniciar_HexenMap.bat**. Se o jogo estiver elevado, aceite a solicitação de administrador para permitir a interação com os pins.
3. Use o Genshin em **janela ou sem bordas**. Escolha o mapa, a camada e as categorias no painel e volte ao jogo.

O pacote portátil inclui o runtime: **não exige Python instalado**. Clonar este repositório não instala os pacotes pessoais de mapas e imagens. Mapas sem referência válida ficam indisponíveis, sem dados de demonstração como substituto.

## Funções e controles

| Controle | Ação padrão |
| --- | --- |
| **F8** | Abrir/recolher o painel; o botão animado pode ser arrastado. |
| **Ctrl+Alt+F12** | Mostrar/ocultar os marcadores. |
| **Ctrl + clique no pin** | Abrir o cartão para marcar/desmarcar e consultar fotos do ponto. |
| **Segurar Ctrl** | Revelar itens coletados em cinza. |
| **F9** | Confirmar o item próximo; diante de ambiguidade, selecionar no painel. |
| **F10** | Desfazer a última coleta da sessão. |

Os atalhos são configuráveis nos Ajustes. Clicar fora do cartão devolve a interação ao jogo. O cartão tem fotos da comunidade AppSample com **Anterior/Próxima**, quando disponíveis; essas consultas exigem internet. Veja [origem, cache e limites das fotos](docs/MARKER_HINTS.md).

O painel reúne busca por itens, ícones, contadores e seleção de mapa/camada. **Recursos** contém seis subgrupos recolhíveis: especialidades locais, plantas e ingredientes, minérios, madeiras, pesca e animais, outros materiais. A busca aceita aliases e nomes sem acentos. [Revisão do catálogo em português](docs/LOCALIZATION.md).

**A bússola, a busca guiada e o alvo amarelo foram retirados.** O fluxo atual mantém os marcadores nos mapas e o AutoMark.

## AutoMark de baús — beta

A opção **Marcar baús automaticamente** é desligada por padrão e depende de referências visuais qualificadas na instalação. Ela combina sinais de interação e recompensas com um candidato próximo identificado sem ambiguidade. Não depende de um alvo destacado.

Diante de posição incerta ou associação ambígua, o aplicativo preserva o progresso e permite confirmação manual. F10 desfaz uma marcação. A beta ainda não tem validação real completa para todas as raridades, fundos, resoluções e idiomas. [Estado e limitações](docs/REBUILD.md) · [Estabilidade e critérios de aceite](docs/STABILITY.md).

## Trazer os coletados do AppSample

A extensão **Hexen Map Exporter 0.2.0**, para Chrome e Edge, lê os IDs de coletados que o próprio AppSample carrega. Não precisa de F12.

1. Extraia o ZIP da extensão e carregue a pasta **HexenMapExporter** em `chrome://extensions` ou `edge://extensions`, usando **Modo do desenvolvedor → Carregar sem compactação**. Ao migrar da 0.1.x, desative a extensão antiga antes de instalar a nova.
2. Abra o AppSample conectado à sua conta. Na extensão, use **Atualizar leitura**, aguarde a página carregar e confira **Progresso detectado**.
3. Escolha uma das formas de importar:
   - **Enviar ao Hexen Map:** no aplicativo atualizado, ative uma vez **Ajustes → Ativar conexão com a extensão**. Mantenha `HexenMapBridge.exe` junto de `HexenMap.exe`. O envio abre o aplicativo, se necessário, e apresenta a prévia para confirmar a mesclagem.
   - **Baixar JSON:** salve o arquivo e use **Ajustes → Importar coletados do AppSample** no aplicativo.

A mesclagem preserva o progresso existente e cria backup. Repetir a mesma importação não duplica coletas; IDs sem correspondência comprovada não são transferidos por aproximação. Cancelar a prévia não aplica coletas.

O envio direto usa **Native Messaging**, somente após o clique, com registro local para o usuário atual do Windows. Não usa servidor ou localhost. A extensão não lê cookies, senhas ou tokens, não altera o AppSample e não sincroniza em segundo plano. Após trocar de conta ou alterar marcações no site, atualize a leitura.

**Validação:** a exportação no Chrome foi conferida com um arquivo de 3.755 IDs únicos. O envio nativo completo e a compatibilidade real no Edge ainda precisam de conferência. Não há sincronização bidirecional.

[Guia ilustrado e permissões](docs/EXPORTER_INSTALL.html) · [Importação e alternativa manual](docs/APPSAMPLE_IMPORT.md) · [Relatório de testes](docs/EXPORTER_TEST_REPORT.md).

## Mapas, progresso e desempenho

AppSample é a única fonte operacional de marcadores e referências de terreno. A seleção usa seus mapas e camadas nativos; não infere nações ou pequenas áreas a partir de outro catálogo. IDs, progresso e preferências ficam em `userData`. Não apague essa pasta ao atualizar; preserve também os backups.

Não existe prazo universal de reposição. Itens permanentes não expiram; recursos sem regra qualificada mostram **Reposição não confirmada**. [Cobertura efetiva](docs/REGIONAL_COVERAGE.md).

Em **Ajustes → Desempenho**, **Leve** é o padrão e carrega referências próximas sob demanda. **Global** prepara o mapa e as camadas selecionadas: consome mais memória e pode aumentar CPU e carregamento. Não carrega automaticamente todos os mapas instalados. A troca dispensa reinício; uma falha de memória no Global retorna ao Leve. [Medições e limitações](docs/PERFORMANCE.md).

## Desenvolvimento e builds

Use Python compatível com `pyproject.toml` e execute a partir da raiz do projeto:

```powershell
python -m pip install -r requirements.txt
python src/app.py
python src/app.py --diagnose
python -m pytest -q
```

Os testes JavaScript da extensão também precisam de Node.js no ambiente de desenvolvimento. Node.js e Python não são necessários para quem recebe os executáveis e o ZIP prontos.

Para gerar os executáveis no Windows e o ZIP da extensão:

```powershell
python -m pip install pyinstaller
python scripts/build_exe.py --build-only
python -m PyInstaller --noconfirm --distpath dist --workpath build/bridge HexenMapBridge.spec
python scripts/package_exporter.py
```

As saídas ficam em `dist`: `HexenMap.exe`, `HexenMapBridge.exe`, a pasta carregável `HexenMapExporter` e seu ZIP versionado. O empacotador incorpora o núcleo compartilhado em cada entrada da extensão; carregue a pasta gerada, não a pasta-fonte incompleta. `scripts/package_portable.py` monta o pacote portátil a partir dos executáveis e dos pacotes pessoais conferidos da instalação; não baixa nem licencia dados ausentes.

## Funcionamento e atribuição

O aplicativo usa captura visual externa e uma janela transparente do Windows. Não lê memória do jogo, não injeta código e não envia comandos ao personagem. Isso descreve a implementação; não é garantia de aprovação pela HoYoverse ou de ausência de penalidades.

Genshin Impact pertence à HoYoverse. Hexen Map é independente e não é uma integração oficial do AppSample. O código original está sob [licença MIT](LICENSE); imagens e dados de terceiros mantêm suas próprias condições de uso. Os pacotes pessoais ficam fora do Git, e sua redistribuição não é presumida pela licença do código.
