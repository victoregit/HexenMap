# Hexen Map Exporter 0.1.0 — relatório de validação

Data: 09/11/2026. Entrega experimental em ZIP, sem publicação nas lojas.

## Implementação

Manifest V3, scripts estáticos em MAIN e ISOLATED no document_start, acesso somente a HTTPS do AppSample, sem service worker ou permissões de cookies, debugger, histórico, downloads ou armazenamento. O host Firestore não recebe permissão de extensão: somente a resposta já recebida pelo site é observada. Referência técnica: [content scripts do Chrome](https://developer.chrome.com/docs/extensions/reference/manifest/content-scripts).

`data/import/appsample-core.js` é a fonte única de validação e observação de transporte; o empacotador copia esse arquivo para a extensão pronta. O script manual salvo pelo aplicativo concatena o mesmo núcleo. A pasta-fonte da extensão precisa ser empacotada para incluir o núcleo; a pasta pronta para carregar está em `dist/HexenMapExporter`.

Somente um documento diretamente na coleção users do projeto genshin-impact é aceito. Backups não contam como progresso; documentos users múltiplos não são combinados. Campo arrayValue sem values é lista vazia confirmada. Não há coerção numérica: `001` e `1` permanecem distintos. Limites: 16 MiB de resposta, 300.000 entradas antes da deduplicação, IDs ASCII decimais de 1 a 32 caracteres.

A ponte valida janela, origem, formato e token aleatório por documento. O popup verifica extensão de origem, aba ativa, contexto e revisão. O token correlaciona documentos, não autentica a página contra código malicioso em MAIN. Um snapshot inicial pode ficar transitoriamente na captura até a ponte estar pronta; após a entrega, só a ponte mantém a lista. Respostas exclusivas de backup ou ambíguas são ignoradas sem apagar um snapshot válido anterior. Não há armazenamento persistente nem mesclagem de snapshots.

## Testes automáticos e simulados

Regressão completa: **364 testes passaram**. Após o ajuste final de validação de listas malformadas, os 19 testes de exportação/extensão/importação foram executados novamente e passaram. Inclui quatro novos testes pytest; dois executam contratos Node com várias asserções internas, sem conta ou rede.

- Core: coleção users, backups, documentos múltiplos, missing, lista vazia, zeros iniciais, duplicação, IDs numéricos/Unicode/inválidos, limites de lista e tamanho.
- Fetch: promessa e resposta originais preservadas; leitura assíncrona de clone, erro e limite de stream sem consumir a resposta original.
- XHR: texto e JSON, conteúdo inválido/excessivo, abort, remoção de listeners e reuso via open.
- Ciclo de vida simulado: leitura anterior à ponte e ao popup, hooks duplicados, documentos/abas independentes, contexto antigo e origem/janela incorretas.
- Popup simulado: nenhum download ao abrir; exportação repetida só após clique, formato exato com três campos, atualização, zero confirmado e bloqueio quando muda a aba ativa.
- Importação local completa: saída do núcleo JS → parse Python → prévia de IDs exatos/ausentes → mesclagem em arquivo temporário → backup idêntico ao original → repetição sem duplicação → leitura após reinício.
- Pacote: manifesto sem background ou permissões amplas; scripts referenciados presentes; núcleo idêntico ao original; apenas oito arquivos permitidos, sem progresso ou dados de usuário.
- Alternativa manual: sete cenários existentes continuam passando após compartilhar o núcleo.

## Validação real — pendente

| Cenário | Chrome | Edge |
|---|---|---|
| Instalação local do ZIP | Pendente | Pendente |
| Captura com conta conectada | Pendente | Pendente |
| Sem login: não confundir ausência com zero | Pendente | Pendente |
| Exportação e importação completas | Pendente | Pendente |
| Recarregar, trocar conta e múltiplas abas reais | Pendente | Pendente |
| Conferência visual do popup | Pendente | Pendente |

Apenas o inventário dos navegadores foi consultado; não foi instalada extensão, realizado login nem alterada marcação. A validação real foi solicitada ao usuário. **Não declarar compatibilidade real concluída enquanto as duas colunas não forem conferidas.** Não inferir sucesso real a partir dos testes VM.

Instalação: [guia ilustrado local](EXPORTER_INSTALL.html), com esquemas próprios, não screenshots de instalação real. Instruções conferidas com a [documentação do Edge](https://learn.microsoft.com/en-us/microsoft-edge/extensions/getting-started/extension-sideloading).

## Reprodução

```powershell
node tests/exporter_contract.cjs .
node tests/exporter_popup_contract.cjs .
python -m pytest tests/test_appsample_export.py tests/test_exporter_extension.py tests/test_appsample_runtime.py -q
python scripts/package_exporter.py
```

ZIP e SHA-256 ficam em dist. O executável do aplicativo não é necessário para instalar a extensão; a importação usa o formato já aceito. O executável com o guia e o script manual atualizados foi gerado; os scripts congelados foram conferidos contra as fontes. A substituição local preserva o executável anterior em backups/exporter-guide-20261109-054355Z, sem tocar em userData. Nenhuma mudança em rastreamento, AutoMark, marcadores, catálogo ou temporizadores foi feita nesta tarefa.


## Hotfix 0.1.1 — leitura e feedback

O teste real do usuário no Chrome mostrou o popup instalado, porém permanentemente em Aguardando; captura/exportação reais ainda não aprovadas. Foi encontrada e reproduzida automaticamente uma corrida: iniciar uma segunda batchGet de backup invalidava a leitura users ainda em andamento. A versão 0.1.1 ordena apenas snapshots aceitos; backups e respostas ambíguas não cancelam leituras válidas. Também copia a resposta XHR antes do reuso do objeto pelo site.

A ponte informa conexão e fases sem URLs, nomes de documentos ou credenciais. MessageSender.url é opcional segundo a API Chrome; a verificação mantém o ID da própria extensão e rejeita scripts de abas e URLs de outras páginas. O popup agora deixa explícita a falta de resposta da ponte, em vez de mascarar essa falha como espera normal.

Barra indeterminada enquanto aguarda, recebe e valida, sem porcentagem fictícia. Após 20 segundos sem avanço, para a animação e diferencia observador desconectado de leitura de progresso ausente. O limite é feedback da interface, não um cancelamento: uma resposta válida posterior continua sendo aceita. Preferência de movimento reduzido é respeitada.

Contratos ampliados: users atrasado + backup concorrente, snapshot antigo após um users mais recente, remetente próprio sem URL, rejeição de content script, fases e timeout da barra. Captura real continua pendente; esta correção não é apresentada como confirmação do caso observado sem novo teste real.


## Hotfix 0.1.2 — núcleo ausente na inicialização

Erro real informado pelo usuário: `Uncaught ReferenceError: HexenAppSample is not defined`, em capture.js. O listener de mensagens já estava registrado quando a inicialização falhava, por isso a versão anterior podia indicar conectado sem observar fetch/XHR.

O empacotador agora gera uma entrada completa por mundo (capture.js e bridge.js), contendo o mesmo núcleo compartilhado e uma referência lexical dentro da mesma execução. O manifesto injeta um único arquivo por mundo; não depende de um global criado por outro arquivo injetado anteriormente. A captura só confirma attached depois de observe iniciar com sucesso. Falhas de inicialização produzem estado de erro explícito.

Novos testes executam os arquivos efetivos do ZIP em contextos vazios, sem núcleo pré-carregado, e verificam o falso conectado durante falha de inicialização. Os testes anteriores carregavam o núcleo antes dos scripts e não cobriam essa condição; a aprovação automática anterior não comprovava essa integração no Chrome.

A exportação real ainda exige conferência após a atualização; não declarada concluída nesta revisão.


## Envio local 0.2.0 — implementação e limites

A exportação 0.1.2 foi validada no Chrome pelo arquivo real entregue pelo usuário: 3.755 IDs únicos, zero duplicatas, contrato exato source/version/markerIds, aceito pelo parser Python. Isso comprova a exportação, não a nova conexão nativa nem a compatibilidade Edge.

A versão 0.2.0 adiciona nativeMessaging, uma identidade fixa por chave pública no manifesto e o host independente HexenMapBridge.exe. O host lê uma única mensagem com framing binário, limita a entrada a 16 MiB, valida origem de extensão e contrato exato e não aceita caminhos ou comandos. Encaminha apenas IDs para userData/browser-imports e abre o aplicativo instalado ao lado se não estiver ativo. Não há localhost, rede, cookies, leitura do perfil do navegador ou escrita no AppSample. O processo auxiliar encerra após responder.

Ativação explícita no painel grava o manifesto e as chaves HKCU NativeMessagingHosts para Chrome e Edge, sem instalar serviço ou registrar acesso a outras extensões. O aplicativo continua exigindo confirmação na prévia, mesclando com backup pelo fluxo existente; cancelar não grava coleta. Arquivos entregues são arquivados localmente após apresentar a prévia. O popup distingue envio à fila de importação aplicada.

Testes novos: pipe parcial/truncado, limite de mensagem, IDs decimais exatos, origem não autorizada, contrato incorreto, falha/cancelamento de abertura sem deixar fila pendente, limite de oito entregas aguardando, identidade do manifesto, consumo único da fila, espera por catálogo, confirmação e cancelamento reais do método de importação com messagebox simulado. O executável independente foi executado com origem inválida e devolveu framing correto sem iniciar o aplicativo. A primeira execução desse smoke test no sandbox não pôde extrair uma DLL temporária; com acesso à pasta temporária, o teste passou.

A regressão monolítica encerrou o processo no teste de imagens test_marker_hints (Windows 0x80000003); o módulo foi reexecutado isoladamente e seus nove testes passaram. O restante é executado separadamente para não apresentar a tentativa abortada como aprovação.

Pendente: validação real do botão Enviar ao Hexen Map no Chrome e Edge, com abertura do app fechado e recebimento no app aberto. O usuário precisa atualizar a extensão (desativando a 0.1.x antiga), ativar o conector e conferir a prévia. Não declarar sincronização bidirecional: o AppSample não é modificado.

Resultado da regressão 0.2.0 em processos separados: **380 testes passaram + 9 testes de marker_hints passaram**, totalizando 389 cenários. O teste monolítico abortado continua registrado acima.

Instalação local 0.2.0 realizada com cópia dos dois executáveis e backup em backups/native-connector-20261109-100222Z. O hash de userData/progress.json permaneceu idêntico. Ativação do registro real e teste completo pelo navegador continuam pendentes de ação do usuário. Após acrescentar a validação simulada das chaves HKCU, os 21 testes do conector/interface/extensão passaram novamente.
