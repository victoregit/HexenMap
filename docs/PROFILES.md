# Perfis locais

Na primeira abertura, o app verifica a pasta pessoal de saves e as pastas
conhecidas de instalações anteriores. Um save anterior único é recuperado
automaticamente, preservando o original e criando backup de migração. Uma
instalação sem sinais de uso anterior começa diretamente, sem perguntar sobre
importação. Saves conflitantes exigem seleção; arquivos inválidos ou sinais de
um save desaparecido bloqueiam a abertura em vez de criar progresso vazio.

Em **Ajustes → Perfis**, selecione um perfil e clique em **Usar perfil**.
Para outra conta do jogo, informe um nome e use **Criar e usar**. O novo perfil
começa sem coletas. **Renomear perfil ativo** muda apenas o nome de exibição.
O perfil ativo aparece no cabeçalho e é lembrado na próxima abertura.

Cada perfil mantém coletas, temporizadores dos recursos, histórico de importação
AppSample e backups próprios. Aparência, filtros, atalhos e recursos instalados
são compartilhados. A troca é manual, sem login, UID ou acesso à conta do jogo.
O Desfazer, as confirmações pendentes e o AutoMark são reiniciados ao trocar.
A prévia de importação informa qual perfil receberá as coletas.

O save anterior continua no mesmo arquivo, como perfil **Principal**. Não há
movimentação ou mesclagem automática dele. Dentro da pasta pessoal indicada
por `state-dir.txt` (normalmente `%LOCALAPPDATA%\HexenMap\state`):

- `progress.json` e seus backups: perfil original.
- `profiles.json` e `profiles.json.bak`: nomes e perfil ativo.
- `profiles/<id>/progress.json` e seus backups: perfis adicionais.

Para preservar todos os perfis, faça backup da pasta pessoal inteira com o app
fechado. Arquivos de save ausentes ou inválidos e falhas de gravação impedem a
troca, em vez de iniciar um perfil vazio ou substituir outra conta. Não há
exclusão de perfis nesta implementação.
