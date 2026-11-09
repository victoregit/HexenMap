"""Auditable local browser helper; never accesses browser sessions from Python."""
from src.live.storage import bundle_dir

GUIDE = '''Exportar coletados do AppSample

1. Salve o script e abra o AppSample no seu navegador.
2. Pressione F12 → Sources (Fontes) → Snippets. Se estiver oculto, use ».
3. Clique em New snippet (Novo snippet), abra o arquivo salvo em um editor e copie seu conteúdo para o snippet. Confira o código antes de executar.
4. Execute com Ctrl+Enter. Não recarregue nem navegue para outra página.
5. Pelo próprio AppSample, saia e entre novamente na conta. O script aguarda até três minutos pela nova leitura do progresso.
6. Confira a quantidade e autorize o download de appsample-coletados.json.
7. Volte ao Hexen Map → Importar arquivo e confira a prévia antes de mesclar.

O script lê somente a resposta de progresso que o próprio site recebe. Salva apenas IDs, origem e versão; não exporta conta, e-mail, cookies ou tokens e não cria requisições. O login continua entre você e o AppSample. Não altera marcações.

O observador temporário se encerra após exportar, cancelar, expirar ou recarregar. Não há sincronização contínua. Se a estrutura do site mudar, pode não encontrar os dados; a importação manual de JSON/TXT continua disponível.

Não desative proteções do navegador. Se ele bloquear a execução ou se não quiser executar código, feche o DevTools e use o arquivo de progresso obtido manualmente. Nunca envie HAR, cabeçalhos ou credenciais ao Hexen Map.

Exportação guiada experimental: o formato foi testado automaticamente; o fluxo completo de reconexão precisa ser conferido no navegador. Não é uma integração oficial do AppSample.'''


def script_text():
    return (bundle_dir()/'data/import/appsample-export.js').read_text(encoding='utf-8')
