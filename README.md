# Hexen Map

**Português (Brasil)** · [English](README.en.md)

[![Como Usar (PT)](https://img.shields.io/badge/📖_Guia-Como_Usar_(PT)-007acc?style=flat-square)](HOW_TO_USE.md)
[![How to Use (EN)](https://img.shields.io/badge/📘_Guide-How_to_Use_(EN)-2ea44f?style=flat-square)](HOW_TO_USE.en.md)
[![Segurança / Security](https://img.shields.io/badge/🛡️_Segurança-Security_Policy-orange?style=flat-square)](SECURITY.md)
[![Roadmap](https://img.shields.io/badge/🗺️_Roadmap-Em_Desenvolvimento-8a2be2?style=flat-square)](#-roadmap--próximos-recursos-em-desenvolvimento)

### Seu progresso do AppSample, nos mapas do jogo.

Explore o **Genshin Impact** com pins sobre o minimapa e o mapa M, acompanhe suas coletas e aproveite o progresso que você já marcou no AppSample. Escolha os itens no painel, recolha a janela e continue jogando.

**Windows 10/11 · Overlay externo · 2.0.0 · Versão de teste**

## O que o Hexen Map oferece

| Recurso | Como ajuda na exploração |
| --- | --- |
| **Pins no minimapa e no mapa M** | Mostra os itens selecionados sobre os mapas nativos, acompanhando o alinhamento reconhecido na tela. |
| **AutoMark de baús · Beta** | Combina sinais de abertura e recompensas para registrar um baú próximo quando a associação é confiável. |
| **Importação do AppSample** | Aproveita seus coletados com prévia, mesclagem e backup, sem precisar marcar tudo novamente. |
| **Português e inglês** | Interface, catálogo, inicialização e instalador nos dois idiomas. A busca aceita nomes e aliases; categorias ainda não identificadas ficam sinalizadas. |
| **Fotos dos pontos** | Clique na foto do cartão para ampliar, usar zoom e arrastar a imagem. |
| **Painel independente** | Pode ser movido, redimensionado pelas bordas e recolhido. Em Ajustes, aumente textos e controles para 125% ou 150%. |
| **Mapa global e áreas separadas** | O planetinha permite consultar Teyvat, os seis mapas permanentes separados e suas camadas instaladas. Zoom, fotos, filtros e coletas são compartilhados; a navegação é independente do rastreamento. |

O aplicativo usa reconhecimento de imagem externo. Não lê memória do jogo, não injeta código e não controla o personagem. O reconhecimento pode perder o alinhamento; nessas situações, os pins são ocultados enquanto a posição é recuperada.

## 🗺️ Roadmap — Próximos Recursos em Desenvolvimento

- 🌿 **Rotas de Farm Guiadas:** Visualização sequencial de rotas para materiais de ascensão, baús/desafios por região e rotas diárias de artefatos (1★ e 2★) com avanço automático pelo overlay.
- ⏳ **Timers de Reset em Tempo Real:** Temporizadores de respawn para especialidades e flores locais (48h), minérios (24h/48h/72h), chefes de mundo (3 min) e reset diário oficial do servidor (04:00).
- 🌐 **Sincronização com o Mapa Oficial HoYoLAB:** Importação passiva e segura de baús, óculos e desafios diretamente da sua conta oficial da HoYoverse.
- 🕳️ **Correção dos Mapas Subterrâneos:** Calibração de coordenadas Z e alinhamento em áreas com múltiplos andares (Sumeru, Despenhadeiro/Chasm, Enkanomiya e Mar do Passado), reduzindo bugs na troca de camadas.

## Começar a jogar

**Instalador (teste local):** execute `HexenMap-VERSAO-Setup-x64.exe`. Depois procure **Hexen Map** no menu Iniciar. O pedido de administrador vem antes da animação; depois o launcher verifica atualizações e abre o aplicativo automaticamente, herdando a permissão. Coletas e configurações ficam salvas no seu PC e são preservadas nas atualizações, reinstalações e desinstalação. [Instalação, atualização e recuperação](docs/UPDATES.md).

1. Extraia o **pacote portátil completo** em uma pasta fixa, preservando `userData`.
2. Abra **HexenMap.exe**. Aceite a solicitação de administrador quando necessária para interagir com o jogo elevado.
3. Use o Genshin em **janela ou sem bordas**. Escolha o mapa, a camada e os itens desejados no painel.
4. Volte ao jogo. Use **F8** para recolher ou reabrir o painel.

**O pacote pronto não exige Python nem Node.js.** Clonar o repositório ou copiar somente o `.exe` não instala os pacotes pessoais de mapas, imagens e referências. A cobertura disponível depende dos arquivos presentes na instalação.

## Controles

| Controle padrão | Ação |
| --- | --- |
| **F8** | Abrir/recolher o painel. |
| **Ctrl+Alt+F12** | Mostrar/ocultar os pins. |
| **Ctrl + clique no pin** | Abrir o cartão para marcar/desmarcar e consultar fotos. |
| **Segurar Ctrl** | Revelar itens já coletados em cinza. |
| **F9** | Confirmar uma coleta próxima ou escolher entre candidatos. |
| **F10** | Desfazer a última coleta da sessão. |

Em **Ajustes → Idioma / Language**, escolha **Português (Brasil)** ou **English** e reabra o aplicativo para aplicar. O instalador também permite escolher o idioma. A preferência é compartilhada entre perfis e preservada nas atualizações automáticas.

Os atalhos são configuráveis nos **Ajustes**. Suas opções ficam em seções recolhíveis: perfis, painel e compartilhamento, coletados do AppSample, atalhos e diagnóstico. O AutoMark fica acima do rodapé do painel principal. O controle de compartilhamento define se o overlay aparece nas capturas; ele não desliga o reconhecimento.

A tradução da interface não altera o idioma do Genshin. O **AutoMark beta** também usa pares de ícones de recompensa, sem depender dos textos do jogo. As referências textuais em português continuam como alternativa; o funcionamento com HUD em inglês foi confirmado em teste local.

## Mapas e troca automática

A expansão em validação local inclui **Enkanomiya, Despenhadeiro subterrâneo,
Mar das Eras Passadas, Montanha Sagrada Antiga, Templo do Espaço e Lua Gélida**,
além de Teyvat. O seletor **Automático · Detectar mapa** procura a nova área pelo
minimapa ou pelo mapa M quando a localização atual é perdida. Também é possível
fixar um mapa/camada manualmente. Durante a identificação, não são exibidos pins
sem localização válida.

O mapa global do planetinha abre na área reconhecida ou na última consultada.
Você pode navegar por outros mapas sem mudar o rastreamento do jogo; **Área atual**
retorna ao contexto reconhecido. As 44 camadas próprias dos mapas separados têm
imagens e filtros próprios. A expansão geral das cavernas de Teyvat e mapas de
eventos não faz parte desta etapa.

Os recursos ficam instalados para uso offline e são carregados sob demanda.
A verificação técnica não substitui a validação dentro do jogo: esta expansão
permanece uma compilação local de teste antes da próxima release.

## Traga seus coletados do AppSample

A extensão de teste **Hexen Map Exporter**, para Chrome e Edge, captura os IDs de progresso carregados pelo próprio site. A exportação normal dispensa F12.

1. Extraia o ZIP da extensão e carregue a pasta **HexenMapExporter** em `chrome://extensions` ou `edge://extensions`, usando **Modo do desenvolvedor → Carregar sem compactação**.
2. Abra o AppSample conectado à sua conta. Na extensão, clique em **Atualizar leitura** e confira **Progresso detectado** após a página carregar.
3. Escolha como trazer os dados:

| Opção | Fluxo |
| --- | --- |
| **Enviar ao Hexen Map** | Ative uma vez **Ajustes → Coletados do AppSample → Ativar conexão com a extensão**. Com `HexenMapBridge.exe` junto do aplicativo, o botão encaminha os IDs e abre a prévia no Hexen Map. |
| **Baixar JSON** | Salve o arquivo e use **Importar arquivo de coletados** nos Ajustes do aplicativo. Não exige ativar o conector. |

Confira a prévia e confirme a mesclagem. O progresso existente é preservado com backup; repetir a mesma importação não duplica coletas. IDs sem correspondência comprovada não são associados por aproximação. Cancelar a prévia não aplica coletas.

O envio direto usa **Native Messaging**, por ação explícita, sem servidor ou localhost. A extensão não lê cookies, senhas ou tokens e não modifica marcações no site. Não há sincronização automática ou bidirecional. Após trocar de conta ou alterar coletados no AppSample, atualize a leitura. Ao migrar da extensão 0.1.x, desative a antiga antes de instalar a nova.

[Instalação ilustrada e permissões](docs/EXPORTER_INSTALL.html) · [Guia de importação](docs/APPSAMPLE_IMPORT.md)

## AutoMark: ajuda automática, com confirmação conservadora

O **AutoMark é beta e vem desligado**. Depende de referências visuais qualificadas na instalação e combina sinais de interação, recompensas e posição para associar a abertura a um único baú próximo.

Uma posição incerta ou vários candidatos não autorizam uma coleta automática. A confirmação manual continua disponível, e **F10** desfaz a última marcação da sessão. A validação real ainda não cobre todas as raridades, fundos, resoluções e idiomas.

## Cobertura, desempenho e estado atual

- **Mapas e camadas:** AppSample é a única fonte operacional de marcadores e referências de terreno. Mapas sem referência válida ficam indisponíveis. Dados importados não equivalem a cobertura integral testada no jogo.
- **Progresso:** fica em `userData`, junto das preferências e dos pacotes pessoais. Preserve essa pasta e seus backups ao atualizar.
- **Reposição:** itens permanentes não expiram. Recursos sem regra qualificada mostram **Reposição não confirmada**; não há temporizador universal.
- **Modo Leve:** padrão, carrega referências próximas sob demanda. Viagens longas podem exigir breve recuperação.
- **Modo Global:** prepara o mapa e as camadas selecionadas. Consome mais memória e pode aumentar CPU e carregamento. Não carrega todos os mapas instalados; falha de memória retorna ao Leve.

**O que já foi conferido:** exportação real no Chrome com 3.755 IDs únicos e validação do arquivo pelo importador. O envio nativo completo pelo navegador e a compatibilidade real no Edge continuam pendentes. Não afirmamos vantagem de precisão, estabilidade ou consumo sobre outros overlays sem comparação controlada.

[Estado do projeto](docs/REBUILD.md) · [Cobertura](docs/REGIONAL_COVERAGE.md) · [Estabilidade](docs/STABILITY.md) · [Desempenho](docs/PERFORMANCE.md) · [Testes do exportador](docs/EXPORTER_TEST_REPORT.md)

<details>
<summary><strong>Desenvolvimento e builds</strong></summary>

Use uma versão de Python compatível com `pyproject.toml` e execute a partir da raiz:

```powershell
python -m pip install -r requirements.txt
python src/app.py
python src/app.py --diagnose
python -m pytest -q
```

Os testes JavaScript da extensão também precisam de Node.js no ambiente de desenvolvimento.

```powershell
python -m pip install pyinstaller
python scripts/build_release.py
python scripts/package_exporter.py
```

O pacote atual fica em `dist/atual`, com versão no nome do ZIP e da pasta. Extraia o ZIP completo; não mova só o executável para uma pasta vazia. Entregas anteriores ficam em `dist/arquivo`. A extensão separada fica em `dist/extensoes/<versão>`. Carregue a pasta gerada; a pasta-fonte depende do empacotador para incluir o núcleo compartilhado.

`scripts/build_release.py` gera os executáveis em `build/release-staging` e chama `scripts/package_portable.py` para montar o portátil com os pacotes pessoais conferidos. Não inclui progresso pessoal, não baixa nem licencia dados ausentes. Uma versão já entregue não é sobrescrita silenciosamente.

[Catálogo em português](docs/LOCALIZATION.md) · [Origem e cache das fotos](docs/MARKER_HINTS.md)

</details>

## Segurança, Transparência e Termos de Uso

- **Código Aberto e Auditável:** O código-fonte é 100% aberto. Não há leitura de memória do jogo (`ReadProcessMemory`), injeção de DLLs ou envio de dados confidenciais.
- **Risco de Jogo / Anti-Cheat:** Por operar como ferramenta externa de terceiros, a desenvolvedora (HoYoverse) não homologa oficialmente o aplicativo. O funcionamento é por visão computacional, mas o uso é de responsabilidade de cada jogador.
- **Alertas de Antivírus:** Executáveis empacotados via PyInstaller sem assinatura comercial podem gerar falsos positivos heurísticos. O aplicativo pode ser executado diretamente em Python via terminal.
- Consulte todos os detalhes e esclarecimentos em nossa [**Política de Segurança (SECURITY.md)**](SECURITY.md) e no [**Guia de Uso e Compilação (HOW_TO_USE.md)**](HOW_TO_USE.md).

## Créditos e licença

Hexen Map é um projeto independente, sem afiliação com a HoYoverse ou o AppSample. Genshin Impact pertence à HoYoverse. O código original está sob [licença MIT](LICENSE); imagens, contribuições e dados de terceiros mantêm suas próprias condições de uso. Os pacotes pessoais ficam fora do Git; a licença do código não concede autorização para redistribuí-los.
