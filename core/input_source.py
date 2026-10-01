"""
Apstraktni izvor ulaza. Aplikacija radi iskljucivo preko njega, pa ne zna
nista o kameri ni o detekciji ruku.
"""

from __future__ import annotations

from core.events import Snapshot


class InputSource:
    name = "base"

    def start(self, app) -> None:
        """Poziva se jednom pre glavne petlje."""

    def poll(self, dt: float) -> Snapshot:
        """Trenutno stanje ulaza. `dt` je vreme proteklo od prethodnog poziva."""
        raise NotImplementedError

    def stop(self) -> None:
        """Ciscenje resursa."""

    def preview(self):
        """Opciono: poslednji kadar kamere (RGB niz) ili None."""
        return None

    def status(self) -> str:
        return self.name