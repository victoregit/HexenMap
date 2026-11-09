# Importar coletados do AppSample

## Extensão de teste (sem F12)

O **Hexen Map Exporter 0.2.0** exporta o progresso carregado pelo próprio site. O ZIP local é gerado com `python scripts/package_exporter.py`; usuários recebem o ZIP pronto, sem precisar de Python. Extraia e carregue a pasta `HexenMapExporter` em `chrome://extensions` ou `edge://extensions`, usando modo de desenvolvedor e Carregar sem compactação. Veja o [guia ilustrado](EXPORTER_INSTALL.html) e o [relatório de testes](EXPORTER_TEST_REPORT.md).

Abra o AppSample e faça login no próprio site. Clique na extensão; se a aba já estava aberta, clique em **Atualizar leitura** e reabra o popup após carregar. Confira quantidade e horário e use **Exportar progresso**. No Hexen Map, importe o JSON pela opção existente, confira a prévia e confirme a mesclagem com backup. Depois de alterar marcações ou trocar de conta, atualize novamente.

A lista fica na memória da aba, sem histórico. Cada nova resposta substitui a anterior. Lista vazia confirmada é exportável; ausência de resposta não é interpretada como zero. A extensão aceita somente um documento `users`, ignora `users-backup` e rejeita ambiguidades. Não há servidor, sincronização ou leitura de credenciais. A captura MAIN compartilha o ambiente do site, portanto não comprova autenticidade contra uma página maliciosa. IDs com zeros iniciais são preservados.

A primeira versão exige instalação local; não está publicada nas lojas. A compatibilidade real permanece pendente até conferir captura e importação completas no Chrome e Edge, com e sem login.

## Alternativa manual experimental

Em **Ajustes → Como exportar do AppSample…**, o Hexen Map oferece um script local auditável e o passo a passo. Não existe comando CMD que leia automaticamente a sessão do navegador. O aplicativo não solicita acesso ao perfil do navegador.

1. Salve `hexen-appsample-export.js` pelo assistente e abra o [AppSample](https://genshin-impact-map.appsample.com/pt/).
2. Abra F12 → Sources/Fontes → Snippets → New snippet. Copie o conteúdo do arquivo para o snippet, confira e execute com Ctrl+Enter.
3. Sem recarregar ou mudar de página, saia e entre novamente na conta **pelo próprio AppSample**. Isso precisa provocar uma nova leitura do progresso.
4. Confira a quantidade e confirme o download de `appsample-coletados.json`.
5. No Hexen Map, use **Importar coletados do AppSample…**, selecione o arquivo e confira a prévia. Confirmar mescla o progresso e cria backup; não altera a conta do site.

O script observa temporariamente as respostas `fetch`/XHR do endpoint Firestore `documents:batchGet` do projeto `genshin-impact`. Não emite requisições, não lê cookies, armazenamento ou cabeçalhos e não grava documentos. A autenticação continua no site, utilizando seu mecanismo normal. A única saída é `{source, version, markerIds}`: IDs decimais únicos dos coletados. Nome do documento, dados da conta e outros campos são descartados. O código não imprime respostas privadas no Console.

O observador se restaura depois de encontrar uma resposta válida, inclusive ao cancelar o download, ou depois de três minutos. Recarregar também cancela. Não há sincronização contínua. O download exige confirmação e aceita lista vazia sem inventar marcações. Arquivos repetidos são tratados pelo importador existente; IDs ausentes do catálogo não são transferidos por aproximação.

**Experimental:** testes automáticos simulam fetch/XHR, lista vazia, cancelamento, prazo, origem indevida e formato inválido, além da compatibilidade com o importador. O fluxo completo de sair/entrar numa conta real ainda precisa de conferência. Se o AppSample mudar seu transporte ou formato, pode não exportar. Nesse caso, o observador expira e a importação manual de JSON/TXT permanece disponível.

Não desative proteções do navegador nem compartilhe HAR, cookies, tokens ou cabeçalhos de autorização. O script salvo pelo aplicativo reúne `data/import/appsample-core.js` e `data/import/appsample-export.js` e acompanha o executável; não baixa código externo. O Hexen Map não é afiliado ao AppSample.


## Envio direto opcional (0.2.0)

Desative a extensão 0.1.x antes de instalar a nova identidade fixa. No aplicativo atualizado, use Ajustes → Ativar conexão com a extensão. O arquivo HexenMapBridge.exe precisa ficar ao lado de HexenMap.exe. A ativação grava apenas o manifesto local e o registro NativeMessagingHosts do usuário atual para Chrome/Edge. Depois, Enviar ao Hexen Map encaminha os IDs para a fila local; abre o app se necessário e apresenta a mesma confirmação de mesclagem com backup. Não confirma importação no popup: apenas o recebimento para a prévia. Nenhuma escrita no AppSample ou sincronização bidirecional foi adicionada. Baixar JSON continua funcionando sem ativar o conector.
