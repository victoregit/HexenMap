# Política de Segurança, Integridade e Termos de Uso / Security Policy

> **Transparência em primeiro lugar:** Este documento detalha a confiabilidade técnica do código-fonte do **Hexen Map**, o posicionamento em relação às regras da desenvolvedora do jogo (HoYoverse) e a questão dos alertas de antivírus.

---

## 1. Confiabilidade e Segurança do Código-Fonte (100% Auditável)

O Hexen Map é um software de código aberto (*open source*). Qualquer desenvolvedor ou jogador pode inspecionar cada arquivo deste repositório para comprovar:

- **Sem Malware ou Spyware:** Não há trojans, backdoors, mineradores ou qualquer rotina maliciosa.
- **Privacidade Completa:** Não há envio de telemetria oculta, webhooks (Discord/Telegram), captura de dados confidenciais ou tráfego em segundo plano. Os únicos acessos de rede são para checar versões no GitHub e o formulário opcional de feedback/suporte via e-mail.
- **Seus Dados Ficam no seu PC:** Saves de exploração e configurações ficam armazenados localmente na pasta `%LOCALAPPDATA%\HexenMap\state`.
- **Extensão do AppSample:** A integração opcional do navegador apenas lê IDs numéricos públicos de marcações já visíveis no site, sem acessar senhas, cookies de sessão ou dados da conta.

---

## 2. Risco de Jogo e Termos de Uso (Seja Franco: Existe Risco?)

### Como o Hexen Map opera:
- **NÃO lê a memória RAM do jogo** (não usa `OpenProcess`, `ReadProcessMemory`, `WriteProcessMemory`).
- **NÃO injeta DLLs nem modifica arquivos do jogo** (não usa `VirtualAllocEx`, `CreateRemoteThread` nem hooks internos).
- **NÃO automatiza comandos ou simula bot** (não envia inputs automáticos para mover o personagem ou lutar).
- Funciona exclusivamente por **visão computacional externa** através de APIs legítimas de captura de tela do Windows (`Windows.Graphics.Capture` / `BitBlt`) e projeta uma janela de overlay transparente sobreposta na tela.

### Sobre Banimentos e Termos de Serviço da HoYoverse:
> [!WARNING]
> **O uso de qualquer software de terceiros junto com o Genshin Impact envolve uma área cinzenta nos Termos de Serviço da HoYoverse.**
> 
> Embora o Hexen Map não faça injeção de DLL nem alteração de memória (diferente de cheats ou hacks convencionais), o sistema anti-cheat proprietário da HoYoverse (**mhyprot2 / HoYoKProtect**) monitora processos rodando no sistema, captura de janelas e ganchos de teclado/mouse no Windows.
> 
> A HoYoverse **não aprova oficialmente nenhum software externo de terceiros**. Por isso:
> - **Não existe "garantia de 0% de risco"** ao utilizar qualquer ferramenta externa sobreposta ao jogo.
> - O uso é de responsabilidade de cada jogador.
> - Se você busca risco zero absoluto de questionamento pela empresa, recomendamos utilizar o mapa interativo em um segundo monitor, no celular ou no navegador com Alt+Tab.

---

## 3. Falsos Positivos de Antivírus (PyInstaller)

Os arquivos executáveis (`.exe`) disponibilizados nas Releases são compilados a partir deste código Python utilizando a ferramenta **PyInstaller**.

- **Por que alguns antivírus alertam?**  
  Binários empacotados por PyInstaller sem um certificado digital pago (EV Code Signing) são frequentemente marcados como *falso positivo* por motores de antivírus heurísticos (como Windows Defender, VirusTotal, etc.), pois o PyInstaller extrai interpretadores e bibliotecas dinâmicas temporariamente na pasta `%TEMP%`.
- **Como executar com 100% de confiança:**  
  Você não precisa rodar o executável pronto se não quiser. Como o projeto é open source, você pode clonar o repositório e executar diretamente em Python:
  ```powershell
  python -m pip install -r requirements.txt
  python src/app.py
  ```

---

## English Summary

- **Code Security:** 100% open-source, fully auditable. No memory reading, no DLL injection, no keylogging, no hidden telemetries or token stealers.
- **Ban Risk / Game Integrity:** The overlay uses pure external computer vision (screen capture + transparency layer). However, HoYoverse's anti-cheat does not officially whitelist any third-party tools. **There is no guarantee of zero risk**; usage is always at your own discretion.
- **Antivirus False Positives:** Precompiled executables use PyInstaller and lack an expensive commercial code-signing certificate, which can trigger heuristic false flags. Users are encouraged to run directly from source with Python if preferred.
