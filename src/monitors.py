"""Detecção e mapeamento de múltiplos monitores.

* ``detect_monitors`` enumera os monitores com ``screeninfo`` (posição ``x, y``
  e tamanho ``width, height`` no desktop virtual do SO). Se a biblioteca não
  estiver instalada, falhar ou o sistema tiver um único monitor, cai de forma
  suave para um monitor único ``(0, 0, largura, altura)``.
* ``MonitorManager`` converte coordenadas normalizadas ``(u, v) ∈ [0, 1]``
  (posição do dedo dentro da moldura ativa) em coordenadas de tela que
  respeitam os offsets do SO (inclusive negativos, p.ex. monitor à esquerda
  do primário), segundo o modo ``config.MULTI_MONITOR_MODE``:

  - ``SPAN``: ``(u, v)`` cobre todo o bounding box do desktop virtual.
  - ``ACTIVE_SWITCH``: ``(u, v)`` cobre apenas o monitor ativo (1:1); o
    monitor ativo é trocado com ``cycle_active`` / ``set_active``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from . import config

MODE_SPAN = "SPAN"
MODE_ACTIVE_SWITCH = "ACTIVE_SWITCH"
VALID_MODES = (MODE_SPAN, MODE_ACTIVE_SWITCH)


@dataclass(frozen=True)
class Monitor:
    """Retângulo de um monitor no desktop virtual (px, origem no primário)."""

    x: int
    y: int
    width: int
    height: int
    is_primary: bool = False
    name: str = ""

    @property
    def right(self) -> int:
        """Borda direita (exclusiva)."""
        return self.x + self.width

    @property
    def bottom(self) -> int:
        """Borda inferior (exclusiva)."""
        return self.y + self.height

    @property
    def center(self) -> Tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.right - 1 and self.y <= py <= self.bottom - 1

    def clamp(self, px: float, py: float) -> Tuple[float, float]:
        """Ponto do monitor mais próximo de ``(px, py)``."""
        return (
            min(max(px, self.x), self.right - 1),
            min(max(py, self.y), self.bottom - 1),
        )


def _enable_dpi_awareness() -> None:
    """Garante coordenadas em pixels físicos (as mesmas do pyautogui)."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001 - melhor esforço
            pass


def _from_override(raw: Sequence) -> List[Monitor]:
    monitors: List[Monitor] = []
    for i, item in enumerate(raw):
        try:
            x, y, w, h = (int(v) for v in item)
        except (TypeError, ValueError):
            print(f"[Monitores] MONITORS_OVERRIDE[{i}] inválido ({item!r}); ignorado.")
            continue
        if w <= 0 or h <= 0:
            print(f"[Monitores] MONITORS_OVERRIDE[{i}] com tamanho inválido; ignorado.")
            continue
        monitors.append(Monitor(x, y, w, h, is_primary=(x == 0 and y == 0)))
    return monitors


def _from_screeninfo() -> List[Monitor]:
    from screeninfo import get_monitors

    _enable_dpi_awareness()
    return [
        Monitor(
            int(m.x), int(m.y), int(m.width), int(m.height),
            bool(getattr(m, "is_primary", False)), m.name or "",
        )
        for m in get_monitors()
        if m.width and m.height
    ]


def detect_monitors(fallback_size: Tuple[int, int]) -> List[Monitor]:
    """Lista os monitores, ordenados da esquerda para a direita (x, depois y).

    Ordem de prioridade: ``config.MONITORS_OVERRIDE`` > ``screeninfo`` >
    monitor único ``(0, 0, *fallback_size)``.
    """
    monitors: List[Monitor] = []

    if config.MONITORS_OVERRIDE:
        monitors = _from_override(config.MONITORS_OVERRIDE)

    if not monitors:
        try:
            monitors = _from_screeninfo()
        except Exception as exc:  # noqa: BLE001 - ImportError, ScreenInfoError, etc.
            print(f"[Monitores] Detecção via screeninfo indisponível ({exc}); usando monitor único.")
            monitors = []

    if not monitors:
        monitors = [Monitor(0, 0, int(fallback_size[0]), int(fallback_size[1]), True)]

    return sorted(monitors, key=lambda m: (m.x, m.y))


