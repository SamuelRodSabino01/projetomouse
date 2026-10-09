# Módulos

## `src/monitors.py`

- `Monitor(x, y, width, height, is_primary, name)` (dataclass imutável):
  - Propriedades `right`, `bottom`, `center`.
  - `contains(px, py) -> bool`: verifica se o ponto está dentro dos limites da tela.
  - `clamp(px, py) -> (float, float)`: projeta um ponto para a borda mais próxima desta tela.
- `detect_monitors(fallback_size) -> list[Monitor]`:
  - Detecta monitores via `screeninfo` com DPI awareness ativado.
  - Suporta `MONITORS_OVERRIDE` configurado pelo usuário.
  - Fallback suave para tela única `(0, 0, *fallback_size)` se houver falha ou apenas 1 monitor.
  - Retorna monitores ordenados da esquerda para a direita (`x` crescente).
- `MonitorManager(monitors, mode, default_index)`:
  - Propriedades: `is_multi`, `virtual_size` (largura e altura combinadas), `active_index`, `active`.
  - `map_normalized(u, v) -> ndarray[2]`:
    - `MODE_SPAN`: mapeia `(u, v) ∈ [0, 1]` pelo bounding box do desktop virtual com clamp para geometrias não retangulares.
    - `MODE_ACTIVE_SWITCH`: mapeia `(u, v)` com sensibilidade 1:1 apenas no monitor ativo.
  - `clamp_to_monitors(x, y) -> (float, float)`: garante que o ponto final esteja sobre uma tela válida do SO.
  - `monitor_at(x, y) -> (int, Monitor)`: retorna qual tela contém (ou está mais próxima) das coordenadas.
  - `cycle_active() -> int` e `set_active(index) -> bool`: alterna o monitor ativo.
  - `label(index) -> str`: texto formatado para o HUD (ex.: `2 [1920x1080]`).

## `src/hand_tracker.py`

- `HandData(points)` — 21 landmarks `(x, y)` em px do frame:
  - `point(idx) -> (int, int)`; `distance(a, b) -> float` (px).
  - `hand_size() -> float`: distância punho(0)–base do médio(9).
  - `pinch_distance(a, b) -> float`: normalizada por `hand_size()` se `USE_NORMALIZED_DISTANCE`, senão px.
  - `ring_tip() -> (int, int)`: coordenadas da ponta do anelar (landmark 16).
  - `ring_thumb_distance() -> float`: distância euclidiana entre anelar (16) e polegar (4).
  - `fingers_up() -> dict[str, bool]`: identifica dedos esticados com base na distância punho-ponta vs punho-PIP.
- `HandTracker()` — adapter automático entre MediaPipe legado (`solutions.hands`) e Tasks API (`HandLandmarker`).
  - `process(frame_bgr) -> HandData | None`.
  - `close()`; propriedade `backend`.
- `_ensure_model(path)` — download automático do modelo `.task` se ausente.
- Constantes de landmarks (`THUMB_TIP=4`, `INDEX_TIP=8`, `MIDDLE_TIP=12`, `RING_TIP=16`...) e `HAND_CONNECTIONS`.

## `src/gesture_controller.py`

- `Mode` (enum): `IDLE`, `PAUSED`, `NAVIGATING`, `CLICK`, `DRAGGING`, `RIGHT_CLICK`, `DOUBLE_CLICK`, `SCROLL`.
- `GestureController(backend=None, clock=time.monotonic, monitors=None)`:
  - `update(hand, frame_w, frame_h) -> Mode`: processa um quadro de vídeo.
  - `display_mode -> Mode`: modo com prioridade para avisos temporários (duplo clique / clique direito).
  - `current_monitor() -> (int, Monitor)`: monitor atual sob o cursor.
  - `switch_monitor(index=None) -> bool`: alterna monitor ativo no modo `ACTIVE_SWITCH` e recentraliza o cursor suavemente.
  - `shutdown()`: cancela cliques pendentes e garante execução de `mouseUp()`.
  - `map_to_screen(point, fw, fh) -> ndarray[2]`: normaliza ponto na moldura ativa da câmera e projeta via `MonitorManager`.
- Regras de negócio e gestos:
  - **Prioridade de pinças**: pinça em curso > pinça do indicador > pinça do médio > pinça do anelar > gestos livres.
  - **Duplo clique temporal (Double-Tap)**: duas pinças rápidas do indicador em `< DOUBLE_CLICK_TIMEOUT` disparam `doubleClick()`. Se não houver 2ª pinça, o clique simples é despachado retroativamente.
  - **Duplo clique dedicado (Anelar + Polegar)**: pinça imediata com debounce `DOUBLE_CLICK_DEBOUNCE_S`. Ignorado com mão em punho fechado (`RING_PINCH_REQUIRE_OPEN_HAND`).
  - **Prevenção de conflito**: duplo clique nunca aciona `is_dragging` nem prende o botão do mouse.
  - **Arraste**: pinça do indicador mantida por `≥ DRAG_HOLD_TIME` ativa `mouseDown()`. Ao soltar, ativa `mouseUp()`.
  - **Clique direito**: pinça do médio com trava e debounce de `0.6s`.
  - **Scroll**: deslocamento vertical acumulado com zona morta e limites de velocidade.
  - **Anti-jitter**: LERP exponencial com fator `SMOOTHING_FACTOR` e deadzone `MIN_MOVE_PIXELS`.

## `src/main.py`

- `open_camera() -> cv2.VideoCapture`: abre webcam tentando `CAP_MSMF` (com HW transforms desativado), `CAP_DSHOW` e `CAP_ANY`.
- `draw_hud(frame, hand, controller, fps)`:
  - Retângulo magenta da zona ativa (deadzone de borda).
  - Esqueleto da mão e círculos de destaque nas pontas dos dedos ativos.
  - Barra superior de status com modo atual colorido e FPS.
  - Barra inferior indicando qual monitor recebe o cursor (`MONITOR ATIVO: X [LxA]`) e atalhos disponíveis.
- `main() -> int`:
  - Loop de captura, espelhamento horizontal, rastreamento e HUD.
  - Atalhos: `ESC`/`q` para sair; `'m'` (ou tecla configurada) para alternar monitores; `'1'`..`'9'` para selecionar tela diretamente.
  - Bloco `finally` chamando `controller.shutdown()` e limpando recursos.

## `src/config.py`

Centraliza todos os parâmetros ajustáveis: câmera, margens de movimento, anti-jitter, limiares de pinça (normalizados e em pixels), modos multimonitor (`SPAN`/`ACTIVE_SWITCH`), atalhos e temporizadores do duplo clique.
