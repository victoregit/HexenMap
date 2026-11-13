# Política de Segurança, Integridade e Termos de Uso / Security & Safety Policy

**[Português](#versão-em-português)** · **[English](#english-version)**

---

<a name="versão-em-português"></a>
## Versão em Português

> **Transparência em primeiro lugar:** Este documento detalha a confiabilidade técnica do código-fonte do **Hexen Map**, o posicionamento franco em relação às regras da desenvolvedora do jogo (HoYoverse) e a questão dos alertas de antivírus.

### 1. Confiabilidade e Segurança do Código-Fonte (100% Auditável)

O Hexen Map é um software de código aberto (*open source*). Qualquer desenvolvedor, jogador ou pesquisador pode inspecionar cada arquivo deste repositório para comprovar:

- **Sem Malware ou Spyware:** Não há trojans, backdoors, mineradores de criptomoeda ou rotinas maliciosas de qualquer tipo.
- **Privacidade Completa:** Não há envio de telemetria oculta, webhooks (Discord/Telegram), captura de dados confidenciais ou tráfego de rede em segundo plano. Os únicos acessos de rede são para checar versões públicas no GitHub e o envio opcional de formulário de suporte/feedback pelo usuário.
- **Seus Dados Ficam no seu PC:** Saves de exploração, fotos em cache e configurações ficam armazenados localmente na pasta `%LOCALAPPDATA%\HexenMap\state`.
- **Extensão do AppSample:** A integração opcional do navegador apenas lê IDs numéricos públicos de marcações já visíveis na sua página do mapa, sem acessar senhas, cookies de sessão ou credenciais de conta.

### 2. Risco de Jogo e Termos de Uso (Seja Franco: Existe Risco?)

#### Como o Hexen Map opera:
- **NÃO lê a memória RAM do jogo** (não usa `OpenProcess`, `ReadProcessMemory`, `WriteProcessMemory`).
- **NÃO injeta DLLs nem modifica arquivos do jogo** (não usa `VirtualAllocEx`, `CreateRemoteThread` nem hooks internos).
- **NÃO automatiza comandos ou simula bot** (não envia inputs simulados de teclado ou mouse para mover o personagem ou interagir).
- Funciona exclusivamente por **visão computacional externa** através de APIs legítimas de captura de tela do Windows (`Windows.Graphics.Capture` / `BitBlt`) e projeta uma janela de overlay transparente sobreposta na tela.

#### Sobre Banimentos e Termos de Serviço da HoYoverse:
> [!WARNING]
> **O uso de qualquer software de terceiros junto com o Genshin Impact envolve uma área cinzenta nos Termos de Serviço da HoYoverse.**
> 
> Embora o Hexen Map não faça injeção de DLL nem alteração de memória (diferente de cheats ou hacks convencionais), o sistema anti-cheat proprietário da HoYoverse (**mhyprot2 / HoYoKProtect**) monitora processos rodando no sistema, captura de janelas e ganchos de teclado/mouse no Windows.
> 
> A HoYoverse **não aprova e nem homologa oficialmente nenhum software externo de terceiros**. Por isso:
> - **Não existe "garantia de 0% de risco"** ao utilizar qualquer ferramenta externa sobreposta ao jogo.
> - O uso é de responsabilidade de cada jogador.
> - Se você busca risco zero absoluto de questionamento pela empresa, recomendamos utilizar o mapa interativo em um segundo monitor, no celular ou no navegador com Alt+Tab.

### 3. Falsos Positivos de Antivírus (PyInstaller)

Os arquivos executáveis (`.exe`) disponibilizados na aba de Releases são compilados a partir deste código Python utilizando a ferramenta **PyInstaller**.

- **Por que alguns antivírus alertam?**  
  Binários empacotados por PyInstaller sem um certificado digital corporativo pago (EV Code Signing) são frequentemente marcados como *falso positivo* por motores heurísticos de antivírus (como Windows Defender, VirusTotal, etc.), pois o PyInstaller extrai interpretadores e bibliotecas dinâmicas temporariamente na pasta `%TEMP%`.
- **Como executar com 100% de confiança:**  
  Você não precisa rodar o executável pronto se não quiser. Como o projeto é open source, você pode clonar o repositório e executar diretamente em Python:
  ```powershell
  python -m pip install -r requirements.txt
  python src/app.py
  ```

---

<a name="english-version"></a>
## English Version

> **Transparency First:** This document details the technical trustworthiness of **Hexen Map's** source code, our straightforward stance regarding the game developer's (HoYoverse) Terms of Service, and technical explanations regarding antivirus alerts.

### 1. Code Trustworthiness & Safety (100% Auditable)

Hexen Map is completely free and open-source software. Any developer, player, or security researcher is encouraged to inspect every single line of code in this repository:

- **No Malware or Spyware:** Absolutely no trojans, backdoors, cryptocurrency miners, or malicious routines.
- **Complete Privacy:** No hidden telemetry, no Discord/Telegram webhooks, no scraping of private information, and no background tracking. The only network requests made are checking for public GitHub releases and sending optional user-triggered support/feedback emails.
- **Your Data Stays on Your Machine:** Exploration saves, cached images, and preferences are stored strictly in your local app data folder (`%LOCALAPPDATA%\HexenMap\state`).
- **AppSample Browser Extension:** The optional browser companion strictly reads public numeric marker IDs already rendered on your active AppSample web page; it never accesses passwords, authentication tokens, session cookies, or account credentials.

### 2. Game Integrity & Terms of Service (Being Honest: Is There a Risk?)

#### How Hexen Map Operates:
- **Does NOT read game process memory** (no `OpenProcess`, `ReadProcessMemory`, or `WriteProcessMemory`).
- **Does NOT inject DLLs or modify game files** (no `VirtualAllocEx`, `CreateRemoteThread`, or internal hooking).
- **Does NOT simulate gameplay inputs or bots** (no automated keyboard or mouse strokes simulating player movement or combat).
- Operates purely via **external computer vision** through standard Windows screen capture APIs (`Windows.Graphics.Capture` / `BitBlt`) and renders a transparent overlay window above the game.

#### Regarding Bans and HoYoverse Terms of Service:
> [!WARNING]
> **Using any third-party software alongside Genshin Impact falls into a gray area under HoYoverse's Terms of Service.**
> 
> Even though Hexen Map does not perform memory injection or file alteration (unlike malicious game cheats), HoYoverse's proprietary anti-cheat engine (**mhyprot2 / HoYoKProtect**) monitors running background processes, window capture activities, and system-wide input hooks.
> 
> HoYoverse **does not officially endorse, approve, or whitelist any third-party external tools**. Therefore:
> - **There is NO guarantee of 0% risk** when running any external overlay tool alongside the game.
> - Usage is entirely at your own discretion and responsibility.
> - If you want absolute zero risk of account flags, we strongly recommend using the interactive map on a secondary monitor, smartphone, or via Alt+Tab in your web browser.

### 3. Antivirus False Positives (PyInstaller)

The standalone executable files (`.exe`) distributed in GitHub Releases are packaged from this exact Python source code using **PyInstaller**.

- **Why do some antivirus engines flag it?**  
  Standalone Python binaries without an expensive corporate Code Signing certificate are frequently flagged as *false positives* by heuristic antivirus scanners (Windows Defender, VirusTotal engines, etc.). This occurs because PyInstaller extracts libraries and interpreters temporarily into `%TEMP%`, a behavioral pattern shared by generic packers.
- **How to run with 100% confidence:**  
  You do not need to download or run the precompiled `.exe` file. Because this project is fully open source, you can audit the code and run it directly with Python:
  ```powershell
  python -m pip install -r requirements.txt
  python src/app.py
  ```
