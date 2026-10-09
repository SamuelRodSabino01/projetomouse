# Changelog

## 2026-10-09 (features multimonitor e duplo clique)

- `requirements.txt`: adicionada dependência `screeninfo==0.8.1`.
- `src/monitors.py`: novo módulo de gerenciamento de desktop virtual e detecção dinâmica de monitores via `screeninfo`, cálculo de bounding box, suporte a offsets negativos e modos `SPAN` e `ACTIVE_SWITCH`.
- `src/config.py`: adicionadas opções de múltiplos monitores (`MULTI_MONITOR_MODE`, `DEFAULT_MONITOR_INDEX`, `MONITORS_OVERRIDE`, `MONITOR_SWITCH_KEY`) e constantes de calibração do duplo clique (`DOUBLE_TAP_ENABLED`, `DOUBLE_CLICK_TIMEOUT`, `DRAG_HOLD_TIME`, `RING_PINCH_THRESHOLD_NORM`, `DOUBLE_CLICK_DEBOUNCE_S`).
- `src/hand_tracker.py`: adicionada extração do Landmark 16 (ponta do anelar) e cálculo da distância euclidiana com o polegar (4) (`ring_thumb_distance()`).
- `src/gesture_controller.py`:
  - Implementado duplo clique temporal via Double-Tap rápido da pinça do indicador (`< DOUBLE_CLICK_TIMEOUT`).
  - Implementado duplo clique instantâneo dedicado com pinça anelar + polegar com debounce e filtro anti-punho.
  - Implementada prevenção de conflito para duplo clique não travar em `is_dragging`.
  - Integrado mapeamento de coordenadas ao `MonitorManager`, suportando múltiplos monitores e troca com centralização suave.
- `src/main.py`: HUD expandido com exibição do monitor ativo e atalhos na barra inferior (`ESC/q` e tecla `'m'` / números `'1'..'9'`), com feedback temporário de duplo clique.
- `Docs/`:
  - `Docs/arquitetura.md`: detalhamento do cálculo de bounding box de telas e novo diagrama de estados.
  - `Docs/features_multimonitor_duplo_clique.md`: guia prático de calibração e resolução de telas mistas.
  - Atualizados `ARCHITECTURE.md`, `FILE_MAP.md`, `MODULES.md` e `DECISIONS.md`.

## 2026-10-09 (correção)

- `main.py`: corrigida a abertura da webcam no Windows com OpenCV 5.0 (DSHOW não abre por índice; MSMF falhava ao capturar). Define `OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS=0` antes de importar o `cv2` e tenta MSMF -> DSHOW -> ANY, validando a leitura de um frame. Ver ADR-007.

## 2026-10-09

- Criação inicial do projeto: `config.py`, `hand_tracker.py`, `gesture_controller.py`, `main.py`, `requirements.txt`, `.gitignore`.
- Gestos: mover, clique/arraste (pinça), clique direito (pinça com debounce), scroll vertical, pausa.
- HUD com moldura ativa, destaques de dedos, estado e FPS; encerramento limpo com `mouseUp()`.
- `HandTracker` com backend duplo (legado e Tasks API) — ver ADR-001.
- Documentação em `Docs/`.
