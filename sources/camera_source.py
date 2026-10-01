"""
KAMERA KAO ULAZ.

Prevodi nagib svake sake u brzinu rotacije.

Podela uloga:
    DESNA saka -> rotacija oko VERTIKALNE ose (objekat se okrece u mestu)
    LEVA saka  -> rotacija oko HORIZONTALNE ose (objekat se preklapa)

Obrada ide u tri koraka, svaki resava jedan konkretan problem:

  1. glacanje ugla   - sirovi ugao podrhtava nekoliko stepeni cak i kad saka
                       miruje, pa bi objekat stalno treperio;
  2. nagib u brzinu  - mrtva zona, zasicenje i kriva odziva (core/control.py);
  3. glacanje brzine - uklanja trzaje pri naglom pokretu.
"""

from __future__ import annotations

import time

from core.control import tilt_to_rate
from core.events import AxisInput, Snapshot
from core.filters import OneEuroFilter
from core.input_source import InputSource
from tracking.hand_tracker import HandTracker


class _Kanal:
    """Obrada jedne ruke: od sirovog ugla do brzine rotacije."""

    def __init__(self, cfg, invert: bool) -> None:
        self.cfg = cfg
        self.invert = invert
        self.filter_ugla = OneEuroFilter(cfg.ANGLE_MIN_CUTOFF, cfg.ANGLE_BETA)
        self.rate = 0.0
        self.angle = 0.0
        self.last_seen = 0.0

    def update(self, sample, now: float) -> AxisInput:
        cfg = self.cfg

        if sample is None:
            # ruka van kadra: posle kratkog cekanja rotacija se gasi
            if now - self.last_seen > cfg.HAND_LOST_GRACE:
                self.rate = 0.0
                self.filter_ugla.reset()
            else:
                self.rate *= 0.5
            return AxisInput(present=False, angle=self.angle, rate=self.rate)

        self.last_seen = now
        self.angle = self.filter_ugla(sample.angle, now)

        ciljna = tilt_to_rate(self.angle, cfg.DEAD_ZONE, cfg.MAX_ANGLE,
                              cfg.MAX_RATE, cfg.RATE_CURVE, self.invert)

        k = max(0.0, min(1.0, cfg.RATE_SMOOTH))
        self.rate = self.rate + (ciljna - self.rate) * (1.0 - k) if k else ciljna

        return AxisInput(present=True, angle=self.angle, rate=self.rate)


class CameraSource(InputSource):
    name = "kamera (MediaPipe)"

    def __init__(self, cfg) -> None:
        self.cfg = cfg
        self.tracker = HandTracker(cfg)
        self.desna = _Kanal(cfg, cfg.INVERT_YAW)
        self.leva = _Kanal(cfg, cfg.INVERT_PITCH)

    def start(self, app) -> None:
        self.tracker.start()

    def stop(self) -> None:
        self.tracker.stop()

    def preview(self):
        return self.tracker.preview()

    # ------------------------------------------------------------------
    def poll(self, dt: float) -> Snapshot:
        fr = self.tracker.get()
        now = time.time()

        yaw = self.desna.update(fr.right, now)
        pitch = self.leva.update(fr.left, now)

        info = {
            "fps": fr.fps,
            "right_angle": fr.right.angle if fr.right else None,
            "left_angle": fr.left.angle if fr.left else None,
            "error": self.tracker.error,
        }
        return Snapshot(yaw=yaw, pitch=pitch, commands=[], info=info)

    def status(self) -> str:
        if self.tracker.error:
            return f"KAMERA GRESKA: {self.tracker.error}"
        return "KAMERA  |  desna saka = okretanje, leva saka = preklapanje"