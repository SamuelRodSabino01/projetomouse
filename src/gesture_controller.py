"""Máquina de estados que converte gestos da mão em ações do mouse.

Estados (``Mode``):
    IDLE         - nenhuma mão detectada
    PAUSED       - mão visível sem gesto reconhecido (punho, palma aberta...)
    NAVIGATING   - indicador esticado: move o cursor
    CLICK        - pinça indicador+polegar recém-fechada (ainda decidindo se é
                   toque, duplo toque ou arraste); cursor congelado
    DRAGGING     - pinça indicador+polegar mantida: ``mouseDown`` ativo
    RIGHT_CLICK  - pinça médio+polegar: dispara ``rightClick`` (com debounce)
    DOUBLE_CLICK - duplo toque da pinça padrão ou pinça anelar+polegar:
                   dispara ``doubleClick`` (nunca entra em ``is_dragging``)
    SCROLL       - indicador e médio levantados: rolagem vertical

Pinça do indicador (fases internas ``_Pinch``):
    NONE -> PENDING   ao fechar (sem mouseDown; cursor congelado)
    PENDING -> DRAGGING  se mantida por ``DRAG_HOLD_TIME`` (mouseDown)
    PENDING -> NONE   se aberta antes (toque): o clique simples fica pendente
                      por ``DOUBLE_CLICK_TIMEOUT``; se uma 2ª pinça fechar nesse
                      prazo => ``doubleClick``; senão => ``click``
    NONE -> CONSUMED  2ª pinça dentro do prazo (doubleClick já disparado)
    Com ``DOUBLE_TAP_ENABLED = False`` o comportamento é o antigo: mouseDown
    imediato ao fechar e mouseUp ao abrir.

O controlador não depende diretamente do ``pyautogui``: ele recebe um
"backend" com a mesma interface (``size``, ``position``, ``moveTo``,
``mouseDown``, ``mouseUp``, ``click``, ``doubleClick``, ``rightClick``,
``scroll``), o que permite testá-lo com um backend falso, sem mover o mouse real.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np

from . import config
from .hand_tracker import HandData, INDEX_TIP, MIDDLE_TIP, RING_TIP, THUMB_TIP
from .monitors import MODE_ACTIVE_SWITCH, Monitor, MonitorManager


class Mode(Enum):
    IDLE = "SEM MAO"
    PAUSED = "PAUSADO"
    NAVIGATING = "NAVEGANDO"
    CLICK = "CLIQUE"
    DRAGGING = "ARRASTANDO"
    RIGHT_CLICK = "CLIQUE DIREITO"
    DOUBLE_CLICK = "DUPLO CLIQUE"
    SCROLL = "SCROLL"


class _Pinch(Enum):
    """Fase da pinça indicador+polegar."""

    NONE = 0
    PENDING = 1     # fechada, ainda não decidiu entre toque e arraste
    DRAGGING = 2    # mouseDown ativo
    CONSUMED = 3    # duplo clique já disparado; aguardando a pinça abrir


@dataclass
class _PendingClick:
    """Toque curto cujo clique simples ainda não foi enviado (espera o 2º toque)."""

    anchor: Tuple[int, int]
    deadline: float


def _default_backend() -> Any:
    """Importa e configura o pyautogui (latência zero, sem failsafe)."""
    import pyautogui

    pyautogui.PAUSE = 0
    pyautogui.FAILSAFE = False
    return pyautogui


class GestureController:
    """Interpreta ``HandData`` a cada quadro e aciona o mouse."""

    def __init__(
        self,
        backend: Any = None,
        clock: Callable[[], float] = time.monotonic,
        monitors: Optional[MonitorManager] = None,
    ) -> None:
        self.backend = backend if backend is not None else _default_backend()
        self._clock = clock

        # Monitores (com fallback automático para monitor único)
        if monitors is None:
            size = self.backend.size()
            monitors = MonitorManager.from_config((int(size[0]), int(size[1])))
        self.monitors: MonitorManager = monitors
        # Tamanho do desktop virtual (compatível com o antigo screen_w/screen_h)
        self.screen_w, self.screen_h = self.monitors.virtual_size

        # Estado público (lido pelo HUD)
        self.mode: Mode = Mode.IDLE
        self.is_dragging: bool = False
        self.right_click_flash_until: float = 0.0
        self.double_click_flash_until: float = 0.0

        # Posição suavizada do cursor (None = ainda não inicializada)
        self._cursor: Optional[np.ndarray] = None

        # Estabilização de modo (apenas NAVIGATING / SCROLL / PAUSED)
        self._stable_mode: Mode = Mode.PAUSED
        self._candidate_mode: Mode = Mode.PAUSED
        self._candidate_count: int = 0

        # Pinça do indicador (arraste / duplo toque)
        self._pinch_phase: _Pinch = _Pinch.NONE
        self._pinch_start: float = 0.0
        self._pinch_anchor: Tuple[int, int] = (0, 0)
        self._pending_click: Optional[_PendingClick] = None

        # Pinça do clique direito (trava até a pinça abrir de novo)
        self._right_pinch_latched: bool = False
        self._last_right_click: float = -1e9

        # Pinça anelar -> duplo clique (idem)
        self._ring_pinch_latched: bool = False
        self._last_ring_double_click: float = -1e9

        # Scroll
        self._scroll_prev_y: Optional[float] = None
        self._scroll_accum: float = 0.0

        # Mão perdida
        self._lost_frames: int = 0

        # Pontos de destaque para o HUD: lista de (x, y) em px do frame
        self.highlight_points: list[Tuple[int, int]] = []

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    @property
    def display_mode(self) -> Mode:
        """Modo exibido no HUD: inclui avisos temporários (clique direito/duplo)."""
        now = self._clock()
        if now < self.double_click_flash_until:
            return Mode.DOUBLE_CLICK
        if now < self.right_click_flash_until:
            return Mode.RIGHT_CLICK
        return self.mode

    def current_monitor(self) -> Tuple[int, Monitor]:
        """Índice (0-based) e monitor onde está o cursor agora."""
        x, y = self.backend.position()
        return self.monitors.monitor_at(x, y)

    def switch_monitor(self, index: Optional[int] = None) -> bool:
        """Troca o monitor ativo (somente ``ACTIVE_SWITCH`` com 2+ monitores).

        ``index=None`` alterna ciclicamente; caso contrário escolhe o índice
        0-based. O cursor é levado ao centro do novo monitor. Ignorado durante
        uma pinça/arraste. Retorna ``True`` se houve troca.
        """
        if self.monitors.mode != MODE_ACTIVE_SWITCH or not self.monitors.is_multi:
            return False
        if self._pinch_phase is not _Pinch.NONE:
            return False
        if index is None:
            self.monitors.cycle_active()
        elif not self.monitors.set_active(index):
            return False

        cx, cy = self.monitors.active.center
        self._pending_click = None
        self.backend.moveTo(cx, cy)
        self._cursor = np.array([cx, cy], dtype=float)
        return True

    def update(self, hand: Optional[HandData], frame_w: int, frame_h: int) -> Mode:
        """Processa um quadro e executa as ações correspondentes."""
        now = self._clock()
        self._resolve_pending_click(now)
        self.highlight_points = []

        if hand is None:
            self._handle_lost_hand()
            return self.mode
        self._lost_frames = 0

        active = self._select_pinch(hand)

        # Pinças que deixaram de estar ativas são encerradas/destravadas.
        if active != "index":
            self._release_index_pinch(now)
        if active != "middle":
            self._right_pinch_latched = False
        if active != "ring":
            self._ring_pinch_latched = False

        if active == "index":
            self._handle_index_pinch(hand, now, frame_w, frame_h)
        elif active == "middle":
            self._handle_right_click(hand, now)
        elif active == "ring":
            self._handle_ring_pinch(hand, now)
        else:
            self._handle_free_gestures(hand, frame_w, frame_h)

        return self.mode

    def shutdown(self) -> None:
        """Libera qualquer botão pendente. Chamar ao encerrar o programa."""
        self._pending_click = None  # descarta toque ainda não confirmado
        if self.is_dragging:
            self._release_drag()
        else:
            # Defesa extra: garante que o botão esquerdo não ficou preso.
            try:
                self.backend.mouseUp()
            except Exception:  # noqa: BLE001 - encerramento deve ser resiliente
                pass
        self._pinch_phase = _Pinch.NONE
        self.mode = Mode.IDLE

    # ------------------------------------------------------------------
    # Seleção da pinça ativa
    # ------------------------------------------------------------------
    def _select_pinch(self, hand: HandData) -> Optional[str]:
        """Escolhe qual pinça está ativa: ``"index"``, ``"middle"``, ``"ring"`` ou ``None``.

        - A pinça já em curso tem prioridade enquanto a distância estiver
          abaixo do limiar de *abertura* (histerese).
        - Para uma pinça nova vence a de menor distância entre as que estão
          abaixo do limiar de *fechamento*.
        """
        close_thr, open_thr = self._pinch_thresholds()
        ring_close, ring_open = self._ring_thresholds()
        dists: Dict[str, Tuple[float, float, float]] = {
            "index": (hand.pinch_distance(THUMB_TIP, INDEX_TIP), close_thr, open_thr),
            "middle": (hand.pinch_distance(THUMB_TIP, MIDDLE_TIP), close_thr, open_thr),
            "ring": (hand.ring_thumb_distance(), ring_close, ring_open),
        }

        held: Optional[str] = None
        if self._pinch_phase is not _Pinch.NONE:
            held = "index"
        elif self._right_pinch_latched:
            held = "middle"
        elif self._ring_pinch_latched:
            held = "ring"
        if held is not None and dists[held][0] < dists[held][2]:
            return held

        candidates = {k: d for k, (d, close, _) in dists.items() if d < close}
        if "ring" in candidates and config.RING_PINCH_REQUIRE_OPEN_HAND:
            fingers = hand.fingers_up()
            if not (fingers["index"] or fingers["middle"] or fingers["pinky"]):
                del candidates["ring"]  # punho: não é gesto de duplo clique
        if not candidates:
            return None
        return min(candidates, key=candidates.get)

    # ------------------------------------------------------------------
    # Pinça do indicador: toque / duplo toque / arraste
    # ------------------------------------------------------------------
    def _handle_index_pinch(self, hand: HandData, now: float, fw: int, fh: int) -> None:
        self._reset_mode_stabilizer()
        self._scroll_prev_y = None

        if self._pinch_phase is _Pinch.NONE:
            self._begin_index_pinch(now)

        if self._pinch_phase is _Pinch.PENDING and now - self._pinch_start >= config.DRAG_HOLD_TIME:
            self.backend.mouseDown()  # cursor está congelado na âncora
            self.is_dragging = True
            self._pinch_phase = _Pinch.DRAGGING

        if self._pinch_phase is _Pinch.DRAGGING:
            self.mode = Mode.DRAGGING
            self._move_cursor(hand.point(INDEX_TIP), fw, fh)
        elif self._pinch_phase is _Pinch.CONSUMED:
            self.mode = Mode.DOUBLE_CLICK
        else:
            self.mode = Mode.CLICK
        self.highlight_points = [hand.point(INDEX_TIP), hand.point(THUMB_TIP)]

    def _begin_index_pinch(self, now: float) -> None:
        """Trata o instante em que a pinça do indicador fecha."""
        if not config.DOUBLE_TAP_ENABLED:
            # Comportamento anterior: mouseDown imediato.
            self.backend.mouseDown()
            self.is_dragging = True
            self._pinch_phase = _Pinch.DRAGGING
            return

        pending = self._pending_click
        if pending is not None and now < pending.deadline:
            # 2ª pinça dentro do prazo: duplo clique no ponto do 1º toque.
            self._pending_click = None
            self._fire_double_click(now, pending.anchor)
            self._pinch_phase = _Pinch.CONSUMED
            return

        pos = self.backend.position()
        self._pinch_anchor = (int(pos[0]), int(pos[1]))
        self._pinch_start = now
        self._pinch_phase = _Pinch.PENDING

    def _release_index_pinch(self, now: float) -> None:
        """Trata o instante em que a pinça do indicador abre."""
        phase = self._pinch_phase
        if phase is _Pinch.NONE:
            return
        if phase is _Pinch.DRAGGING:
            self._release_drag()
        elif phase is _Pinch.PENDING:
            # Toque curto: o clique simples espera um possível 2º toque.
            self._pending_click = _PendingClick(
                anchor=self._pinch_anchor,
                deadline=self._pinch_start + config.DOUBLE_CLICK_TIMEOUT,
            )
        self._pinch_phase = _Pinch.NONE

    def _release_drag(self) -> None:
        self.backend.mouseUp()
        self.is_dragging = False

    def _resolve_pending_click(self, now: float) -> None:
        """Envia o clique simples se o prazo do 2º toque expirou."""
        pending = self._pending_click
        if pending is not None and now >= pending.deadline:
            self._pending_click = None
            self.backend.moveTo(*pending.anchor)
            self.backend.click()

    def _fire_double_click(self, now: float, anchor: Optional[Tuple[int, int]]) -> None:
        if anchor is not None:
            self.backend.moveTo(*anchor)
            self._cursor = np.array(anchor, dtype=float)
        self.backend.doubleClick()
        self.double_click_flash_until = now + config.DOUBLE_CLICK_FLASH_S

    # ------------------------------------------------------------------
    # Demais gestos
    # ------------------------------------------------------------------
    def _handle_right_click(self, hand: HandData, now: float) -> None:
        if (
            not self._right_pinch_latched
            and now - self._last_right_click >= config.RIGHT_CLICK_DEBOUNCE_S
        ):
            self.backend.rightClick()
            self._last_right_click = now
            self.right_click_flash_until = now + 0.4
        # Trava: um mesmo gesto só dispara uma vez, mesmo mantendo a pinça.
        self._right_pinch_latched = True
        self.mode = Mode.RIGHT_CLICK
        self._reset_mode_stabilizer()
        self._scroll_prev_y = None
        self.highlight_points = [hand.point(MIDDLE_TIP), hand.point(THUMB_TIP)]

    def _handle_ring_pinch(self, hand: HandData, now: float) -> None:
        """Pinça anelar+polegar: duplo clique imediato, com trava e debounce."""
        if (
            not self._ring_pinch_latched
            and now - self._last_ring_double_click >= config.DOUBLE_CLICK_DEBOUNCE_S
        ):
            self._fire_double_click(now, anchor=None)  # no ponto atual do cursor
            self._last_ring_double_click = now
        self._ring_pinch_latched = True
        self.mode = Mode.DOUBLE_CLICK
        self._reset_mode_stabilizer()
        self._scroll_prev_y = None
        self.highlight_points = [hand.point(RING_TIP), hand.point(THUMB_TIP)]

    def _handle_free_gestures(self, hand: HandData, fw: int, fh: int) -> None:
        raw = self._classify_free_mode(hand)
        mode = self._stabilize(raw)
        self.mode = mode

        if mode is not Mode.SCROLL:
            self._scroll_prev_y = None
            self._scroll_accum = 0.0

        if mode is Mode.NAVIGATING:
            self._move_cursor(hand.point(INDEX_TIP), fw, fh)
            self.highlight_points = [hand.point(INDEX_TIP)]
        elif mode is Mode.SCROLL:
            self._do_scroll(hand)
            self.highlight_points = [hand.point(INDEX_TIP), hand.point(MIDDLE_TIP)]
        else:  # PAUSED
            # Ao pausar, o cursor será re-ancorado na próxima navegação.
            self._cursor = None

    def _handle_lost_hand(self) -> None:
        self._lost_frames += 1
        if self._lost_frames > config.LOST_HAND_TOLERANCE_FRAMES:
            if self.is_dragging:
                self._release_drag()
            # Pinça pendente/consumida é descartada (o toque já pendente continua
            # valendo e é resolvido por `_resolve_pending_click`).
            self._pinch_phase = _Pinch.NONE
            self.mode = Mode.IDLE
            self._cursor = None
            self._scroll_prev_y = None
            self._scroll_accum = 0.0
            self._right_pinch_latched = False
            self._ring_pinch_latched = False
            self._reset_mode_stabilizer()

    # ------------------------------------------------------------------
    # Classificação e estabilização
    # ------------------------------------------------------------------
    @staticmethod
    def _classify_free_mode(hand: HandData) -> Mode:
        fingers = hand.fingers_up()
        index, middle = fingers["index"], fingers["middle"]
        ring, pinky = fingers["ring"], fingers["pinky"]

        if index and middle and not ring and not pinky:
            return Mode.SCROLL
        if index and not middle and not ring and not pinky:
            return Mode.NAVIGATING
        return Mode.PAUSED

    def _stabilize(self, raw: Mode) -> Mode:
        """Exige ``MODE_CONFIRM_FRAMES`` quadros iguais para trocar de modo."""
        if raw is self._stable_mode:
            self._candidate_mode = raw
            self._candidate_count = 0
            return self._stable_mode

        if raw is self._candidate_mode:
            self._candidate_count += 1
        else:
            self._candidate_mode = raw
            self._candidate_count = 1

        if self._candidate_count >= config.MODE_CONFIRM_FRAMES:
            self._stable_mode = raw
            self._candidate_count = 0
        return self._stable_mode

    def _reset_mode_stabilizer(self) -> None:
        # Após pinça, retoma como PAUSED para exigir confirmação do próximo gesto.
        self._stable_mode = Mode.PAUSED
        self._candidate_mode = Mode.PAUSED
        self._candidate_count = 0

    @staticmethod
    def _pinch_thresholds() -> Tuple[float, float]:
        if config.USE_NORMALIZED_DISTANCE:
            return config.PINCH_CLOSE_THRESHOLD_NORM, config.PINCH_OPEN_THRESHOLD_NORM
        return config.PINCH_CLOSE_THRESHOLD_PX, config.PINCH_OPEN_THRESHOLD_PX

    @staticmethod
    def _ring_thresholds() -> Tuple[float, float]:
        if config.USE_NORMALIZED_DISTANCE:
            return config.RING_PINCH_THRESHOLD_NORM, config.RING_PINCH_OPEN_THRESHOLD_NORM
        return config.RING_PINCH_THRESHOLD_PX, config.RING_PINCH_OPEN_THRESHOLD_PX

    # ------------------------------------------------------------------
    # Movimento do cursor e scroll
    # ------------------------------------------------------------------
    def map_to_screen(self, point: Tuple[float, float], fw: int, fh: int) -> np.ndarray:
        """Mapeia um ponto do frame (px) dentro da moldura ativa para a tela.

        1. Normaliza dentro da moldura (com clamp nas bordas):
           ``u = interp(x, [m_x, fw - m_x], [0, 1])``, idem ``v``.
        2. ``MonitorManager.map_normalized(u, v)`` converte para coordenadas
           absolutas do desktop virtual (SPAN) ou do monitor ativo
           (ACTIVE_SWITCH), já com os offsets do SO.
        """
        u = np.interp(point[0], (config.FRAME_MARGIN_X, fw - config.FRAME_MARGIN_X), (0.0, 1.0))
        v = np.interp(point[1], (config.FRAME_MARGIN_Y, fh - config.FRAME_MARGIN_Y), (0.0, 1.0))
        return self.monitors.map_normalized(float(u), float(v))

    def _move_cursor(self, point: Tuple[float, float], fw: int, fh: int) -> None:
        # Cursor congelado enquanto um toque aguarda o possível 2º toque:
        # garante que o clique/duplo clique caia no ponto original.
        if self._pending_click is not None:
            return

        target = self.map_to_screen(point, fw, fh)

        if self._cursor is None:
            # Ancora na posição real atual para evitar "teletransporte".
            pos = self.backend.position()
            self._cursor = np.array([pos[0], pos[1]], dtype=float)

        # Deadzone: alvo muito próximo do cursor => ignora microtremores.
        if np.linalg.norm(target - self._cursor) < config.MIN_MOVE_PIXELS:
            return

        # LERP: pos = pos_anterior + (alvo - pos_anterior) * alpha
        new = self._cursor + (target - self._cursor) * config.SMOOTHING_FACTOR
        if np.linalg.norm(new - self._cursor) < 0.5:
            return  # passo sub-pixel: nada a mover

        # Mantém o cursor sobre uma tela válida (desktop virtual não retangular).
        cx, cy = self.monitors.clamp_to_monitors(new[0], new[1])
        self._cursor = np.array([cx, cy], dtype=float)
        self.backend.moveTo(int(round(cx)), int(round(cy)))

    def _do_scroll(self, hand: HandData) -> None:
        """Rola conforme o deslocamento vertical relativo da mão."""
        y = (hand.point(INDEX_TIP)[1] + hand.point(MIDDLE_TIP)[1]) / 2.0

        if self._scroll_prev_y is None:
            self._scroll_prev_y = y
            self._scroll_accum = 0.0
            return

        # Mão sobe (y diminui) => delta positivo => rolar para cima.
        self._scroll_accum += self._scroll_prev_y - y
        self._scroll_prev_y = y

        if abs(self._scroll_accum) < config.SCROLL_DEADZONE_PX:
            return

        amount = self._scroll_accum * config.SCROLL_SENSITIVITY
        if config.SCROLL_INVERT:
            amount = -amount
        amount = int(np.clip(amount, -config.SCROLL_MAX_STEP, config.SCROLL_MAX_STEP))
        self._scroll_accum = 0.0
        if amount != 0:
            self.backend.scroll(amount)
