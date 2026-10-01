"""
Pomocni filteri (preneti iz prvog projekta, prilagodjeni ovom zadatku).

  - OneEuroFilter : glacanje ugla sake
  - Hysteresis    : prag sa dve granice (stisak sake)
  - Dwell         : potvrda zadrzavanjem
"""

from __future__ import annotations

import math
from typing import Optional


class _LowPass:
    def __init__(self) -> None:
        self.y: Optional[float] = None

    def __call__(self, x: float, alpha: float) -> float:
        self.y = x if self.y is None else alpha * x + (1.0 - alpha) * self.y
        return self.y

    def reset(self) -> None:
        self.y = None


class OneEuroFilter:
    """Jako glaca kad vrednost miruje, popusta kad se brzo menja."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.02,
                 d_cutoff: float = 1.0) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x = _LowPass()
        self._dx = _LowPass()
        self._t_prev: Optional[float] = None
        self._x_prev: Optional[float] = None

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def reset(self) -> None:
        self._x.reset()
        self._dx.reset()
        self._t_prev = None
        self._x_prev = None

    def __call__(self, x: float, t: float) -> float:
        if self._t_prev is None:
            self._t_prev = t
            self._x_prev = x
            return self._x(x, 1.0)
        dt = t - self._t_prev
        if dt <= 0.0:
            dt = 1e-3
        self._t_prev = t
        dx = (x - (self._x_prev if self._x_prev is not None else x)) / dt
        self._x_prev = x
        edx = self._dx(dx, self._alpha(self.d_cutoff, dt))
        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self._x(x, self._alpha(cutoff, dt))


class Hysteresis:
    """Prag sa dve granice. `inverted` = pali se kad vrednost padne ispod."""

    def __init__(self, on_th: float, off_th: float, inverted: bool = False) -> None:
        self.on_th = on_th
        self.off_th = off_th
        self.inverted = inverted
        self.state = False

    def update(self, value: Optional[float]) -> bool:
        if value is None:
            return self.state
        if self.inverted:
            if not self.state and value < self.on_th:
                self.state = True
            elif self.state and value > self.off_th:
                self.state = False
        else:
            if not self.state and value > self.on_th:
                self.state = True
            elif self.state and value < self.off_th:
                self.state = False
        return self.state

    def reset(self) -> None:
        self.state = False


class Dwell:
    """Vraca (okinuto, napredak 0..1) dok je uslov neprekidno ispunjen."""

    def __init__(self, hold_time: float) -> None:
        self.hold_time = hold_time
        self._t0: Optional[float] = None
        self._fired = False

    def update(self, condition: bool, now: float):
        if not condition:
            self._t0 = None
            self._fired = False
            return False, 0.0
        if self._t0 is None:
            self._t0 = now
        progress = min(1.0, (now - self._t0) / self.hold_time) if self.hold_time > 0 else 1.0
        if not self._fired and progress >= 1.0:
            self._fired = True
            return True, 1.0
        return False, progress

    def reset(self) -> None:
        self._t0 = None
        self._fired = False
