"""Loop principal do Virtual Gesture Mouse.

Execução (a partir da raiz do projeto):
    python -m src.main
ou
    python src/main.py
"""

import os
import sys
import time
from pathlib import Path

# Permite executar como script (`python src/main.py`) além de `python -m src.main`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "src"

# Deve ser definido ANTES de importar o cv2: com os HW transforms ligados, o
# backend MSMF do Windows abre a webcam mas falha ao capturar frames
# (erro -1072875772). Também acelera a abertura da câmera.
os.environ.setdefault("OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS", "0")

import cv2  # noqa: E402

from . import config  # noqa: E402
from .gesture_controller import GestureController, Mode  # noqa: E402
from .hand_tracker import HAND_CONNECTIONS, HandData, HandTracker  # noqa: E402
from .monitors import MODE_ACTIVE_SWITCH  # noqa: E402

KEY_ESC = 27


def open_camera() -> cv2.VideoCapture:
    """Abre a webcam com a resolução/FPS configurados e buffer mínimo.

    Tenta vários backends e só aceita um que realmente entregue um frame
    (no OpenCV 5.0 o DSHOW não abre por índice e o MSMF pode abrir sem capturar).
    """
    if sys.platform == "win32":
        backends = [cv2.CAP_MSMF, cv2.CAP_DSHOW, cv2.CAP_ANY]
    else:
        backends = [cv2.CAP_ANY]

    for backend in backends:
        cap = cv2.VideoCapture(config.CAMERA_INDEX, backend)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # menor latência
            ok, _ = cap.read()
            if ok:
                return cap
        cap.release()

    raise RuntimeError(
        f"Não foi possível abrir a webcam (índice {config.CAMERA_INDEX}). "
        "Verifique se outro app a está usando, as permissões de câmera do "
        "Windows, ou ajuste CAMERA_INDEX em src/config.py."
    )


def draw_hud(frame, hand, controller: GestureController, fps: float) -> None:
    """Desenha moldura ativa, esqueleto, pontas dos dedos ativos, estado e monitor."""
    h, w = frame.shape[:2]

    # Retângulo da zona ativa de movimento (deadzone de borda)
    cv2.rectangle(
        frame,
        (config.FRAME_MARGIN_X, config.FRAME_MARGIN_Y),
        (w - config.FRAME_MARGIN_X, h - config.FRAME_MARGIN_Y),
        config.HUD_COLOR_BOX,
        2,
    )

    # Esqueleto leve da mão (feedback de rastreamento)
    if isinstance(hand, HandData):
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, hand.point(a), hand.point(b), (120, 120, 120), 1, cv2.LINE_AA)

    # Círculos de destaque nas pontas dos dedos ativos
    tip_color = (0, 0, 255) if controller.is_dragging else config.HUD_COLOR_TIP
    for pt in controller.highlight_points:
        cv2.circle(frame, pt, config.HUD_TIP_RADIUS, tip_color, cv2.FILLED)
        cv2.circle(frame, pt, config.HUD_TIP_RADIUS + 3, (255, 255, 255), 2, cv2.LINE_AA)

    # Modo atual (com prioridade para avisos temporários como duplo clique / clique direito)
    mode = controller.display_mode
    bar_color = {
        Mode.NAVIGATING: (0, 140, 0),
        Mode.DRAGGING: (0, 0, 180),
        Mode.RIGHT_CLICK: (180, 80, 0),
        Mode.DOUBLE_CLICK: (200, 0, 160),
        Mode.SCROLL: (0, 140, 180),
        Mode.CLICK: (0, 100, 180),
    }.get(mode, (60, 60, 60))

    # Barra de estado no topo
    cv2.rectangle(frame, (0, 0), (w, 40), bar_color, cv2.FILLED)
    cv2.putText(
        frame, f"MODO: {mode.value}", (10, 28),
        cv2.FONT_HERSHEY_SIMPLEX, config.HUD_FONT_SCALE, config.HUD_COLOR_TEXT, 2, cv2.LINE_AA,
    )
    cv2.putText(
        frame, f"FPS: {fps:4.1f}", (w - 130, 28),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, config.HUD_COLOR_TEXT, 2, cv2.LINE_AA,
    )

    # Informações de multimonitor e atalhos na parte inferior
    monitors_mgr = controller.monitors
    if monitors_mgr.mode == MODE_ACTIVE_SWITCH and monitors_mgr.is_multi:
        active_lbl = monitors_mgr.label(monitors_mgr.active_index)
        monitor_text = f"MONITOR ATIVO: {active_lbl} [SWITCH]"
    else:
        # Modo SPAN ou monitor único: informa onde o cursor está no momento
        curr_idx, _ = controller.current_monitor()
        mode_tag = " [SPAN]" if monitors_mgr.is_multi else ""
        monitor_text = f"MONITOR ATIVO: {monitors_mgr.label(curr_idx)}{mode_tag}"

    # Fundo escuro semitransparente para a barra inferior
    cv2.rectangle(frame, (0, h - 30), (w, h), (30, 30, 30), cv2.FILLED)
    cv2.putText(
        frame, monitor_text, (10, h - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 255, 200), 1, cv2.LINE_AA,
    )

    # Atalhos disponíveis
    switch_hint = f" | '{config.MONITOR_SWITCH_KEY}': alternar tela" if (
        monitors_mgr.mode == MODE_ACTIVE_SWITCH and monitors_mgr.is_multi
    ) else ""
    help_text = f"ESC/q: sair{switch_hint}"
    cv2.putText(
        frame, help_text, (w - 240 if switch_hint else w - 100, h - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.48, config.HUD_COLOR_TEXT, 1, cv2.LINE_AA,
    )


def main() -> int:
    cap = open_camera()
    tracker = HandTracker()
    controller = GestureController()

    mon_info = f"{len(controller.monitors)} tela(s) [{controller.monitors.mode}]"
    print(
        f"[VGM] Backend MediaPipe: {tracker.backend} | Monitores: {mon_info}.\n"
        f"      Pressione ESC ou 'q' para sair."
        + (f" Use '{config.MONITOR_SWITCH_KEY}' para alternar telas." if controller.monitors.is_multi else "")
    )

    switch_key_code = ord(config.MONITOR_SWITCH_KEY.lower()) if config.MONITOR_SWITCH_KEY else ord("m")
    switch_key_upper = ord(config.MONITOR_SWITCH_KEY.upper()) if config.MONITOR_SWITCH_KEY else ord("M")

    fps = 0.0
    prev = time.perf_counter()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("[VGM] Falha ao ler frame da webcam.")
                break

            frame = cv2.flip(frame, 1)  # espelha horizontalmente
            h, w = frame.shape[:2]

            hand = tracker.process(frame)
            controller.update(hand, w, h)

            now = time.perf_counter()
            dt = now - prev
            prev = now
            if dt > 0:
                fps = 0.9 * fps + 0.1 * (1.0 / dt) if fps else 1.0 / dt

            draw_hud(frame, hand, controller, fps)
            cv2.imshow(config.WINDOW_NAME, frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (KEY_ESC, ord("q"), ord("Q")):
                break

            # Atalho de alternância de monitor ativo (modo ACTIVE_SWITCH)
            if key in (switch_key_code, switch_key_upper):
                controller.switch_monitor()
            elif ord("1") <= key <= ord("9"):
                target_idx = key - ord("1")
                controller.switch_monitor(target_idx)

            # Fechar a janela pelo "X" também encerra o programa de forma limpa.
            if cv2.getWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break
    except KeyboardInterrupt:
        pass
    finally:
        controller.shutdown()  # garante mouseUp() de qualquer clique pendente
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
