# Decisões Técnicas (ADR)

## ADR-001
**MediaPipe: backend duplo (legado `solutions` + Tasks API)** — 2026-10-09

- **Contexto**: a especificação pede `mediapipe.solutions.hands`. Essa API foi removida nas versões ≥ 0.10.30 (verificado: `mediapipe 0.10.35` não tem `mp.solutions`). As versões que a têm (≤ 0.10.21) não têm wheels para Python 3.13 (o ambiente só tem 3.13).
- **Decisão**: `HandTracker` usa `mp.solutions.hands` quando existir e, caso contrário, a Tasks API `HandLandmarker` (modo `VIDEO`, `num_hands=1`). `requirements.txt` fixa `mediapipe==0.10.35`.
- **Trade-off**: o modelo `.task` (~7,8 MB) é baixado na primeira execução (URL fixa do Google, em `models/`, ignorado pelo git). Quem quiser a API legada instala Python ≤ 3.12 + `mediapipe==0.10.21`, sem mudar código.

## ADR-002
**Distância de pinça normalizada pelo tamanho da mão** — 2026-10-09

- Limiares em pixels dependem da distância à câmera. Normalizar por `dist(punho, base do médio)` torna os limiares estáveis. Mantida a opção em px (`USE_NORMALIZED_DISTANCE=False`).
- Histerese (fechar 0,28 / abrir 0,40) para evitar que o botão "pisque".

## ADR-003
**Backend de mouse injetável no `GestureController`** — 2026-10-09

- Permite testar a máquina de estados sem mover o mouse real. O padrão continua sendo `pyautogui` com `PAUSE=0` e `FAILSAFE=False` (exigência da especificação).

## ADR-004
**Dedo esticado por distância ao punho** — 2026-10-09

- Comparar `dist(punho, ponta)` com `dist(punho, PIP)` é invariante à rotação da mão, ao contrário de comparar só Y.

## ADR-005
**Deadzone do cursor medida até o alvo (não pelo passo do LERP)** — 2026-10-09

- Medir o passo fazia o cursor parar até `MIN_MOVE_PIXELS/α` px antes do alvo (8 px com α=0,25). Medindo o erro até o alvo, o erro final é < `MIN_MOVE_PIXELS`.

## ADR-006
**Scroll por deslocamento relativo acumulado** — 2026-10-09

- Acumula Δy da mão entre quadros e só dispara acima da zona morta (comportamento de touchpad). Alternativa descartada: "joystick" (distância a uma âncora), que exige devolver a mão à origem.

## ADR-007
**Abertura da webcam: MSMF com HW transforms desativado + fallback de backends** — 2026-10-09

- **Contexto**: no OpenCV 5.0.0.93 (Windows) o backend DSHOW não abre câmeras por índice, e o MSMF abre mas falha ao capturar (erro -1072875772) com HW transforms ligados. Verificado na máquina do usuário.
- **Decisão**: `OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS=0` antes do `import cv2` e `open_camera()` tenta MSMF, DSHOW e ANY, aceitando só o que entregar um frame.
- **Trade-off**: a variável é global ao processo (só afeta o backend MSMF).

## ADR-008
**Mapeamento Multimonitor: SPAN e ACTIVE_SWITCH com DPI Awareness** — 2026-10-09

- **Contexto**: usuários com múltiplos monitores podem ter telas de resoluções diferentes, escalas DPI desiguais e monitores secundários com coordenadas negativas no Windows.
- **Decisão**: utilizar `screeninfo` combinado com `SetProcessDPIAware()`, encapsulado na classe `MonitorManager`.
  - Modo `SPAN`: a área da câmera é mapeada linearmente através de todo o bounding box virtual, com *clamp* para a tela mais próxima quando o ponto cair fora da geometria dos monitores.
  - Modo `ACTIVE_SWITCH`: mapeamento 1:1 mantido no monitor selecionado, com alternância facilitada via tecla `'m'` ou números `'1'..'9'`.
  - Fallback suave automático para monitor único caso haja apenas 1 monitor ou a biblioteca falhe.

## ADR-009
**Duplo Clique Híbrido: Double-Tap temporal + Pinça Dedicada do Dedo Anelar** — 2026-10-09

- **Contexto**: a automação de duplo clique precisa de velocidade, previsibilidade e não deve interferir no gesto de arrastar janelas/arquivos (*drag and drop*).
- **Decisão**: fornecer duas abordagens complementares:
  1. *Double-Tap* com a pinça tradicional (indicador + polegar): duas pinças curtas em `< DOUBLE_CLICK_TIMEOUT` disparam `doubleClick()`. Para evitar cliques prematuros, o clique simples aguarda o timeout; o arraste é ativado apenas se a pinça for segurada por `≥ DRAG_HOLD_TIME`.
  2. *Pinça Dedicada*: aproximação entre ponta do anelar (16) e polegar (4) dispara `doubleClick()` instantaneamente, com debounce (`0.8s`), trava por gesto e filtro contra mão em punho fechado.
- **Trade-off e Prevenção de Conflito**: o duplo clique nunca ativa a flag `is_dragging` nem aciona `mouseDown()`, eliminando risco de travar janelas presas ao cursor.
