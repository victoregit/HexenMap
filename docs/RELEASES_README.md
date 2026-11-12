<div align="center">

# ✦ Hexen Map

### Explore mais. Troque menos de janela. / Explore more. Switch windows less.

[![Download](https://img.shields.io/badge/Download-Windows%2010%2F11-ae97e8?style=for-the-badge&logo=windows)](https://github.com/victoregit/HexenMap-Releases/releases/latest)
[![Version](https://img.shields.io/github/v/release/victoregit/HexenMap-Releases?style=for-the-badge&label=Latest&color=788cde)](https://github.com/victoregit/HexenMap-Releases/releases/latest)

**Marcadores no jogo · Modo streamer · AutoMark beta · Fotos dos pontos**  
**In-game markers · Streamer mode · AutoMark beta · Location photos**

</div>

[Português](#português) · [English](#english) · [Download / Releases](https://github.com/victoregit/HexenMap-Releases/releases/latest)

## Português

**Seu companheiro de exploração no Genshin Impact.** Hexen Map mostra marcadores sobre o minimapa e o mapa do jogo, ajuda a acompanhar coletados, exibe fotos dos pontos e permite importar progresso do AppSample. Este repositório distribui os instaladores e as atualizações para Windows 10/11 de 64 bits.

### Tudo o que você precisa, mais perto da exploração

Chega de interromper cada rota para conferir onde está o próximo item. O Hexen Map reúne orientação visual, fotos e controle de coletas em uma camada sobre o jogo, para você manter o foco na aventura.

| ✨ Recurso | O que você ganha |
| --- | --- |
| **📍 Pins no minimapa e no mapa M** | Veja os itens selecionados sobre os mapas do jogo e reduza as idas ao navegador. |
| **🎥 Modo streamer** | Escolha se o overlay aparece nas capturas e no compartilhamento de tela, mantendo a ajuda visível para você. A compatibilidade depende do método de captura; teste antes da live. |
| **⚡ AutoMark de baús · Beta** | Ative acima do rodapé, acompanhe a sincronização e use ↻ para sincronizar novamente. Registra um baú próximo quando abertura, recompensas e posição permitem uma associação confiável. Beta, desligado por padrão. |
| **🖼️ Fotos do local** | Está difícil encontrar o ponto? Abra o cartão, consulte as fotos e amplie com zoom para enxergar os detalhes. |
| **🔄 Importação + extensão AppSample** | O Hexen Map Exporter ajuda a exportar seus coletados do navegador, sem F12. Importe com prévia e continue de onde parou. Exige suporte a extensões do Chrome. |
| **🌍 Mapa global e áreas separadas** | Consulte Teyvat e seis mapas permanentes separados, com 44 camadas próprias, zoom, filtros, fotos e coletas. A navegação não altera o rastreamento do jogo. |
| **📚 Catálogo organizado** | Busque itens, filtre categorias e mantenha na tela o que importa para a sua rota. Interface e catálogo em português e inglês, com aliases de busca. |
| **🎛️ Painel do seu jeito** | Fixe o painel ao Genshin ou use uma janela independente. Mova, redimensione, recolha e ajuste a escala dos controles. |
| **🚀 Abra e jogue** | O launcher verifica atualizações e segue para o app sozinho. Sem instalar Python ou baixar a pasta inteira a cada versão. |
| **💾 Seu progresso continua seu** | Coletas e preferências ficam fora da pasta do programa e são preservadas nas atualizações e reinstalações. Perfis locais separam contas; mantenha backups independentes. |

> **Joga e transmite?** Use as referências na sua tela e escolha o que vai para a captura. **Já explora pelo AppSample?** Importe seus coletados para continuar de onde parou.

### Funções e limites atuais · 2.0.1

- **Mapas:** Teyvat, Enkanomiya, Despenhadeiro subterrâneo, Mar das Eras Passadas, Montanha Sagrada Antiga, Templo do Espaço e Lua Gélida. Use **Automático · Detectar mapa** ou fixe mapa/camada nos Ajustes. A cobertura depende dos recursos instalados; mapas temporários e a expansão geral das cavernas de Teyvat ficam fora desta versão.
- **Sem bússola ou busca guiada:** os pins mostram os itens selecionados nos mapas do jogo. Não há navegação por alvo nem atalhos de farm.
- **Controles padrão:** F8 abre/recolhe o painel; Ctrl+Alt+F12 mostra/oculta os pins; Ctrl + clique abre o cartão; segurar Ctrl revela coletados em cinza; F9 confirma uma coleta próxima ou apresenta candidatos; F10 desfaz a última coleta da sessão. Os quatro atalhos de teclado são configuráveis nos Ajustes.
- **AutoMark:** beta e desligado por padrão. Requer o jogo em foco, referências qualificadas, posição confiável e associação sem ambiguidade. Também confirma recompensas por pares de ícones, sem depender do texto em português ou inglês. A sincronização inicial não garante uma coleta; o assistente de calibração pessoal ainda não está incluído.
- **Recursos e reposição:** referências e memória são gerenciadas automaticamente, sem seletor Leve/Global. Itens permanentes não expiram; recursos sem regra qualificada mostram **Reposição não confirmada**.
- **Idioma:** português e inglês no aplicativo e instalador. Altere em **Ajustes → Idioma / Language** e reabra o app.
- **Tela e diagnóstico:** prefira janela ou sem bordas se o overlay não aparecer em tela cheia. Diagnóstico permite recarregar o reconhecimento e gravar o canto do minimapa por até 20 segundos/50 MiB, com exportação manual; nenhuma captura é enviada automaticamente. A bandeja do Windows permite reabrir o painel ou encerrar.
- **Correção 2.0.1:** revalidação do minimapa por referências nativas para reduzir desaparecimentos intermitentes. A validação real da estabilidade continua pendente; não há garantia de eliminar todas as piscadas.

### Comece em poucos passos

1. Baixe o instalador `.exe` na [última release](https://github.com/victoregit/HexenMap-Releases/releases/latest), instale e procure **Hexen Map** no menu Iniciar.
2. Autorize o pedido de administrador. Ele vem antes do launcher porque o overlay precisa interagir com a janela do jogo quando ela está elevada.
3. O launcher verifica atualizações, instala uma versão nova quando disponível e abre o aplicativo automaticamente. Sem conexão, tenta abrir a versão instalada.
4. Escolha os itens no painel. Com o mapa aberto, **Ctrl + clique** em um marcador abre seu cartão com fotos e a opção de marcar/desmarcar a coleta.

O alinhamento usa captura de imagem e reconhecimento visual: o aplicativo não lê a memória do jogo, não injeta código e não controla o personagem. Isso permite desenhar uma camada externa sobre os mapas já exibidos pelo jogo.

### 🧩 Hexen Map Exporter: traga seu progresso do navegador

A extensão **Hexen Map Exporter** ajuda a exportar os itens já marcados no AppSample, sem precisar usar o console do navegador. No aplicativo, vá a **Ajustes → Coletados do AppSample → Abrir pasta da extensão** e carregue a pasta pelo modo de desenvolvedor do navegador. Abra o AppSample conectado à sua conta e use **Atualizar leitura** na extensão.

- **Baixar JSON:** exporte o arquivo e importe pelos Ajustes do Hexen Map.
- **Enviar ao Hexen Map:** ative antes **Ativar conexão com a extensão** nos Ajustes. Confira a prévia e confirme a mesclagem no aplicativo.

> **Compatibilidade:** a extensão é exclusiva de navegadores que aceitam extensões do Chrome/Chromium. Chrome é a referência de uso; a validação real no Edge ainda está pendente. Navegadores sem esse suporte, como Firefox e Safari, não são compatíveis com esta extensão. A conexão direta está preparada para Chrome e Edge; outros navegadores Chromium não têm suporte garantido. Essa restrição é da extensão de exportação, não do overlay.

A extensão não pede sua senha, não lê cookies ou tokens e não modifica seus coletados no AppSample. A exportação é feita quando você solicita; não há sincronização contínua ou bidirecional.

### Seus dados

**A partir da 1.0.1**, coletas e preferências ficam **no seu PC**, em `%LOCALAPPDATA%\HexenMap\state`, fora da pasta do programa. Atualizações e reinstalações usam o mesmo save pessoal; o desinstalador não remove essa pasta. Saves antigos encontrados são migrados com backup. Se você já usava o app e ele pedir para importar um arquivo, selecione o `progress.json` antigo ou um backup, em vez de confirmar um perfil novo. Não há backup em nuvem: mantenha também uma cópia independente. [Correção e recuperação de marcações](https://github.com/victoregit/HexenMap-Releases/releases/tag/v1.0.1).

### Riscos e limites

- Projeto independente, sem afiliação com HoYoverse ou AppSample. Não prometemos risco zero ao usar uma ferramenta de terceiros nem garantia contra medidas do jogo/anticheat.
- O reconhecimento pode perder o alinhamento; cobertura, resolução e idioma influenciam o resultado. **AutoMark continua beta**, vem desligado e pode errar. Confira suas marcações.
- O programa executa com privilégios de administrador. Baixe apenas deste repositório. A build ainda não tem assinatura digital própria; avisos do Windows não devem ser ignorados automaticamente. O `.sha256` permite conferir a integridade do arquivo.
- Mapas, fotos e serviços externos podem mudar ou ficar indisponíveis. Seus conteúdos pertencem aos respectivos autores; a distribuição do aplicativo não transfere direitos sobre eles.

Encontrou um problema? Abra uma [issue](https://github.com/victoregit/HexenMap-Releases/issues) com a versão, resolução e passos para reproduzir. Não envie senhas, cookies, tokens ou arquivos pessoais de progresso.

## English

**Your exploration companion for Genshin Impact.** Hexen Map overlays markers on the minimap and in-game map, tracks collected items, displays location photos, and imports AppSample progress. This repository distributes installers and updates for 64-bit Windows 10/11.

### Keep the tools close and the adventure moving

Stop interrupting every route to look up the next item. Hexen Map brings visual references, location photos, and collection tracking into an overlay, helping you stay focused on exploring.

| ✨ Feature | What it does for you |
| --- | --- |
| **📍 Minimap and in-game map markers** | See selected items over the game's maps and cut down on browser switching. |
| **🎥 Streamer mode** | Choose whether the overlay appears in screen captures and screen sharing while keeping it visible to you. Support depends on the capture method; test your setup before going live. |
| **⚡ Chest AutoMark · Beta** | Enable it above the footer, follow synchronization status and use ↻ to resync. Records a nearby chest when opening, rewards and position support a reliable match. Opt-in beta. |
| **🖼️ Location photos** | Having trouble finding a spot? Open its card, check the photos, and zoom in for the details. |
| **🔄 AppSample import + browser extension** | Hexen Map Exporter helps export collected markers from your browser without developer tools. Review the import and pick up where you left off. Requires Chrome extension support. |
| **🌍 World map and separate areas** | Browse Teyvat and six permanent separate maps with 44 dedicated layers, zoom, filters, photos and progress. Browsing does not change game tracking. |
| **📚 Organized item catalog** | Search and filter categories to show what matters for your route. The interface and catalog support Portuguese and English, including search aliases. |
| **🎛️ A panel that fits your setup** | Attach the panel to Genshin or use an independent window. Move, resize, collapse and scale the controls. |
| **🚀 Launch and play** | The launcher checks for updates and opens the app automatically. No Python installation or repeated full-folder downloads. |
| **💾 Your progress stays yours** | Collected items and preferences live outside the program folder and survive updates and reinstalls. Local profiles separate accounts; keep independent backups. |

> **Playing and streaming?** Keep your references on your screen and choose what goes into the capture. **Already using AppSample?** Import your collected markers and pick up where you left off.

### Current features and limits · 2.0.1

- **Maps:** Teyvat, Enkanomiya, The Chasm: Underground Mines, Sea of Bygone Eras, Ancient Sacred Mountain, Temple of Space and Frost Moon. Use **Automatic · Detect map** or select a fixed map/layer in Settings. Coverage depends on installed resources; temporary maps and a general expansion of Teyvat caves are outside this version.
- **No compass or guided search:** pins display selected items on the in-game maps. Target navigation and farming hotkeys are not available.
- **Default controls:** F8 opens/collapses the panel; Ctrl+Alt+F12 shows/hides pins; Ctrl + click opens a card; holding Ctrl reveals collected items in gray; F9 confirms a nearby collection or presents candidates; F10 undoes the session's last collection. The four keyboard shortcuts are configurable in Settings.
- **AutoMark:** opt-in beta. Requires game focus, qualified references, a reliable position and an unambiguous match. Reward icon pairs also work without relying on Portuguese or English text. Initial synchronization does not guarantee a collection; the personal calibration wizard is not included yet.
- **Resources and respawns:** references and memory are managed automatically, without a Light/Global selector. Permanent items never expire; resources without a qualified rule show **Respawn unconfirmed**.
- **Language:** Portuguese and English in the app and installer. Change **Settings → Idioma / Language** and reopen the app.
- **Display and diagnostics:** try windowed or borderless mode if fullscreen hides the overlay. Diagnostics can reload recognition and record the minimap corner for up to 20 seconds/50 MiB, with manual export; captures are never uploaded automatically. The Windows tray can reopen the panel or exit.
- **2.0.1 fix:** native minimap reference revalidation aims to reduce intermittent marker disappearances. Real gameplay stability validation remains pending; eliminating all flickering is not guaranteed.

### Get started in a few steps

1. Download the `.exe` installer from the [latest release](https://github.com/victoregit/HexenMap-Releases/releases/latest), install it, and find **Hexen Map** in the Start menu.
2. Approve the administrator prompt. It appears before the launcher because the overlay needs to interact with the game window when the game runs elevated.
3. The launcher checks for updates, installs a newer version when available, and opens the app automatically. If offline, it attempts to open the installed version.
4. Select items in the panel. With the map open, **Ctrl + click** a marker to see its photos and mark or unmark it as collected.

Alignment relies on screen capture and visual recognition. The app does not read game memory, inject code, or control your character. It draws an external layer over the maps already displayed by the game.

### 🧩 Hexen Map Exporter: bring your browser progress with you

The **Hexen Map Exporter** extension helps export markers you have already collected on AppSample, without using the browser console. In the app, open **Settings → AppSample collected items → Open extension folder** and load that folder through your browser's developer mode. Open AppSample signed in to your account and use **Refresh reading / Atualizar leitura** in the extension.

- **Download JSON:** export the file and import it through Hexen Map settings.
- **Send to Hexen Map:** first enable **Ativar conexão com a extensão** in settings. Review the preview and confirm the merge in the app.

> **Compatibility:** this extension requires a browser that supports Chrome/Chromium extensions. Chrome is the reference browser; real-world Edge validation is still pending. Browsers without that support, such as Firefox and Safari, are not compatible with this extension. Direct app integration is prepared for Chrome and Edge; other Chromium browsers are not guaranteed to work. This restriction applies to the export extension, not to the overlay.

The extension does not ask for your password, read cookies or tokens, or change collected markers on AppSample. Exports happen at your request; there is no continuous or bidirectional synchronization.

### Your data

**Starting with 1.0.1**, collected items and preferences stay **on your PC**, in `%LOCALAPPDATA%\HexenMap\state`, outside the program folder. Updates and reinstalls use the same personal save; the uninstaller does not remove that folder. Detected older saves are migrated with backups. If you previously used the app and are asked to select a file, choose your old `progress.json` or a backup instead of confirming a new profile. There is no cloud backup: keep an independent copy too. [Save recovery update](https://github.com/victoregit/HexenMap-Releases/releases/tag/v1.0.1).

### Risks and limitations

- Independent project, not affiliated with HoYoverse or AppSample. We do not promise risk-free use of a third-party tool or protection against game/anti-cheat enforcement.
- Visual recognition can lose alignment; coverage, resolution, and language affect results. **AutoMark remains beta**, is disabled by default, and can make mistakes. Review your collected markers.
- The app runs with administrator privileges. Download only from this repository. The build does not yet have its own digital signature; do not automatically dismiss Windows warnings. The `.sha256` file lets you check download integrity.
- Maps, photos, and external services may change or become unavailable. Their content belongs to its respective owners; distributing the app does not transfer those rights.

Found a problem? Open an [issue](https://github.com/victoregit/HexenMap-Releases/issues) with your version, resolution, and reproduction steps. Do not share passwords, cookies, tokens, or personal progress files.
