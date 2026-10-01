"""
Ulazna tacka aplikacije za manipulaciju 3D objektom pokretima ruku.

Pokretanje:
    python main.py
    python main.py --camera 1      druga kamera, ako ih ima vise
    python main.py --no-preview    bez prikaza kamere u uglu

Objekat se okrece nagibom saka: desna oko uspravne ose, leva oko vodoravne.
Uspravna saka znaci da objekat miruje.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

FROZEN = getattr(sys, "frozen", False)


def radni_folder() -> str:
    """Folder u koji se upisuju snimci ekrana. Kao .exe to je folder pored
    samog .exe fajla, a ne trenutni folder komandne linije."""
    if FROZEN:
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Manipulacija 3D objektom pokretima ruku")
    ap.add_argument("--camera", type=int, default=config.CAMERA_INDEX,
                    help="redni broj kamere (podrazumevano 0)")
    ap.add_argument("--no-preview", action="store_true",
                    help="bez prikaza kamere u uglu prozora")
    args = ap.parse_args()

    try:
        os.chdir(radni_folder())
    except OSError:
        pass

    config.CAMERA_INDEX = args.camera
    if args.no_preview:
        config.SHOW_PREVIEW = False

    from sources.camera_source import CameraSource
    from ui.app import App

    App(CameraSource(config), config).run()


if __name__ == "__main__":
    main()