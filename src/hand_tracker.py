"""Wrapper do MediaPipe Hands com extração de landmarks e distâncias.

Dois backends são suportados, escolhidos automaticamente:

1. **Legado** ``mediapipe.solutions.hands`` (mediapipe <= 0.10.21, Python <= 3.12),
   que é a API pedida na especificação do projeto.
2. **Tasks API** ``HandLandmarker`` (mediapipe >= 0.10.30), usada quando
   ``mediapipe.solutions`` não existe (removida nas versões novas). Requer o
   arquivo de modelo ``hand_landmarker.task``, baixado automaticamente na
   primeira execução para ``models/``.

Ambos entregam o mesmo ``HandData`` (21 landmarks em pixels do frame).
"""

from __future__ import annotations

import math
import time
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

from . import config

# Índices dos landmarks usados (https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker)
WRIST = 0
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_TIP = 12
RING_PIP = 14
RING_TIP = 16
PINKY_PIP = 18
PINKY_TIP = 20

# Conexões dos 21 pontos para desenhar o esqueleto da mão no HUD.
HAND_CONNECTIONS: Tuple[Tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
)

_FINGER_JOINTS = {
    "index": (INDEX_PIP, INDEX_TIP),
    "middle": (MIDDLE_PIP, MIDDLE_TIP),
    "ring": (RING_PIP, RING_TIP),
    "pinky": (PINKY_PIP, PINKY_TIP),
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)


class HandData:
    """Landmarks de uma mão em pixels do frame + utilitários geométricos."""

    def __init__(self, points: Sequence[Tuple[float, float]]) -> None:
        if len(points) != 21:
            raise ValueError("HandData requer exatamente 21 landmarks.")
        self.points: List[Tuple[float, float]] = [(float(x), float(y)) for x, y in points]

    def point(self, idx: int) -> Tuple[int, int]:
        """Posição (x, y) inteira em pixels do landmark ``idx``."""
        x, y = self.points[idx]
        return int(round(x)), int(round(y))

    def distance(self, a: int, b: int) -> float:
        """Distância euclidiana 2D (px do frame) entre dois landmarks."""
        ax, ay = self.points[a]
        bx, by = self.points[b]
        return math.hypot(ax - bx, ay - by)

    def hand_size(self) -> float:
        """Escala da mão: distância punho -> base do dedo médio (px)."""
        return max(self.distance(WRIST, MIDDLE_MCP), 1e-6)

    def pinch_distance(self, a: int, b: int) -> float:
        """Distância usada nos limiares de pinça.

        Normalizada pelo tamanho da mão (independe da distância à câmera) se
        ``config.USE_NORMALIZED_DISTANCE``; caso contrário, em pixels.
        """
        d = self.distance(a, b)
        return d / self.hand_size() if config.USE_NORMALIZED_DISTANCE else d

    def ring_tip(self) -> Tuple[int, int]:
        """Posição (x, y) da ponta do anelar (landmark 16)."""
        return self.point(RING_TIP)

    def ring_thumb_distance(self) -> float:
        """Distância Euclidiana ponta do anelar (16) <-> ponta do polegar (4).

        Mesma unidade de ``pinch_distance`` (normalizada ou em px).
        """
        return self.pinch_distance(THUMB_TIP, RING_TIP)

    def fingers_up(self) -> Dict[str, bool]:
        """Indica quais dedos (indicador..mínimo) estão esticados.

        Um dedo está esticado se a ponta está mais longe do punho do que a
        articulação PIP (com folga). Isso é invariante à rotação da mão,
        diferente de comparar apenas a coordenada Y.
        """
        result: Dict[str, bool] = {}
        for name, (pip, tip) in _FINGER_JOINTS.items():
            result[name] = self.distance(WRIST, tip) > self.distance(WRIST, pip) * 1.1
        return result


def _legacy_available() -> bool:
    try:
        import mediapipe as mp

        return hasattr(mp, "solutions") and hasattr(mp.solutions, "hands")
    except ImportError:
        return False


def _ensure_model(path: Path = MODEL_PATH) -> Path:
    """Garante a existência do modelo da Tasks API, baixando se necessário."""
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"[HandTracker] Baixando modelo para {path} ...")
    tmp = path.with_suffix(".tmp")
    try:
        urllib.request.urlretrieve(MODEL_URL, tmp)  # noqa: S310 - URL fixa e confiável
        tmp.replace(path)
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            f"Falha ao baixar o modelo ({exc}). Baixe manualmente de {MODEL_URL} "
            f"e salve em {path}."
        ) from exc
    return path


class HandTracker:
    """Detecta uma mão por quadro e devolve ``HandData`` (ou ``None``)."""

    def __init__(self) -> None:
        import mediapipe as mp

        self._mp = mp
        self._backend = "legacy" if _legacy_available() else "tasks"
        self._start = time.monotonic()
        self._last_ts_ms = -1

        if self._backend == "legacy":
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=config.MAX_NUM_HANDS,
                model_complexity=config.MODEL_COMPLEXITY,
                min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            )
        else:
            from mediapipe.tasks.python import BaseOptions, vision

            model = _ensure_model()
            options = vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(model)),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=config.MAX_NUM_HANDS,
                min_hand_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_hand_presence_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            )
            self._landmarker = vision.HandLandmarker.create_from_options(options)

    @property
    def backend(self) -> str:
        return self._backend

    def process(self, frame_bgr: np.ndarray) -> Optional[HandData]:
        """Processa um frame BGR (já espelhado) e retorna a mão detectada."""
        h, w = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        if self._backend == "legacy":
            rgb.flags.writeable = False  # evita cópia interna
            res = self._hands.process(rgb)
            if not res.multi_hand_landmarks:
                return None
            lms = res.multi_hand_landmarks[0].landmark
        else:
            image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
            ts = int((time.monotonic() - self._start) * 1000)
            ts = max(ts, self._last_ts_ms + 1)  # timestamps estritamente crescentes
            self._last_ts_ms = ts
            res = self._landmarker.detect_for_video(image, ts)
            if not res.hand_landmarks:
                return None
            lms = res.hand_landmarks[0]

        return HandData([(lm.x * w, lm.y * h) for lm in lms])

    def close(self) -> None:
        """Libera os recursos do MediaPipe."""
        if self._backend == "legacy":
            self._hands.close()
        else:
            self._landmarker.close()
