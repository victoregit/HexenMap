# Hexen Map — Guia de Uso, Execução e Compilação Independente

**Português (Brasil)** · [English](HOW_TO_USE.en.md)

Guia prático para jogadores, desenvolvedores e auditores de segurança executarem, testarem e compilarem o **Hexen Map** de forma transparente, reprodutível e verificável.

---

## Índice

1. [Visão Geral e Arquitetura](#visão-geral-e-arquitetura)
2. [Instalação e Uso Rápido (Pacote Oficial)](#1-instalação-e-uso-rápido-pacote-oficial)
3. [Execução Direta pelo Código-Fonte](#2-execução-direta-pelo-código-fonte)
4. [Entendendo os Dados e a Pasta `userData`](#3-entendendo-os-dados-e-a-pasta-userdata)
5. [Execução dos Testes Automatizados (604 Testes)](#4-execução-dos-testes-automatizados-604-testes)
6. [Compilação Independente com PyInstaller](#5-compilação-independente-com-pyinstaller)
7. [Execução da Suíte de Benchmarks](#6-execução-da-suíte-de-benchmarks)
8. [Verificação de Segurança e Integridade](#7-verificação-de-segurança-e-integridade)

---

## Visão Geral e Arquitetura

O **Hexen Map** é um assistente desktop para exploração no Genshin Impact. Ele opera **100% como janela transparente externa (overlay)**:
- **Não lê memória RAM do jogo** (`ReadProcessMemory` / `OpenProcess` não existem no código).
- **Não injeta DLLs** nem altera executáveis do jogo.
- **Não envia inputs automatizados** para o jogo.
- A detecção e o alinhamento são realizados unicamente por **visão computacional passiva** (`Windows.Graphics.Capture`, GDI `BitBlt` e OpenCV).
- As marcações de progresso e preferências são armazenadas exclusivamente de forma local em `%LOCALAPPDATA%\HexenMap\state`.

---

## 1. Instalação e Uso Rápido (Pacote Oficial)

Para a grande maioria dos jogadores, não é necessário instalar Python nem ferramentas de build:

1. Baixe o pacote portátil completo (`HexenMap-VERSAO-Windows-x64.zip`) ou o instalador oficial (`HexenMap-VERSAO-Setup-x64.exe`) nas [Releases Oficiais](https://github.com/victoregit/HexenMap-Releases).
2. Extraia o arquivo `.zip` para uma pasta de sua preferência (ex: `C:\Jogos\Hexen Map`). **Mantenha a pasta `userData` junto ao executável**.
3. Abra o **Genshin Impact** em modo **Janela** ou **Sem Bordas**.
4. Execute `HexenMap.exe` (ou use o atalho criado pelo instalador).
5. No painel de controle do Hexen Map:
   - **F8**: Exibir ou recolher o painel de itens.
   - **Ctrl + clique**: Marcar ou desmarcar itens no mapa.
   - **Ctrl + Alt + F12**: Mostrar ou ocultar todos os pins na tela.
   - **F9**: Confirmar coleta rápida de ponto próximo.
   - **F10**: Desfazer a última coleta realizada na sessão.

---

## 2. Execução Direta pelo Código-Fonte

Caso prefira inspecionar e rodar o projeto diretamente em Python:

### Pré-requisitos
- **Windows 10 ou 11** (64 bits).
- **Python 3.10 a 3.12** instalado com suporte a Tkinter e adicionado ao PATH.

### Passo a Passo

1. **Clone o repositório:**
   ```powershell
   git clone https://github.com/victoregit/HexenMap.git
   cd HexenMap
   ```

2. **Crie um ambiente virtual (recomendado):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Instale as dependências:**
   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

4. **Configuração dos dados (`userData`):**
   O código do Hexen Map é 100% aberto sob licença MIT. No entanto, por razões de direitos autorais de terceiros (HoYoverse / AppSample), as imagens de mapas e satélite não são versionadas diretamente no Git.
   - Baixe a versão portátil oficial mais recente e copie a pasta `userData` para a raiz do repositório clonado.
   
5. **Diagnóstico dos dados:**
   Antes de abrir a interface, confirme que os recursos foram reconhecidos:
   ```powershell
   python src/app.py --diagnose
   ```
   *Retorno esperado:* `{"items": 88957, "region": "appsample", ... "references": "available"}`.

6. **Inicie o aplicativo:**
   ```powershell
   python src/app.py
   ```

---

## 3. Entendendo os Dados e a Pasta `userData`

A separação de diretórios no Hexen Map segue o princípio de segurança e conformidade de licenças:

- `data/`: Contém assets autorizados, ícones SVG/PNG, arquivos de localização bilíngue (`ui-en-US.json`, `appsample-pt-BR.json`), metadados de licenças e dados de demonstração (`demo_markers.json`).
- `userData/`: Contém os catálogos importados, modelos visuais de reconhecimento (`automark/`), e caches locais de tiles de mapas.
- `%LOCALAPPDATA%\HexenMap\state`: Onde suas coletas reais (`progress.json`) e ajustes pessoais ficam armazenados, garantindo que atualizar o aplicativo nunca sobrescreva seu progresso.

---

## 4. Execução dos Testes Automatizados (604 Testes)

O Hexen Map possui **604 testes automatizados** cobrindo integração, rastreamento por visão computacional, importação/exportação, interface e segurança.

Para rodar todos os testes com `pytest`:

```powershell
$env:LANG="en_US.UTF-8"
python -m pytest
```

> [!NOTE]
> A variável `$env:LANG="en_US.UTF-8"` previne uma limitação da distribuição padrão do Tcl/Tk 8.6 no Windows ao carregar catálogos de mensagens em ambientes com localidade padrão em português.

---

## 5. Compilação Independente com PyInstaller

Você pode compilar seus próprios executáveis diretamente do código-fonte para garantir que o binário gerado corresponde estritamente ao repositório público:

### 1. Compilar o Hexen Map principal (`HexenMap.exe`):
```powershell
python scripts/build_exe.py --build-only
```
O executável compilado será colocado em `build/release-staging/HexenMap.exe`.

### 2. Compilar o Host de Comunicação com Extensão (`HexenMapBridge.exe`):
```powershell
python -m PyInstaller --noconfirm --distpath build/release-staging HexenMapBridge.spec
```

### 3. Compilar o Launcher (`HexenMapLauncher.exe`):
```powershell
python -m PyInstaller --noconfirm --distpath build/release-staging HexenMapLauncher.spec
```

### 4. Empacotar a extensão de navegador:
```powershell
python -c "import scripts.package_exporter; print(scripts.package_exporter.package())"
```

---

## 6. Execução da Suíte de Benchmarks

Para auditar o desempenho computacional, consumo de memória e latência dos algoritmos de visão e rastreamento:

```powershell
python scripts/run_benchmarks.py
```

Resultados típicos em hardware moderno:
- **Uso de Memória (RSS):** ~38 MB ocioso / ~48 MB em carga de pico.
- **Pipeline de Visão Computacional:** ~4.9 ms por matching de minimapa.
- **Taxa de Renderização:** < 0.1 ms por quadro (capaz de > 1000 FPS sem impactar o jogo).

---

## 7. Verificação de Segurança e Integridade

Auditoria independente confirmada:
- **Rede restrita:** Requisições são feitas unicamente sob demanda direta para a API do GitHub (verificação de releases oficiais assinadas por hash SHA-256), obtenção de fotos públicas de marcadores (`game-cdn.appsample.com`) e envio voluntário de feedback (`formsubmit.co`).
- **Zero telemetria:** Nenhuma credencial de conta, token de sessão, UID do jogo ou identificador de hardware é transmitido.
- **Sem privilégios indesejados:** O aplicativo não cria serviços do Windows, não agenda tarefas no Task Scheduler e não se adiciona à inicialização automática do sistema.
- Consulte a política completa em [SECURITY.md](SECURITY.md).
