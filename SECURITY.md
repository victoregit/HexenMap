# Política de Segurança e Boas Práticas / Security & Transparency Policy

**[Português](#versão-em-português)** · **[English](#english-version)**

---

<a name="versão-em-português"></a>
## Versão em Português

O **Hexen Map** foi desenvolvido com foco em código aberto, privacidade do jogador e integridade do sistema operacional.

### 1. Boas Práticas e Arquitetura do Código

- **Código Aberto e Auditável:** Todo o código-fonte está disponível neste repositório para inspeção pública por qualquer jogador ou desenvolvedor.
- **Privacidade e Dados Locais:** Suas preferências e marcações de exploração são salvas exclusivamente no seu computador (`%LOCALAPPDATA%\HexenMap\state`). Não há envio de telemetria oculta, dados de hardware ou informações confidenciais.
- **Integração com AppSample:** A extensão complementar de navegador realiza leitura passiva apenas dos IDs numéricos públicos já exibidos no mapa, sem solicitar senhas, tokens ou cookies de sessão.
- **Atualizações Oficiais:** As atualizações buscam exclusivamente novas versões e notas de lançamento publicadas no repositório oficial do projeto no GitHub.

### 2. Funcionamento do Overlay e Relação com o Jogo

- **Método Não Invasivo (Visão Computacional Externa):**
  - O aplicativo opera como uma janela externa transparente sobreposta na tela do Windows.
  - Utiliza exclusivamente recursos padrão do Windows (`Windows.Graphics.Capture` e `BitBlt`) para reconhecer elementos visuais do mapa na tela.
  - **Não lê memória RAM do jogo** (`ReadProcessMemory`).
  - **Não injeta DLLs** nem altera arquivos de instalação do jogo.
  - **Não simula ações de jogador** nem automatiza combate ou movimentação (sem automação de inputs).

- **Orientações para o Jogador:**
  - O Hexen Map é uma ferramenta complementar e independente, sem filiação com a HoYoverse.
  - Como a desenvolvedora do jogo não homologa softwares de terceiros de forma oficial, o uso é pessoal e opcional para enriquecer a experiência de exploração.

### 3. Execução e Verificação Técnica

- **Executáveis Empacotados:**  
  Os arquivos executáveis (`.exe`) disponíveis nas Releases são gerados diretamente do código Python através do PyInstaller. Softwares empacotados sem certificados comerciais caros podem ocasionalmente ser sinalizados por mecanismos heurísticos de antivírus como falso positivo, devido ao processo padrão de extração temporária de bibliotecas.
- **Execução Direta via Código-Fonte:**  
  Caso prefira executar sem o binário compilado, você pode rodar o projeto diretamente com Python:
  ```powershell
  python -m pip install -r requirements.txt
  python src/app.py
  ```

---

<a name="english-version"></a>
## English Version

**Hexen Map** is designed with a strong focus on open-source principles, player privacy, and operating system safety.

### 1. Engineering Best Practices & Architecture

- **Open Source & Auditable:** All source code is openly hosted in this repository for review by any player or developer.
- **Privacy & Local Data Storage:** Your preferences and exploration progress are stored locally on your PC (`%LOCALAPPDATA%\HexenMap\state`). No hidden telemetry, hardware logging, or private data collection is performed.
- **AppSample Integration:** The optional companion browser extension passively reads only the public numeric marker IDs displayed on your map page, without requesting passwords, cookies, or authentication tokens.
- **Official Updates:** The update mechanism retrieves only verified release assets published on the project's official GitHub repository.

### 2. How the Overlay Works

- **Non-Invasive Architecture (External Computer Vision):**
  - The application functions as an external transparent overlay window on Windows.
  - Operates purely via standard Windows graphics capture APIs (`Windows.Graphics.Capture` and `BitBlt`) to align map markers.
  - **Does NOT read game memory** (`ReadProcessMemory`).
  - **Does NOT inject DLLs** or alter game installation files.
  - **Does NOT automate gameplay** (no synthetic combat or bot input simulation).

- **Player Guidance:**
  - Hexen Map is an independent community tool, unaffiliated with HoYoverse.
  - As third-party tools are not officially whitelisted by game publishers, usage is optional and designed to enhance map exploration convenience.

### 3. Execution & Verification

- **Packaged Executables:**  
  The `.exe` binaries provided in GitHub Releases are built directly from this Python repository using PyInstaller. Unsigned standalone Python executables may occasionally trigger heuristic antivirus false flags due to temporary library extraction routines.
- **Running Directly from Source:**  
  If preferred, users can inspect every file and launch the application directly using Python:
  ```powershell
  python -m pip install -r requirements.txt
  python src/app.py
  ```
