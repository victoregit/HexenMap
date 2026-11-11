# Comparação do minimapa antes e depois da expansão

Investigação local em 11 de novembro de 2026, antes da correção de iluminação.
Esta investigação não altera o executável, os detectores, os recursos instalados
ou os dados pessoais.

## Bases comparadas

- `f406ce3`: correção de estabilidade anterior à release 1.0.6.
- `a07fc1a`: painel e interação da versão 1.0.7.
- `bdecb77`: localização em inglês; último commit antes da expansão ainda local.
- Árvore atual: expansão, recuperação do AutoMark por ícones e diagnóstico local.

Após normalizar apenas as chamadas de tradução, a comparação das árvores
sintáticas entre `f406ce3` e `bdecb77` não encontrou diferenças nas classes e
funções de `motion.py`, `budget_vision.py` e `vision.py`. A apresentação dos pins
também não tem alterações nesse intervalo. As mudanças de ativação das janelas
em `native.py` tratam a interação em fullscreen, sem mudar a implementação da
captura. Não foram revertidas.

## Referências de Teyvat

Os 216 arquivos declarados no manifesto atual coincidem com os nomes e hashes
dos pacotes locais 1.0.7 e dos oito pacotes de teste arquivados de 9 de novembro.
Os hashes dos 216 arquivos atuais também foram recalculados, sem divergências.
A preparação dos novos mapas acrescentou um índice `routing.npz` em Teyvat;
o rastreador detalhado existente não usa esse arquivo.

## Mudanças posteriores relevantes

| Mudança | Possível impacto | Situação observada |
| --- | --- | --- |
| Busca automática de outros mapas | Concorrência durante uma recuperação prolongada | Existe desde a expansão; a versão atual evita iniciar por uma perda breve comum após localizar. Requer teste durante transições. |
| Troca confirmada de contexto | Reinício de continuidade, referências e AutoMark | Proteção necessária para não exibir pins de outra área; preservada. |
| Leitura de recompensas por ícones | Trabalho adicional na thread do AutoMark | Introduzida para reconhecer recompensas em inglês; preservada porque o usuário confirmou funcionamento. Falta medir a concorrência no percurso atual. |
| Separação da observação visível e da última pose verificada | Permite recuperar após uma falha sem encurtar a validade da âncora pela observação oculta | Introduzida no último teste local; pode alterar a frequência de reaparecimentos. Não relaxa os limites geométricos. |
| Invalidação por geometria e mapa/camada | Descarta resultados absolutos incompatíveis | Introduzida no último teste local; proteção preservada. |
| Registro opcional do minimapa | Escrita assíncrona durante teste iniciado pelo usuário | Inativo até início explícito; não explica perdas anteriores à gravação. |

## Reprodução com o rastreador histórico

O módulo de movimento foi extraído diretamente de `f406ce3` e comparado ao atual
na mesma sequência real já disponível (`build/minimap-walk-source.npz`), com as
mesmas referências, mantendo a cadência gravada. A sequência contém 450 quadros,
incluindo momentos sem minimapa; os valores abaixo não são percentuais de
validade do percurso jogável.

| Medida | Movimento de `f406ce3` | Movimento atual |
| --- | ---: | ---: |
| Quadros com localização publicada | 301 | 308 |
| Intervalos ocultos detectados pelo HUD | 5 | 6 |
| Soma desses intervalos | 0,843 s | 0,564 s |
| Intervalos menores que 500 ms | 4 | 6 |

O atual ficou menos tempo oculto, mas alternou mais vezes nessa execução. O
histórico também perde localização nessa captura. Isso não comprova melhora
visual, nem reproduz necessariamente o problema atual relatado pelo usuário.
Correspondências absolutas são assíncronas e variam com carga e temporização.
Não há posição independente de referência neste teste. Relatório completo:
`build/minimap-historical-comparison.json`.

Em outra reprodução, os 58 quadros estáveis tiveram acréscimo médio de 0,00495 ms
pela chamada da busca automática (0,074% do tempo do rastreador). Nenhuma busca
de fundo foi iniciada nesse trecho. Esse resultado exclui uma sobrecarga grande
nessa condição estável, mas não mede recuperação concorrente nem AutoMark.
Relatório: `build/minimap-historical-search-overhead.json`.

## Evidência da sessão atual e limite da conclusão

O log local de 18:47–18:48 mostra perdas por fluxo/RANSAC e expiração da âncora
enquanto o reconhecimento absoluto retorna “Locating this map area…”. Há
exemplos de expiração perto de 1,53 s e de 5,03 s, correspondentes aos dois
limites já existentes na versão histórica. Uma mensagem `flow=accepted` isolada
não prova localização publicada: pode corresponder à cadeia relativa de uma
âncora ainda pendente.

Ainda não foi identificada uma alteração específica que explique toda a
regressão relatada. Uma reversão integral do rastreador não está justificada
pelas medições. A próxima evidência necessária é a gravação explícita do
percurso atual com falha, repetida com AutoMark ligado e desligado, para
comparar movimento, concorrência e busca de mapas no mesmo cenário. Nenhuma
captura nova foi iniciada nesta investigação.

## Validação posterior

Após esta auditoria, a comparação visual confirmou que a captura da janela usada
pelo app não inclui os pins, mesmo quando eles aparecem na captura do desktop.
Uma nova sequência limpa identificou duas rejeições associadas à mudança do
cone claro da câmera. A recuperação de contraste passou nesses dois pares,
preservando a rotina do AutoMark. O usuário aprovou a compilação local seguinte.
Resultados e limites estão em `MINIMAP-VALIDATION.md`.
