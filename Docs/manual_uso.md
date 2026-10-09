# Manual de Uso

## 1. Instalação

Requer Windows/Linux/macOS com webcam e Python 3.10+ (testado: Python 3.13, Windows).

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Na primeira execução com mediapipe ≥ 0.10.30 o modelo `hand_landmarker.task` (~7,8 MB) é baixado automaticamente para `models/` (requer internet nessa primeira vez). Alternativa manual: baixe de
`https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task` e salve em `models/hand_landmarker.task`.

> No macOS é necessário conceder permissão de "Acessibilidade" e "Gravação de tela" ao terminal; no Linux, é preciso um servidor X11 (PyAutoGUI não controla Wayland puro).

## 2. Executar

Na raiz do projeto:

```powershell
python -m src.main
```

Encerrar: `ESC` ou `q` com a janela da câmera em foco (ou fechar a janela / `Ctrl+C`). Qualquer clique pendente é solto automaticamente.

## 3. Gestos

| Gesto | Como fazer | Resultado |
|---|---|---|
| Mover | Só o **indicador** esticado (demais recolhidos) | Cursor segue a ponta do indicador |
| Clique / Arrastar | **Pinça** polegar + indicador | Fechou = botão esquerdo pressionado; segurar e mover = arrastar; abrir = soltar. Pinça rápida = clique |
| Clique direito | **Pinça** polegar + dedo médio | Um clique direito por gesto |
| Scroll | **Indicador + médio** esticados juntos (anelar e mínimo recolhidos) | Subir a mão rola para cima, descer rola para baixo |
| Pausa | Punho fechado ou palma aberta | Nada acontece (descanse a mão aqui) |

Dicas: mantenha a palma voltada para a câmera, boa iluminação e fundo sem muito ruído. Antes de clicar, pare o indicador sobre o alvo e só então feche a pinça (a ponta do indicador se desloca um pouco ao fechar).

## 4. HUD

- Retângulo magenta: moldura ativa (a mão só precisa se mover dentro dele).
- Círculos nas pontas dos dedos ativos (vermelhos durante o arraste).
- Barra superior: `MODO: NAVEGANDO | ARRASTANDO | CLIQUE DIREITO | SCROLL | PAUSADO | SEM MAO` e FPS.

## 5. Calibração (tudo em `src/config.py`)

### 5.1 Distância do usuário à câmera

Por padrão `USE_NORMALIZED_DISTANCE = True`: a distância da pinça é dividida pelo tamanho da mão na imagem, então os limiares funcionam de ~40 cm a ~1,5 m **sem recalibrar**. Procedimento recomendado:

1. Sente-se na distância habitual e rode o programa.
2. Faça a pinça de arraste. Se não fecha com facilidade, **aumente** `PINCH_CLOSE_THRESHOLD_NORM` (ex.: 0,28 → 0,33). Se dispara sem querer ao esticar o indicador, **diminua** (ex.: 0,22).
3. Mantenha `PINCH_OPEN_THRESHOLD_NORM` ~0,10–0,15 acima do valor de fechar. Se o arraste "solta sozinho", aumente essa folga; se demora a soltar, reduza.
4. Repita para o clique direito (usa os mesmos limiares).

Valores de referência (razão distância/tamanho da mão): dedos encostados ≈ 0,05–0,15; pinça "relaxada" ≈ 0,20–0,30; mão aberta ≈ 0,6–1,2.

Modo em pixels (`USE_NORMALIZED_DISTANCE = False`): ajuste `PINCH_CLOSE_THRESHOLD_PX` / `PINCH_OPEN_THRESHOLD_PX` conforme a distância (resolução 640x480):

| Distância à câmera | Fechar (px) | Abrir (px) |
|---|---|---|
| ~40 cm (perto) | 50–60 | 80–90 |
| ~70 cm (padrão) | 30–40 | 50–60 |
| ~1,2 m (longe) | 15–22 | 28–35 |

Se mudar a distância com frequência, prefira o modo normalizado.

### 5.2 Sensibilidade e alcance

- `FRAME_MARGIN_X/Y`: **maior** = moldura menor = cursor mais rápido, menos movimento da mão. **Menor** = mais precisão, mais movimento. Se não alcança os cantos da tela, aumente a margem. Se a mão sai do campo da câmera, diminua.
- Mais longe da câmera, a mão fica menor: reduza a margem (ex.: 60) para manter o alcance.

### 5.3 Suavização

- `SMOOTHING_FACTOR` (α): 0,15–0,2 = muito suave (mais atraso); **0,25** padrão; 0,4–0,6 = responsivo (mais tremor); 1,0 = sem suavização.
- `MIN_MOVE_PIXELS`: 2–4 elimina tremor parado; 0 desativa.

### 5.4 Gestos e scroll

- `MODE_CONFIRM_FRAMES`: quadros para confirmar troca de modo. Aumente (3–4) se o modo "pisca"; reduza (1) para resposta imediata.
- `RIGHT_CLICK_DEBOUNCE_S`: intervalo mínimo entre cliques direitos.
- `SCROLL_SENSITIVITY`, `SCROLL_DEADZONE_PX`, `SCROLL_MAX_STEP`: velocidade, zona morta e limite da rolagem. `SCROLL_INVERT = True` inverte o sentido.
- `LOST_HAND_TOLERANCE_FRAMES`: quadros sem mão tolerados antes de soltar um arraste (evita soltar por falha momentânea de detecção).

### 5.5 Desempenho

- Use `MODEL_COMPLEXITY = 0` (mais rápido; só afeta o backend legado), resolução 640x480 e boa iluminação (câmeras reduzem o FPS no escuro).
- Feche outros programas que usem a webcam; ajuste `CAMERA_INDEX` se houver mais de uma câmera.

## 6. Solução de problemas

| Sintoma | Causa provável / ação |
|---|---|
| `Não foi possível abrir a webcam` | Webcam em uso ou índice errado: ajuste `CAMERA_INDEX`. Feche apps que usem a câmera (Teams, Zoom, navegador) e confira em Configurações > Privacidade > Câmera se apps de desktop têm acesso |
| `module 'mediapipe' has no attribute 'solutions'` | Não deve ocorrer: o projeto usa a Tasks API nesse caso. Verifique `pip install -r requirements.txt` |
| Falha ao baixar modelo | Sem internet: baixe manualmente (seção 1) |
| Cursor treme | Diminua `SMOOTHING_FACTOR` e aumente `MIN_MOVE_PIXELS` |
| Cursor atrasado | Aumente `SMOOTHING_FACTOR` |
| Clique escapa do alvo | Pare o indicador antes de fechar a pinça; reduza o limiar de fechar |
| Não arrasta em alguns apps | Apps executados como administrador ignoram input de processos não elevados: rode o terminal como administrador |

> Segurança: `pyautogui.FAILSAFE = False` desabilita o atalho de emergência de mover o mouse ao canto. Use sempre `ESC`/`q` com a janela da câmera em foco, ou `Ctrl+C` no terminal.
