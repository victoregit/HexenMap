"""Auditable local browser helper; never accesses browser sessions from Python."""
from src.live.storage import bundle_dir

GUIDE = '''Exportar coletados do AppSample

Método recomendado: extensão Hexen Map Exporter (ZIP de teste).
Envio direto opcional: em Ajustes, use Ativar conexão com a extensão (uma vez). HexenMapBridge.exe deve ficar junto do aplicativo. Na extensão 0.2.0, Enviar ao Hexen Map abre a prévia; confirme a mesclagem para aplicar. Ao migrar da 0.1.x, desative a extensão antiga antes de carregar a nova.
O conector é local, sem localhost e sem escrever no AppSample. Os arquivos enviados ficam em userData/browser-imports; cancelar a prévia preserva seu progresso.
Extraia o ZIP, abra chrome://extensions ou edge://extensions, ative Modo do desenvolvedor e use Carregar sem compactação na pasta que contém manifest.json.
Abra o AppSample, entre na conta pelo próprio site e clique na extensão. Use Atualizar leitura se a aba já estava aberta. Confira a quantidade, exporte e importe o JSON pelo Hexen Map. Lista vazia confirmada é diferente de leitura ausente.
Após mudar marcações ou trocar de conta, atualize a leitura. A extensão não salva histórico nem modifica o site. Compatibilidade real deve ser conferida nos dois navegadores antes de distribuir como versão estável.

Alternativa manual experimental:
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
    return '\n'.join((bundle_dir() / 'data/import' / name).read_text(encoding='utf-8')
                     for name in ('appsample-core.js', 'appsample-export.js'))
