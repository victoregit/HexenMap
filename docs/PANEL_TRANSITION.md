# Transição para a miniatura Electro

Ao usar **Jogar**, o botão **—** do painel ou **F8**, o app executa uma transição de 820 ms:

1. Um corte luminoso cruza o painel real.
2. Uma máscara Win32 fecha a janela do topo e da base em direção ao centro.
3. A fenda aprovada aparece sobre o corte e se desloca/encolhe até a posição da miniatura.
4. O controle compacto assume a reprodução no instante 3000 ms do ciclo aprovado de 5 segundos, evitando reiniciar num quadro vazio.

A janela não é capturada nem seus widgets são redimensionados durante a animação. A máscara recorta os controles reais; os efeitos são desenhados em uma janela temporária com a mesma preferência de captura. Essa janela usa o estilo Win32 NOACTIVATE e não cria botão na barra de tarefas. O foco só retorna ao jogo ao concluir o recolhimento.

A transição usa `after` e tempo monotônico. Não há espera bloqueante. O tamanho normal e a posição persistida são preservados. O estado salvo recolhido é restaurado imediatamente ao iniciar, sem repetir a transição. Ao clicar ou acionar novamente durante o efeito, ele conclui uma única vez. Ao fechar o app, a janela temporária e sua máscara são limpas.

Se o suporte nativo não estiver disponível ou a transição não puder começar, o caminho existente de recolhimento imediato continua disponível. Ao trocar para outro aplicativo durante o efeito, o recolhimento é concluído sem trazer o jogo ou a miniatura para a frente.

## Implementação

- `src/live/panel_transition.py`: coordenadas, composição e controlador temporário.
- `src/live/panel.py`: entrada por Jogar/—/F8, conclusão, foco e restauração.
- `src/live/native.py`: máscara de janela, transferência correta de ownership das regiões GDI e estilo sem ativação.
- `src/live/brand.py`: retomada da miniatura numa fase definida.

## Verificação

Os testes reais de Tk/Win32 verificam o término, foco uma única vez, estilo NOACTIVATE, fase correta da miniatura, posição, tamanho normal restaurado e acionamento repetido. Os testes de composição verificam os quadros inicial e final e a preservação das imagens de origem.

Uma **prévia ilustrativa**, feita com dados fictícios e sem leitura de tela, pode ser gerada com:

```powershell
python -m scripts.preview_panel_transition
```

Saída: `artifacts/panel-transition/panel-collapse.webp`. A ilustração usa as mesmas coordenadas e o mesmo renderizador de efeitos; o painel nela é uma representação desenhada no tema do app, não uma captura da janela.

A funcionalidade entra no executável no próximo build do projeto.
