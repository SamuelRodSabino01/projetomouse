"""Constantes de configuração do Virtual Gesture Mouse.

Todos os parâmetros ajustáveis (resolução, margens, limiares, suavização)
ficam centralizados aqui. Veja ``Docs/manual_uso.md`` para o guia de calibração.
"""

# ---------------------------------------------------------------------------
# Captura de vídeo
# ---------------------------------------------------------------------------
CAMERA_INDEX = 0          # Índice da webcam (0 = padrão)
CAMERA_WIDTH = 640        # Resolução solicitada à webcam (px)
CAMERA_HEIGHT = 480
CAMERA_FPS = 30           # FPS solicitado à webcam
WINDOW_NAME = "Virtual Gesture Mouse"

# ---------------------------------------------------------------------------
# MediaPipe Hands
# ---------------------------------------------------------------------------
MAX_NUM_HANDS = 1
MODEL_COMPLEXITY = 0              # 0 = mais rápido, 1 = mais preciso
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.6

# ---------------------------------------------------------------------------
# Moldura ativa (zona de movimento) — margem em px a partir de cada borda
# do frame da câmera. Aumentar a margem = precisa mover menos a mão para
# alcançar as bordas da tela (e vice-versa).
# ---------------------------------------------------------------------------
FRAME_MARGIN_X = 100
FRAME_MARGIN_Y = 100

# ---------------------------------------------------------------------------
# Suavização anti-jitter (LERP / média móvel exponencial)
#   pos = pos_anterior + (alvo - pos_anterior) * SMOOTHING_FACTOR
# Faixa: (0, 1]. Valores baixos = mais suave porém com mais atraso;
# 1.0 = sem suavização.
# ---------------------------------------------------------------------------
SMOOTHING_FACTOR = 0.25

# Se o alvo estiver a menos deste valor (px de tela) do cursor, nada é movido,
# eliminando vibrações residuais quando a mão está parada.
MIN_MOVE_PIXELS = 2

# ---------------------------------------------------------------------------
# Limiares de pinça (distância 2D em px do frame da câmera).
# Para ser independente da distância do usuário, a distância é normalizada
# pelo tamanho da mão (punho -> base do dedo médio) quando
# USE_NORMALIZED_DISTANCE = True. Nesse caso os limiares são razões.
# ---------------------------------------------------------------------------
USE_NORMALIZED_DISTANCE = True

# Valores em razão (modo normalizado)
PINCH_CLOSE_THRESHOLD_NORM = 0.28   # abaixo disso = pinça fechada
PINCH_OPEN_THRESHOLD_NORM = 0.40    # acima disso = pinça aberta (histerese)

# Valores em px (modo não normalizado)
PINCH_CLOSE_THRESHOLD_PX = 35
PINCH_OPEN_THRESHOLD_PX = 55

# ---------------------------------------------------------------------------
# Clique direito
# ---------------------------------------------------------------------------
RIGHT_CLICK_DEBOUNCE_S = 0.6        # tempo mínimo entre dois cliques direitos

# ---------------------------------------------------------------------------
# Scroll vertical
# ---------------------------------------------------------------------------
SCROLL_DEADZONE_PX = 8              # deslocamento mínimo (px do frame) p/ rolar
SCROLL_SENSITIVITY = 6.0            # unidades de scroll por px de deslocamento
SCROLL_MAX_STEP = 120               # limite de unidades por quadro
SCROLL_INVERT = False               # True inverte o sentido da rolagem

# ---------------------------------------------------------------------------
# Estabilidade dos gestos
# ---------------------------------------------------------------------------
# Quadros consecutivos necessários para confirmar uma troca de modo
# (evita flicker na classificação dos dedos).
MODE_CONFIRM_FRAMES = 2
# Quadros sem mão detectada tolerados antes de soltar o botão do mouse.
LOST_HAND_TOLERANCE_FRAMES = 8

# ---------------------------------------------------------------------------
# Múltiplos monitores (requer `screeninfo`; sem ele usa o monitor único)
#   "SPAN"          - a moldura ativa da câmera cobre TODO o desktop virtual
#                     (todos os monitores lado a lado): a mão cruza a borda de
#                     um monitor direto para o outro.
#   "ACTIVE_SWITCH" - a moldura cobre só o monitor ativo (sensibilidade 1:1);
#                     a tecla MONITOR_SWITCH_KEY alterna o monitor ativo
#                     (teclas 1..9 escolhem diretamente).
# ---------------------------------------------------------------------------
MULTI_MONITOR_MODE = "SPAN"
# Monitor ativo inicial (ACTIVE_SWITCH). None = monitor primário; ou índice
# 0-based na ordem da esquerda para a direita (0 = monitor mais à esquerda).
DEFAULT_MONITOR_INDEX = None
# Limites manuais de tela, ignorando a detecção. Lista de (x, y, largura, altura)
# no desktop virtual do SO, p.ex.: [(-1600, 130, 1600, 900), (0, 0, 1920, 1080)].
# None = detectar automaticamente.
MONITORS_OVERRIDE = None
MONITOR_SWITCH_KEY = "m"            # tecla (janela da câmera em foco) que alterna o monitor

# ---------------------------------------------------------------------------
# Duplo clique
#  1) Double-tap: duas pinças curtas (indicador+polegar) em menos de
#     DOUBLE_CLICK_TIMEOUT disparam doubleClick() em vez de dois cliques.
#     Para isso o clique simples é confirmado só após o timeout (e o cursor
#     fica parado nesse intervalo); o arraste começa após DRAG_HOLD_TIME.
#     DOUBLE_TAP_ENABLED = False restaura o comportamento anterior (mouseDown
#     imediato ao fechar a pinça, sem double-tap).
#  2) Pinça dedicada: anelar (landmark 16) + polegar (4) dispara doubleClick()
#     imediatamente, com debounce.
# ---------------------------------------------------------------------------
DOUBLE_TAP_ENABLED = True
DOUBLE_CLICK_TIMEOUT = 0.35         # segundos entre o início das duas pinças
DRAG_HOLD_TIME = 0.18               # s com a pinça fechada p/ virar arraste (< DOUBLE_CLICK_TIMEOUT)

# Pinça anelar+polegar (mesma lógica de normalização/histerese da pinça padrão)
RING_PINCH_THRESHOLD_NORM = 0.28    # abaixo disso = pinça fechada (razão)
RING_PINCH_OPEN_THRESHOLD_NORM = 0.40
RING_PINCH_THRESHOLD_PX = 35        # modo não normalizado
RING_PINCH_OPEN_THRESHOLD_PX = 55
# Ignora a pinça do anelar com a mão em punho (indicador, médio e mínimo todos
# recolhidos): evita duplo clique acidental ao fechar o punho para pausar.
RING_PINCH_REQUIRE_OPEN_HAND = True
DOUBLE_CLICK_DEBOUNCE_S = 0.8       # intervalo mínimo entre duplos cliques da pinça anelar
DOUBLE_CLICK_FLASH_S = 0.6          # tempo do aviso "DUPLO CLIQUE" no HUD

# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------
HUD_COLOR_BOX = (255, 0, 255)       # BGR
HUD_COLOR_TIP = (0, 255, 0)
HUD_COLOR_TEXT = (255, 255, 255)
HUD_FONT_SCALE = 0.8
HUD_TIP_RADIUS = 12
