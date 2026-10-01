"""
Detekcija ruku (preuzeto iz prethodnog projekta i prilagodjeno).

Dve razlike u odnosu na prvu fazu:

1. Ugao se NE zaokruzuje na vrednosti 0, 45, 90... Tamo je zaokruzivanje
   pomagalo da se ocitavanje lepo ispise, ovde bi rotaciju ucinilo trzavom,
   jer bi objekat naglo menjao brzinu na granicama. Potreban je neprekidan ugao.

2. Izostavljena je korekcija znaka preko palca. U ovoj primeni saka je okrenuta
   dlanom ka kameri, pa je nagib jednoznacan; korekcija bi pri delimicnom
   okretanju sake naglo promenila znak i objekat bi skrenuo na suprotnu stranu.
   Ostavljena je kao opcija (`USE_THUMB_SIGN`) radi poredjenja.

Klasa radi u posebnoj niti da detekcija ne bi usporavala iscrtavanje.
"""

from __future__ import annotations

import math
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

import cv2                      # noqa: E402
import mediapipe as mp          # noqa: E402

cv2.setNumThreads(1)

PALM_IDS = [0, 5, 9, 13, 17]
TIP_IDS = [8, 12, 16, 20]
USE_THUMB_SIGN = False


@dataclass
class HandSample:
    angle: float        # nagib sake u stepenima, 0 = uspravno
    cx: float           # centar dlana, normalizovano 0..1
    cy: float
    pinch: float        # odnos palac-kaziprst prema velicini dlana
    fist: float
    ts: float


@dataclass
class HandsFrame:
    left: Optional[HandSample] = None
    right: Optional[HandSample] = None
    ts: float = 0.0
    fps: float = 0.0


def _dist(a, b, aspect: float) -> float:
    dx = (a.x - b.x) * aspect
    dy = a.y - b.y
    return math.hypot(dx, dy)


def ugao_sake(lm) -> float:
    """Nagib sake u odnosu na vertikalu, neprekidan, u stepenima.

    Pravac se uzima od korena srednjeg prsta (tacka 9) ka njegovom vrhu
    (tacka 12). Uspravna saka daje 0, nagib udesno pozitivan ugao, ulevo
    negativan.
    """
    mcp, tip = lm[9], lm[12]
    fx, fy = tip.x - mcp.x, tip.y - mcp.y
    ugao = math.degrees(math.atan2(fx, -fy))

    if USE_THUMB_SIGN:
        wrist, thumb = lm[0], lm[4]
        tx, ty = thumb.x - wrist.x, thumb.y - wrist.y
        if fx * ty - fy * tx < 0:
            ugao = -ugao
    return ugao


def centar_dlana(lm):
    xs = [lm[i].x for i in PALM_IDS]
    ys = [lm[i].y for i in PALM_IDS]
    return sum(xs) / len(xs), sum(ys) / len(ys)


class HandTracker:
    """Kamera i MediaPipe u posebnoj niti. `get()` je neblokirajuc."""

    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self._frame = HandsFrame()
        self._preview = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self.error: Optional[str] = None
        self.cam_w = 0
        self.cam_h = 0

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def get(self) -> HandsFrame:
        with self._lock:
            return self._frame

    def preview(self):
        with self._lock:
            return self._preview

    # ------------------------------------------------------------------
    def _loop(self) -> None:
        cfg = self.cfg
        cap = cv2.VideoCapture(cfg.CAMERA_INDEX)
        if not cap.isOpened():
            self.error = "Nije moguce otvoriti web kameru."
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.CAM_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.CAM_HEIGHT)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        ok, frame = cap.read()
        if not ok:
            self.error = "Nije moguce procitati kadar sa kamere."
            cap.release()
            return
        self.cam_h, self.cam_w = frame.shape[:2]

        hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=0,
            min_detection_confidence=cfg.MIN_DET_CONF,
            min_tracking_confidence=cfg.MIN_TRK_CONF,
        )
        mp_draw = mp.solutions.drawing_utils
        mp_styles = mp.solutions.drawing_styles
        conn = mp.solutions.hands.HAND_CONNECTIONS

        t_prev = time.time()
        fps = 0.0
        try:
            while self._running:
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.01)
                    continue

                frame = cv2.flip(frame, 1)       # ogledalo, prirodnije korisniku
                h, w = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if cfg.PROC_WIDTH and w > cfg.PROC_WIDTH:
                    small = cv2.resize(rgb, (cfg.PROC_WIDTH,
                                             int(h * cfg.PROC_WIDTH / w)))
                else:
                    small = rgb
                aspect = small.shape[1] / float(small.shape[0])
                res = hands.process(small)

                now = time.time()
                out = HandsFrame(ts=now)
                preview = None
                if getattr(cfg, "SHOW_PREVIEW", False):
                    preview = cv2.resize(frame, (cfg.PREVIEW_W,
                                                 int(h * cfg.PREVIEW_W / w)))

                if res.multi_hand_landmarks and res.multi_handedness:
                    for lm_obj, handed in zip(res.multi_hand_landmarks,
                                              res.multi_handedness):
                        lm = lm_obj.landmark
                        cx, cy = centar_dlana(lm)
                        palm = _dist(lm[0], lm[9], aspect) or 1e-6
                        sample = HandSample(
                            angle=ugao_sake(lm),
                            cx=cx, cy=cy,
                            pinch=_dist(lm[4], lm[8], aspect) / palm,
                            fist=sum(_dist(lm[i], lm[0], aspect)
                                     for i in TIP_IDS) / (4.0 * palm),
                            ts=now,
                        )
                        label = handed.classification[0].label
                        if cfg.SWAP_HANDS:
                            label = "Right" if label == "Left" else "Left"
                        if label == "Left":
                            out.left = sample
                        else:
                            out.right = sample

                        if preview is not None:
                            mp_draw.draw_landmarks(
                                preview, lm_obj, conn,
                                mp_styles.get_default_hand_landmarks_style(),
                                mp_styles.get_default_hand_connections_style())

                dt = now - t_prev
                t_prev = now
                if dt > 0:
                    fps = 0.9 * fps + 0.1 * (1.0 / dt)
                out.fps = fps

                with self._lock:
                    self._frame = out
                    if preview is not None:
                        self._preview = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
        finally:
            cap.release()
            hands.close()
