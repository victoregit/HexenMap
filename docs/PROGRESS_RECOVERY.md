# Persistência de coletas — correção 1.0.1

O modelo anterior guardava os saves em `userData` junto do executável. Instalar
em outra pasta podia abrir um perfil vazio, mesmo com o arquivo original intacto.
Preservar arquivos durante a reinstalação na mesma pasta não cobria esse caso.

## Novo contrato

- Saves e preferências ficam em `%LOCALAPPDATA%\HexenMap\state`, separados dos
  arquivos atualizados/desinstalados. `userData` continua contendo recursos e caches.
- O instalador registra a pasta pessoal original em `state-dir.txt`, preservado
  nas atualizações. Credenciais de outra conta administradora não mudam o destino.
- No primeiro uso, saves das pastas conhecidas são copiados com backup do original.
  Um arquivo vazio não ganha preferência sobre um save com coletas.
- Saves não vazios divergentes exigem escolha explícita. Não há união silenciosa
  que ressuscite itens desmarcados. O save fixo existente continua sendo a autoridade.
- Sem save detectado, o aplicativo pede para selecionar o arquivo antigo ou confirmar
  um perfil novo. Cancelar não cria um progresso vazio.
- Após inicialização, desaparecimento do save e do backup bloqueia novas gravações.
  Corrupção de arquivo e backup também bloqueia a abertura com progresso vazio.
- Falha ao preservar backup interrompe o salvamento. Além do backup anterior,
  mantém-se a primeira cópia diária. Esses arquivos não são removidos pelo instalador.
- Restaurar executáveis anteriores à 1.0.1 é bloqueado: eles usariam a pasta antiga
  e poderiam mostrar marcações desatualizadas. Rollback entre versões compatíveis
  continua usando o mesmo estado pessoal.

## Validação

Testes cobrem mudança de pasta/versão, migração, precedência de save não vazio,
conflitos, desmarcações, backup isolado, corrupção inicial e durante sessão,
falha de backup, desaparecimento de arquivos e conta administradora diferente.
O teste real isolado do instalador verifica upgrade, recuperação e retenção após
desinstalar. Não é garantia contra exclusão manual, falha de disco ou perda de
todas as cópias: backups independentes continuam necessários.

Neste incidente, o progresso original foi encontrado e copiado para a instalação
nova e para a pasta fixa, mantendo cópias de segurança e os arquivos antigos.
