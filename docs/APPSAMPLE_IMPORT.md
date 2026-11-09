# Importar coletados do AppSample

Em **Ajustes → Como exportar do AppSample…**, o Hexen Map oferece um script local auditável e o passo a passo. Não existe comando CMD que leia automaticamente a sessão do navegador. O aplicativo não solicita acesso ao perfil do navegador.

1. Salve `hexen-appsample-export.js` pelo assistente e abra o [AppSample](https://genshin-impact-map.appsample.com/pt/).
2. Abra F12 → Sources/Fontes → Snippets → New snippet. Copie o conteúdo do arquivo para o snippet, confira e execute com Ctrl+Enter.
3. Sem recarregar ou mudar de página, saia e entre novamente na conta **pelo próprio AppSample**. Isso precisa provocar uma nova leitura do progresso.
4. Confira a quantidade e confirme o download de `appsample-coletados.json`.
5. No Hexen Map, use **Importar coletados do AppSample…**, selecione o arquivo e confira a prévia. Confirmar mescla o progresso e cria backup; não altera a conta do site.

O script observa temporariamente as respostas `fetch`/XHR do endpoint Firestore `documents:batchGet` do projeto `genshin-impact`. Não emite requisições, não lê cookies, armazenamento ou cabeçalhos e não grava documentos. A autenticação continua no site, utilizando seu mecanismo normal. A única saída é `{source, version, markerIds}`: IDs decimais únicos dos coletados. Nome do documento, dados da conta e outros campos são descartados. O código não imprime respostas privadas no Console.

O observador se restaura depois de encontrar uma resposta válida, inclusive ao cancelar o download, ou depois de três minutos. Recarregar também cancela. Não há sincronização contínua. O download exige confirmação e aceita lista vazia sem inventar marcações. Arquivos repetidos são tratados pelo importador existente; IDs ausentes do catálogo não são transferidos por aproximação.

**Experimental:** testes automáticos simulam fetch/XHR, lista vazia, cancelamento, prazo, origem indevida e formato inválido, além da compatibilidade com o importador. O fluxo completo de sair/entrar numa conta real ainda precisa de conferência. Se o AppSample mudar seu transporte ou formato, pode não exportar. Nesse caso, o observador expira e a importação manual de JSON/TXT permanece disponível.

Não desative proteções do navegador nem compartilhe HAR, cookies, tokens ou cabeçalhos de autorização. O script completo está em `data/import/appsample-export.js` e acompanha o executável; não baixa código externo. O Hexen Map não é afiliado ao AppSample.
