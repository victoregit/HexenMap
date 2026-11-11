# Validação local do minimapa

O usuário aprovou a correção local do minimapa em 11 de novembro de 2026.
A recuperação adicional remove a iluminação suave do cone da câmera somente
quando o fluxo original rejeita a consistência dos pontos. Os limites
geométricos e o detector de abertura e recompensas do AutoMark foram preservados.
A publicação dos mapas novos e a calibração pessoal continuam como etapas próprias.

## Gravação no jogo

1. Em Ajustes → Diagnóstico, selecione **Gravar / encerrar teste do minimapa…** e confirme.
2. Volte ao jogo. Durante os próximos 20 segundos, caminhe, corra e gire a câmera
   no percurso em que os ícones costumam desaparecer. O mesmo botão encerra antes.
3. Selecione **Exportar teste do minimapa…** e salve o ZIP.
4. Repita o percurso com o AutoMark no outro estado, ligado ou desligado.
5. Valide separadamente baús, menus, teleporte, perda de foco, troca de mapas e
   resoluções menores disponíveis. As dimensões reais ficam no diagnóstico.

Somente o canto superior esquerdo é gravado, com limite de 20 quadros por segundo,
20 segundos e 50 MiB por sessão. A fila de escrita tem oito entradas; descartes
são registrados. Os arquivos ficam em `diagnostics/minimap`, junto à pasta dos
dados pessoais, fora dos perfis de progresso. Não há envio automático. Não se
deve contabilizar quadros descartados como prova de continuidade.

## Reprodução técnica

Extraia o ZIP. No ambiente de desenvolvimento:

```powershell
python scripts/replay_minimap_test.py CAMINHO_DA_GRAVACAO --output build/replay.json
```

Para comparar com uma cópia anterior do rastreador, acrescente
`--baseline-python CAMINHO_DO_MODULO_ANTERIOR.py`. Use as mesmas referências e a
mesma máquina. A reprodução mantém a cadência gravada; resultados absolutos
assíncronos ainda podem variar conforme a carga da máquina.

O relatório distingue a localização publicada das tentativas internas e informa
as rejeições por pontos, consistência de ida e volta, RANSAC, distribuição,
movimento, resíduo, incerteza e reaplicação absoluta. Resultados incompatíveis com
o mapa/camada ou com uma geometria descartada não podem restaurar os pins.

Na captura real limpa em 1366×768, os pares de movimento válidos passaram de
229/231 para 231/231. Cada par começa com identidade; esse teste não equivale à
localização absoluta contínua. Na reprodução completa de outra sequência de
450 quadros, o tempo oculto caiu de 0,548 s para 0,360 s, com quatro intervalos
em vez de seis. Ainda houve um intervalo de 156 ms, portanto a aprovação visual
do usuário não comprova o cumprimento de todas as metas numéricas.

Para reproduzir a comparação entre pares de uma gravação exportada:

```powershell
python scripts/validate_minimap_lighting.py CAMINHO_DA_GRAVACAO --output build/lighting.json
```

Percentuais de quadros válidos dependem da identificação correta do trecho
jogável; o resíduo do fluxo óptico não é erro de posição medido contra uma
referência independente. A meta de 99,5% de validade e P95 de até 3 px ainda
exige capturas reais e posições verificáveis. Resoluções simuladas não substituem
testes em outro monitor ou escala de DPI.
