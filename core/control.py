"""
SRZ TEHNIKE OVOG PROJEKTA: pretvaranje nagiba sake u rotaciju objekta.

Polazna zamisao korisnika:
  - saka otvorena ka kameri i uspravna  -> objekat miruje
  - saka nagnuta levo ili desno         -> objekat se okrece na tu stranu

Iz toga sledi da nagib ne zadaje UGAO objekta nego BRZINU njegovog okretanja
(upravljanje tipa dzojstik). Nagni i drzi - objekat se okrece; vrati saku
uspravno - objekat stane u zatecenom polozaju. Tako se objekat moze okrenuti
za proizvoljan ugao, iako saka ima ogranicen opseg nagiba.

Preslikavanje nagiba u brzinu ima tri dela:

  1. MRTVA ZONA   - mali nagibi se ignorisu. Saka nikad nije savrseno uspravna,
                    pa bi bez mrtve zone objekat stalno lagano plutao.
  2. ZASICENJE    - iznad gornje granice brzina vise ne raste. Sprecava da
                    slucajan nagli pokret zavrti objekat nekontrolisano.
  3. KRIVA ODZIVA - izmedju te dve granice veza nije linearna nego stepena.
                    Mali nagibi daju vrlo male brzine (fino dotericanje),
                    veliki nagibi brzo okretanje (grubo razgledanje).
"""

from __future__ import annotations


def tilt_to_rate(angle: float, dead_zone: float, max_angle: float,
                 max_rate: float, curve: float = 1.6,
                 invert: bool = False) -> float:
    """Nagib sake (stepeni) -> brzina rotacije (stepeni u sekundi).

    >>> tilt_to_rate(0.0, 12.0, 70.0, 120.0)        # uspravna saka
    0.0
    >>> tilt_to_rate(8.0, 12.0, 70.0, 120.0)        # unutar mrtve zone
    0.0
    >>> round(tilt_to_rate(70.0, 12.0, 70.0, 120.0))   # puno zasicenje
    120
    >>> round(tilt_to_rate(-90.0, 12.0, 70.0, 120.0))  # preko granice, isto
    -120
    """
    smer = 1.0 if angle >= 0.0 else -1.0
    velicina = abs(angle)

    if velicina <= dead_zone:
        return 0.0

    raspon = max(1e-6, max_angle - dead_zone)
    t = (velicina - dead_zone) / raspon
    t = min(1.0, max(0.0, t))           # zasicenje
    t = t ** curve                      # kriva odziva

    rate = smer * t * max_rate
    return -rate if invert else rate


def normalizuj_ugao(a: float) -> float:
    """Svodi ugao na opseg (-180, 180]. Koristi se da se nagomilana
    rotacija ne pretvori u ogroman broj posle duzeg rada."""
    a = (a + 180.0) % 360.0 - 180.0
    return a + 360.0 if a <= -180.0 else a


class Orientation:
    """Trenutni polozaj objekta: dva ugla koja se vremenom nagomilavaju.

    `yaw`   - oko vertikalne ose (desna saka)
    `pitch` - oko horizontalne ose (leva saka)
    """

    def __init__(self, clamp_pitch: bool = False, pitch_limit: float = 89.0,
                 start_yaw: float = 0.0, start_pitch: float = 0.0) -> None:
        self.start_yaw = start_yaw
        self.start_pitch = start_pitch
        self.yaw = start_yaw
        self.pitch = start_pitch
        self.clamp_pitch = clamp_pitch
        self.pitch_limit = pitch_limit

    def reset(self) -> None:
        self.yaw = self.start_yaw
        self.pitch = self.start_pitch

    def update(self, yaw_rate: float, pitch_rate: float, dt: float) -> None:
        """Brzina pomnozena proteklim vremenom daje prirastaj ugla.

        Mnozenje sa `dt` je ono sto rotaciju cini nezavisnom od broja slika u
        sekundi: na brzem i na sporijem racunaru isti nagib daje isto okretanje.
        """
        self.yaw = normalizuj_ugao(self.yaw + yaw_rate * dt)
        pitch = self.pitch + pitch_rate * dt
        if self.clamp_pitch:
            self.pitch = max(-self.pitch_limit, min(self.pitch_limit, pitch))
        else:
            self.pitch = normalizuj_ugao(pitch)