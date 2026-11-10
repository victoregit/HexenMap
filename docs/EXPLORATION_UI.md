# Hexen Map 0.4.0-beta.1 — painel, fotos e mapa geral

## Como usar

- **Tamanho do painel:** puxe as bordas da janela independente. No modo
  fixado ao jogo, arraste a alça do canto inferior direito.
- **Escala:** Ajustes → Painel e compartilhamento → Tamanho dos textos e
  controles. Opções: 100%, 125% e 150%. Restaurar tamanho padrão mantém a
  escala escolhida. Tamanho expandido, posição e escala são salvos.
- **Fotos:** clique numa foto carregada no cartão. A roda aproxima,
  arrastar move e Ajustar à janela restaura o enquadramento. Esc fecha a
  ampliação sem fechar o cartão. A resolução é a da foto já carregada;
  ampliar não inventa detalhes.
- **Oculi:** pins nos mapas recebem contorno pérola e borda escura. O halo
  não intercepta cliques; o seletor mantém a arte original. Coletados
  revelados continuam dessaturados.
- **Planetinha:** abre o mapa geral da superfície de Teyvat, mesmo sem
  jogo aberto ou localização válida. Arraste, use a roda ou +/−. Ver Teyvat
  inteiro restaura a visão geral. Grupos indicam vários pontos próximos;
  clique para aproximar. Clique num pin para abrir seu cartão e alterar
  a coleta. Mostrar coletados permite desmarcá-los; Desfazer restaura o
  registro anterior, incluindo o prazo de um recurso.

O mapa compartilha a seleção de tipos e o progresso com o painel, mas sua
navegação e seu recorte de superfície são independentes do mapa/camada
usados pelo reconhecimento do jogo. Não move o mapa M nem o personagem.
Selecionar zero tipos mostra zero pontos. Cavernas e mapas separados não
recebem um fundo de superfície como substituto.

## Dados e recursos

O mapa usa somente o catálogo e os tiles pessoais AppSample v72 já
instalados, no sistema `appsample-webmercator-z14`. A base de zoom 12 tem
288 tiles e cobre a extensão instalada; 2.239 tiles de zoom 14 dão maior
detalhe nos trechos disponíveis. Na falta de um tile detalhado, usa-se o
mesmo trecho da base, com menor definição. Fora da cobertura, não se
inventa imagem nem coordenada. Não há downloads durante a navegação.

São aproximadamente 15 MiB adicionais de tiles no pacote privado, sem
gravações de calibração ou progresso pessoal. O cache de imagens PIL do
mapa é limitado a 32 MiB; imagens Tk são mantidas para o viewport atual.
Índice e decodificação são feitos em background; pins usam desenho em
lotes. Fechar a janela cancela pendências e libera seus recursos.

Origem e condições estão em `data/world_map/SOURCE.json`. A página de
embed do AppSample permite incorporar o site; isso não foi interpretado
como autorização geral para redistribuir dados ou arte. Os arquivos são
os da instalação pessoal e o pacote permanece para testes privados.

## Verificação

Testes cobrem redimensionamento e ida/volta entre escalas, persistência,
enquadramento/zoom, filtros e coletas, fallback dos tiles, recorte de fotos
durante zoom, Esc e halo sem ampliar a máscara de clique. O mapa foi
inspecionado em janela Tk com imagens e pontos reais, usando uma cópia
temporária do progresso. A instalação confere o progresso antes/depois.

Não foram repetidos aceites manuais das regiões antigas. O aceite real
do AutoMark em 1080p e 1440p continua pendente com os testadores; estas
funções de apresentação não alteram os detectores ou suas referências.
