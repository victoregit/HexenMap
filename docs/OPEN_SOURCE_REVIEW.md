# Revisão para abertura do código

Revisão local em 12/11/2026. Nenhum arquivo existente foi removido e nenhuma visibilidade de repositório foi alterada.

## Escopo e resultado

Inspecionados os arquivos versionados, regras de exclusão, fontes dos recursos, empacotamento e os 105 commits alcançáveis pelas referências locais. Foram examinados 989 blobs únicos do histórico por padrões de credenciais, caminhos pessoais e e-mails. Não foram encontrados padrões de tokens GitHub/AWS, chaves privadas ou atribuições comuns de credenciais. A busca por padrões não garante ausência de segredos; não inclui referências remotas ainda não baixadas, objetos inacessíveis nem inspeção visual/OCR dos binários.

O código já tem licença MIT em LICENSE. Não é adequado tratar automaticamente imagens do jogo e dados externos como MIT.

## Preparar antes de publicar

1. **Arte externa versionada:** revisar ou substituir `data/assets/nations/*`, `data/assets/groups/*.png`, `data/source/brand/*` e os derivados em `data/assets/brand/*`. Os manifestos atribuem emblemas/ícones à HoYoverse, registram símbolo Electro extraído de GIF e constelação Traveler capturada do jogo. Para uma publicação limpa sem permissões documentadas, usar recursos originais/substitutos e separar as licenças. Os manifestos não comprovam autorização de redistribuição. Não se conclui aqui que todos os recursos tenham o mesmo titular ou condição.
2. **Capturas versionadas:** `data/reference/*.png` precisa de inspeção visual antes da publicação, inclusive quanto a UID, nomes e outros dados visíveis. Não foi feita inspeção visual nesta revisão. Para a primeira publicação, pode-se omitir esse material e ajustar os scripts/testes que o utilizam.
3. **Dados locais:** manter fora da publicação `userData/`, `backups/`, `artifacts/`, `build/`, `dist/`, `.test-deps/`, executáveis, `state-dir.txt` e resultados locais. Já estão ignorados; não foram encontrados saves, .env ou chaves privadas entre os arquivos versionados pelos nomes pesquisados. Não publicar um ZIP indiscriminado da pasta de trabalho.
4. **Privacidade:** o suporte em `src/live/identity.py` usa e-mail pessoal; commits locais também expõem um e-mail pessoal de autor. Decidir se serão mantidos publicamente ou substituídos por contato dedicado e identidade noreply. Trocar o arquivo atual não muda commits antigos. Há caminhos locais em tarefas antigas; testes também contêm caminhos simulados, que não devem ser confundidos com dados reais.
5. **Histórico:** excluir um arquivo atual não o remove de commits antigos. Recomenda-se preparar uma exportação limpa em repositório novo se o objetivo for não publicar arte e metadados antigos. Preservar o repositório original como histórico privado.
6. **Documentação e execução:** README atual informa que clonar não fornece os pacotes pessoais de mapas/imagens/referências. Documentar instalação por código, dependências do Windows, recursos opcionais e execução sem os pacotes privados. Conferir que a versão pública funcione ou explique claramente suas limitações sem copiar userData pessoal.
7. **Empacotamento:** `scripts/package_portable.py` copia catálogos, referências, tiles, arte e templates de userData para um pacote explicitamente marcado como teste privado. Não usar esse fluxo sem revisão como pacote público de código/recursos. `data/world_map/SOURCE.json` e `scripts/prepare_appsample_package.py` também registram ausência de permissão geral de redistribuição.
8. **Créditos:** preservar LICENSE, avisos de terceiros, licenças de runtime e a licença da referência de localização. Criar uma explicação central delimitando código MIT, arte e dados externos. A documentação antiga em docs/archive e tasks pode ser omitida por organização, após conferir referências; isso não é uma exigência de segurança.

## Pode compor a versão pública

Código próprio de `src/`, testes sem dados pessoais, extensão em `extensions/`, scripts revisados, arquivos de build e instalador, documentação atual e licenças. Os testes e scripts podem depender de recursos omitidos e precisam de validação no pacote limpo.

A chave `key` do manifest da extensão é uma chave pública usada na identidade da extensão, não uma chave privada; não removê-la apenas por parecer um segredo. URLs públicas de atualização, doações e redes sociais não são credenciais.

## Limites

Esta é uma revisão técnica local, sem verificação externa de termos ou autorização de titulares. Não certifica conformidade jurídica, não valida visualmente capturas e não garante que uma exportação limpa já compile ou passe nos testes. Nenhum teste foi executado porque o código não foi alterado.
