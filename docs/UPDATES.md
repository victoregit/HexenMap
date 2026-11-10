# Launcher e instalador Windows

Implementação inicial de 10/11/2026. Artefatos locais de teste; publicação de
release e autorização para redistribuir o conjunto de mapas/arte continuam separadas.

## Uso

O instalador por usuário cria **Hexen Map** no menu Iniciar, na busca do Windows
e em Aplicativos instalados. O atalho abre `HexenMapLauncher.exe`. A pasta padrão
é `%LOCALAPPDATA%\Programs\Hexen Map`, sem exigir administrador para instalar.
Ao abrir o launcher, o Windows pede administrador antes da verificação de
atualizações. Depois de autorizado, o launcher inicia o overlay herdando essa
permissão, sem novo pedido. A continuação após atualização também herda a
elevação do instalador. Cancelar a autorização impede a abertura.

Desde a 1.0.1, coletas e preferências ficam em `%LOCALAPPDATA%\HexenMap\state`,
fora da pasta do programa. O caminho original é registrado em `state-dir.txt`.
`userData` continua contendo recursos e caches. Saves anteriores encontrados
são migrados com backup; sem save encontrado, o usuário escolhe importar um
arquivo antigo ou confirmar um perfil novo. Falhas não autorizam sobrescrever
progresso com uma base vazia. Veja [PROGRESS_RECOVERY.md](PROGRESS_RECOVERY.md).
Não há sincronização em nuvem: faça backup da pasta pessoal com o app fechado.
O instalador inclui dados iniciais, nunca os saves do desenvolvedor.

A instalação registra sua conta original em `installed-user.txt`. Se forem
usadas credenciais de outra conta administradora na abertura do launcher,
ele mantém a pasta e os saves originais e abre o overlay, mas não executa a
atualização por usuário naquela conta diferente. Isso evita mover atalhos e
registro para o administrador informado. Atualize pela conta que instalou.

## Atualização ao abrir

O launcher mostra uma abertura breve, centralizada, com animação giratória,
sem botões nem cliques no fluxo normal. Consulta até 30 Releases públicas de
`victoregit/HexenMap-Releases`.
Uma instalação beta acompanha betas e estáveis; uma estável aceita somente
estáveis. Tags usam `vMAJOR.MINOR.PATCH` ou `vMAJOR.MINOR.PATCH-beta.N`
(alpha e rc também são aceitos). Rascunhos, versões antigas e ativos inválidos
são ignorados. Sem atualização, o launcher abre o aplicativo. Se houver erro
de rede, limitação da API ou repositório privado, abre a versão instalada automaticamente.

O ativo deve chamar-se `HexenMap-VERSAO-Setup-x64.exe`, com tamanho e digest
`sha256:…` informados pela API do GitHub. O launcher baixa o arquivo, confere
tamanho, SHA-256 e cabeçalho Windows antes de executá-lo. Sem digest, não há
instalação automática. Não há tokens ou credenciais embutidos. Isso verifica
integridade; o instalador ainda não possui assinatura Authenticode própria.

A atualização automática usa o mesmo instalador por usuário em modo totalmente silencioso,
com a pasta atual explícita. O launcher sai para liberar seus arquivos e o
instalador o reabre ao concluir. Tanto o launcher quanto o instalador bloqueiam
a atualização enquanto o overlay estiver aberto. Não se encerra o jogo ou o
overlay à força. A cópia baixada fica em `updates` para diagnóstico/reinstalação.

## Recuperação

Ao trocar de versão, o instalador salva os três executáveis, `BUILD.json` e o
marcador de versão em `.previous`. Se a versão nova não funcionar, feche overlay
e launcher e execute `Restaurar versao anterior.cmd` na pasta instalada.
O script aceita somente versões 1.0.1 ou posteriores, que usam o mesmo save fixo.
Versões anteriores são bloqueadas para não reabrir dados antigos de outra pasta.
O script restaura somente os arquivos do programa e pausa a atualização automática,
evitando reinstalar imediatamente a mesma versão com falha. Nesse estado, o
launcher abre diretamente a versão restaurada. Remova o arquivo `updates-paused`
da pasta instalada para retomar as atualizações. Backups incompletos são recusados antes da
cópia; nesse caso, execute o instalador anterior. `userData` permanece intacta.

## Geração e publicação

1. Atualize as versões em `src/live/identity.py`, `pyproject.toml` e no recurso
   Windows. Gere e confira o pacote portátil com `scripts/build_release.py`.
2. Instale o compilador oficial Inno Setup 6.4+ ou 7. Execute
   `python scripts/build_installer.py --iscc "CAMINHO/ISCC.exe"`.
   O script verifica o inventário e os hashes do pacote, compila o launcher e
   produz o Setup e seu `.sha256` em `dist/installer`.
3. Confira instalação limpa, upgrade, recuperação e preservação das coletas.
   Publique o Setup e o `.sha256` numa Release com tag correspondente somente
   após revisar os arquivos e as condições de distribuição dos dados.

A primeira Release, `v1.0.0`, foi publicada em 10/11/2026 em
https://github.com/victoregit/HexenMap-Releases/releases/tag/v1.0.0 .
Os dois anexos e o digest do instalador foram conferidos na API pública;
o código do launcher detectou 1.0.0 usando 0.4.1-beta.1 como versão instalada.
O ciclo completo de instalação de uma próxima atualização ainda requer uma
versão posterior publicada.
