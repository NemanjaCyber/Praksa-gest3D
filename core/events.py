"""
Zajednicki tipovi podataka izmedju ULAZA (mis/tastatura ili kamera) i
APLIKACIJE (3D prikaz).

Ista ideja kao u prethodnom projektu: aplikacija ne zna odakle dolazi ulaz.
Razlika je u tome sta ulaz nosi - ovde nije pozicija kursora nego ugao
nagiba svake sake i brzina rotacije koju taj nagib zadaje.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Command(Enum):
    """Diskretne komande. U emulatoru ih daje tastatura, sa kamere stisak
    sake zadrzan odredjeno vreme."""

    RESET = "reset"             # vrati objekat u pocetni polozaj
    LOAD = "load"               # ucitaj drugi 3D model
    WIREFRAME = "wireframe"     # zicani prikaz
    AXES = "axes"               # prikaz osa
    FREEZE = "freeze"           # privremeno zamrzni ulaz
    SPIN = "spin"               # automatsko okretanje (za demonstraciju)
    HELP = "help"
    QUIT = "quit"


@dataclass
class AxisInput:
    """Stanje jedne sake i rotacija koju ona zadaje.

    `angle`  - nagib sake u stepenima, 0 = uspravno (objekat miruje)
    `rate`   - brzina rotacije u stepenima u sekundi koju taj nagib zadaje
    `locked` - saka je stisnuta: rotacija se pauzira, gest sluzi za komandu
    """

    present: bool = False
    angle: float = 0.0
    rate: float = 0.0
    locked: bool = False
    hold_progress: float = 0.0      # 0..1 napredak drzanja stiska


@dataclass
class Snapshot:
    """Jedno ocitavanje ulaza.

    `yaw`   - DESNA saka, rotacija oko vertikalne ose 
    `pitch` - LEVA saka, rotacija oko horizontalne ose
    """

    yaw: AxisInput = field(default_factory=AxisInput)
    pitch: AxisInput = field(default_factory=AxisInput)
    commands: List[Command] = field(default_factory=list)
    info: Dict[str, Any] = field(default_factory=dict)

    def any_hand(self) -> bool:
        return self.yaw.present or self.pitch.present