class MonitorManager:
    """Estado e mapeamento do desktop virtual."""

    def __init__(
        self,
        monitors: Sequence[Monitor],
        mode: Optional[str] = None,
        default_index: Optional[int] = None,
    ) -> None:
        if not monitors:
            raise ValueError("MonitorManager requer ao menos um monitor.")
        self.monitors: List[Monitor] = list(monitors)

        mode = (mode or config.MULTI_MONITOR_MODE or MODE_SPAN).upper()
        if mode not in VALID_MODES:
            print(f"[Monitores] MULTI_MONITOR_MODE '{mode}' inválido; usando {MODE_SPAN}.")
            mode = MODE_SPAN
        self.mode: str = mode

        self.virtual_bounds: Tuple[int, int, int, int] = (
            min(m.x for m in self.monitors),
            min(m.y for m in self.monitors),
            max(m.right for m in self.monitors),
            max(m.bottom for m in self.monitors),
        )

        primary = next((i for i, m in enumerate(self.monitors) if m.is_primary), 0)
        if default_index is None:
            default_index = config.DEFAULT_MONITOR_INDEX
        if default_index is None:
            self._active = primary
        elif 0 <= default_index < len(self.monitors):
            self._active = default_index
        else:
            print(f"[Monitores] DEFAULT_MONITOR_INDEX={default_index} fora do intervalo; usando o primário.")
            self._active = primary

    @classmethod
    def from_config(cls, fallback_size: Tuple[int, int]) -> "MonitorManager":
        return cls(detect_monitors(fallback_size))

    # ------------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.monitors)

    @property
    def is_multi(self) -> bool:
        return len(self.monitors) > 1

    @property
    def virtual_size(self) -> Tuple[int, int]:
        x0, y0, x1, y1 = self.virtual_bounds
        return x1 - x0, y1 - y0

    @property
    def active_index(self) -> int:
        return self._active

    @property
    def active(self) -> Monitor:
        return self.monitors[self._active]

    def set_active(self, index: int) -> bool:
        if 0 <= index < len(self.monitors):
            self._active = index
            return True
        return False

    def cycle_active(self) -> int:
        self._active = (self._active + 1) % len(self.monitors)
        return self._active

    # ------------------------------------------------------------------
    def map_normalized(self, u: float, v: float) -> np.ndarray:
        """``(u, v) ∈ [0, 1]`` -> coordenadas absolutas do desktop virtual.

        SPAN:          X = x_min + u·(W_virtual - 1),  Y = y_min + v·(H_virtual - 1)
        ACTIVE_SWITCH: X = m.x   + u·(m.width  - 1),   Y = m.y   + v·(m.height   - 1)

        No SPAN o resultado é ajustado ao monitor mais próximo, pois o
        bounding box pode conter áreas sem tela (monitores com alturas ou
        alinhamentos diferentes).
        """
        u = min(max(float(u), 0.0), 1.0)
        v = min(max(float(v), 0.0), 1.0)

        if self.mode == MODE_ACTIVE_SWITCH:
            m = self.active
            return np.array([m.x + u * (m.width - 1), m.y + v * (m.height - 1)], dtype=float)

        x0, y0, x1, y1 = self.virtual_bounds
        x = x0 + u * (x1 - x0 - 1)
        y = y0 + v * (y1 - y0 - 1)
        return np.array(self.clamp_to_monitors(x, y), dtype=float)

    def clamp_to_monitors(self, x: float, y: float) -> Tuple[float, float]:
        """Mantém o ponto sobre alguma tela (no modo ACTIVE_SWITCH, a ativa)."""
        if self.mode == MODE_ACTIVE_SWITCH:
            return self.active.clamp(x, y)
        best: Optional[Tuple[float, float]] = None
        best_d = float("inf")
        for m in self.monitors:
            if m.contains(x, y):
                return float(x), float(y)
            cx, cy = m.clamp(x, y)
            d = (cx - x) ** 2 + (cy - y) ** 2
            if d < best_d:
                best, best_d = (cx, cy), d
        assert best is not None
        return best

    def monitor_at(self, x: float, y: float) -> Tuple[int, Monitor]:
        """Índice (0-based) e monitor que contém (ou está mais próximo de) o ponto."""
        best_i, best_d = 0, float("inf")
        for i, m in enumerate(self.monitors):
            cx, cy = m.clamp(x, y)
            d = (cx - x) ** 2 + (cy - y) ** 2
            if d < best_d:
                best_i, best_d = i, d
                if d == 0:
                    break
        return best_i, self.monitors[best_i]

    def label(self, index: int) -> str:
        """Texto do HUD, ex.: ``2 [1920x1080]`` (numeração a partir de 1)."""
        m = self.monitors[index]
        return f"{index + 1} [{m.width}x{m.height}]"
