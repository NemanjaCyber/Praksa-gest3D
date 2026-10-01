"""
Glavna aplikacija: prozor, petlja i spajanje ulaza sa 3D prikazom.

Aplikacija od izvora ulaza dobija Snapshot sa dve brzine rotacije i spiskom
komandi, i to je sve sto joj treba. Ne zna nista o kameri ni o detekciji.
"""

from __future__ import annotations

import os
import time

import pygame

from core.control import Orientation
from core.events import Command, Snapshot
from core.model import podrazumevani_model, ucitaj_model
from ui.renderer import Renderer

# Svaki red je par (levo, desno); samo levo znaci naslov odeljka, a None
# prazan red. Dve kolone se crtaju na odvojenim polozajima, pa se poravnanje
# ne oslanja na razmake u tekstu.
POMOC = [
    ("Upravljanje rukama", None),
    ("desna saka nagnuta levo ili desno", "okrece objekat oko vertikalne ose"),
    ("leva saka nagnuta levo ili desno", "okrece objekat oko horizontalne ose"),
    ("saka uspravno, dlanom ka kameri", "objekat miruje"),
    ("", ""),
    ("Tasteri", None),
    ("r", "pocetni polozaj"),
    ("o", "ucitaj drugi model"),
    ("f", "zicani prikaz"),
    ("x", "prikaz osa"),
    ("g", "prikaz mreze"),
    ("p", "automatsko okretanje"),
    ("space", "zamrzni ulaz"),
    ("s", "snimi sliku"),
    ("h", "pomoc"),
    ("Esc", "izlaz"),
]

TASTERI = {
    pygame.K_r: Command.RESET,
    pygame.K_o: Command.LOAD,
    pygame.K_f: Command.WIREFRAME,
    pygame.K_x: Command.AXES,
    pygame.K_SPACE: Command.FREEZE,
    pygame.K_p: Command.SPIN,
    pygame.K_h: Command.HELP,
    pygame.K_ESCAPE: Command.QUIT,
}


class App:
    def __init__(self, source, cfg) -> None:
        self.cfg = cfg
        self.source = source
        self.width = cfg.WIN_W
        self.height = cfg.WIN_H

        pygame.init()
        pygame.display.set_caption("Manipulacija 3D objektom pokretima ruku")
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)
        try:
            self.screen = pygame.display.set_mode(
                (self.width, self.height),
                pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)
        except pygame.error:
            # neke graficke kartice ne podrzavaju vise uzoraka
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 0)
            pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 0)
            self.screen = pygame.display.set_mode(
                (self.width, self.height),
                pygame.DOUBLEBUF | pygame.OPENGL | pygame.RESIZABLE)

        self.clock = pygame.time.Clock()
        self.renderer = Renderer(cfg, self.width, self.height)
        self.renderer.resize(self.width, self.height)

        self.orientation = Orientation(cfg.CLAMP_PITCH, cfg.PITCH_LIMIT,
                                       cfg.START_YAW, cfg.START_PITCH)
        self.model_name = ""
        self._ucitaj("")

        self.freeze = False
        self.auto_spin = False
        self.show_help = False
        self.running = True
        self.status = "spremno"
        self._status_t = time.time()

        self.source.start(self)

    # ============================== MODEL ==============================
    def _ucitaj(self, path: str) -> None:
        if path:
            try:
                mesh = ucitaj_model(path)
            except (OSError, ValueError) as exc:
                mesh = podrazumevani_model()
                self.renderer.set_mesh(mesh)
                self.model_name = mesh.name
                self._poruka(f"greska pri ucitavanju: {exc}")
                return
        else:
            mesh = podrazumevani_model()

        self.renderer.set_mesh(mesh)
        self.model_name = mesh.name
        self._poruka(f"{mesh.name}  ({mesh.broj_trouglova} trouglova)")

    def _izaberi_model(self) -> None:
        """Dijalog za izbor fajla. Kamera i dalje radi u svojoj niti."""
        try:
            import tkinter as tk
            from tkinter import filedialog
            koren = tk.Tk()
            koren.withdraw()
            path = filedialog.askopenfilename(
                title="Izaberi 3D model",
                filetypes=[("3D modeli", "*.obj *.stl *.ply *.glb *.gltf"),
                           ("Svi fajlovi", "*.*")])
            koren.destroy()
        except Exception:
            self._poruka("dijalog za izbor fajla nije dostupan")
            return
        if path:
            self._ucitaj(path)

    # ============================== PETLJA =============================
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(self.cfg.UI_FPS) / 1000.0
            dt = min(dt, 0.1)                 # zastita od skoka posle zastoja

            self._dogadjaji()
            snap = self.source.poll(dt)
            self._primeni(snap, dt)
            self._crtaj(snap)
            pygame.display.flip()

        self.source.stop()
        pygame.quit()

    def _dogadjaji(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.width, self.height = event.w, event.h
                self.renderer.resize(event.w, event.h)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    self.renderer.show_grid = not self.renderer.show_grid
                elif event.key == pygame.K_s:
                    self._snimi_sliku()
                elif event.key in TASTERI:
                    self._komanda(TASTERI[event.key])

    # ============================== LOGIKA =============================
    def _primeni(self, snap: Snapshot, dt: float) -> None:
        for cmd in snap.commands:
            self._komanda(cmd)

        if self.freeze:
            return

        yaw_rate = snap.yaw.rate
        pitch_rate = snap.pitch.rate
        if self.auto_spin:
            yaw_rate += self.cfg.AUTO_SPIN_RATE
        self.orientation.update(yaw_rate, pitch_rate, dt)

    def _komanda(self, cmd: Command) -> None:
        if cmd is Command.RESET:
            self.orientation.reset()
            self._poruka("pocetni polozaj")
        elif cmd is Command.LOAD:
            self._izaberi_model()
        elif cmd is Command.WIREFRAME:
            self.renderer.wireframe = not self.renderer.wireframe
            self._poruka("zicani prikaz" if self.renderer.wireframe else "pun prikaz")
        elif cmd is Command.AXES:
            self.renderer.show_axes = not self.renderer.show_axes
        elif cmd is Command.FREEZE:
            self.freeze = not self.freeze
            self._poruka("ulaz zamrznut" if self.freeze else "ulaz aktivan")
        elif cmd is Command.SPIN:
            self.auto_spin = not self.auto_spin
            self._poruka("automatsko okretanje" if self.auto_spin else "rucno")
        elif cmd is Command.HELP:
            self.show_help = not self.show_help
        elif cmd is Command.QUIT:
            self.running = False

    def _poruka(self, tekst: str) -> None:
        self.status = tekst
        self._status_t = time.time()

    def _snimi_sliku(self) -> None:
        from OpenGL.GL import GL_RGB, GL_UNSIGNED_BYTE, glReadPixels
        os.makedirs(self.cfg.SCREENSHOT_DIR, exist_ok=True)
        podaci = glReadPixels(0, 0, self.width, self.height, GL_RGB,
                              GL_UNSIGNED_BYTE)
        surf = pygame.image.fromstring(podaci, (self.width, self.height), "RGB")
        surf = pygame.transform.flip(surf, False, True)
        ime = time.strftime("snimak_%Y%m%d_%H%M%S.png")
        putanja = os.path.join(self.cfg.SCREENSHOT_DIR, ime)
        pygame.image.save(surf, putanja)
        self._poruka(f"snimljeno: {ime}")

    # ============================== CRTANJE ============================
    def _crtaj(self, snap: Snapshot) -> None:
        self.renderer.draw_scene(self.orientation)
        self.renderer.begin_2d()

        self._hud(snap)
        self._pokazivaci(snap)

        frame = self.source.preview()
        if frame is not None and self.cfg.SHOW_PREVIEW:
            self.renderer.preview(frame, self.width - frame.shape[1] - 14, 14)

        if self.show_help:
            self._pomoc()

        self.renderer.end_2d()

    def _hud(self, snap: Snapshot) -> None:
        r = self.renderer

        r.tekst(f"Okretanje oko vertikalne ose (Y): {self.orientation.yaw:.1f}°", 16, 64)
        r.tekst(f"Okretanje oko horizontalne ose (X): {self.orientation.pitch:.1f}°", 16, 88)

        delovi = [f"{self.clock.get_fps():.0f} fps"]
        if snap.info.get("fps"):
            delovi.append(f"kamera {snap.info['fps']:.0f} fps")
        if self.freeze:
            delovi.append("ZAMRZNUTO")
        if self.auto_spin:
            delovi.append("auto")
        if time.time() - self._status_t < 4.0:
            delovi.append(self.status)
        r.tekst("   |   ".join(delovi), 16, self.height - 48, mali=True,
                boja=(140, 155, 180))
        r.tekst("h = pomoc     Esc = izlaz", 16, self.height - 28, mali=True,
                boja=(95, 108, 130))

    def _pokazivaci(self, snap: Snapshot) -> None:
        """Dve skale koje pokazuju nagib svake sake i mrtvu zonu."""
        r = self.renderer
        poluprecnik = 54.0
        y = self.height - 96.0
        r.pokazivac_nagiba(self.width / 2 - 150, y, poluprecnik,
                           snap.pitch.angle, snap.pitch.present,
                           snap.pitch.locked, "Leva - okretanje oko horizontalne ose",
                           boja=(0.45, 0.78, 0.60))
        r.pokazivac_nagiba(self.width / 2 + 150, y, poluprecnik,
                           snap.yaw.angle, snap.yaw.present,
                           snap.yaw.locked, "Desna - okretanje oko vertikalne ose",
                           boja=(0.45, 0.70, 0.95))

    def _pomoc(self) -> None:
        r = self.renderer
        w = min(620, self.width - 60)
        h = min(len(POMOC) * 23 + 70, self.height - 60)
        x = (self.width - w) / 2
        y = (self.height - h) / 2
        r.pravougaonik(x, y, w, h)
        r.tekst("Pomoc", x + 26, y + 18, boja=(238, 242, 250))

        kolona2 = x + 26 + min(300, w * 0.46)
        red = y + 54
        for levo, desno in POMOC:
            if desno is None:
                r.tekst(levo, x + 26, red, boja=(205, 216, 236))
            elif levo or desno:
                r.tekst(levo, x + 38, red, mali=True, boja=(168, 182, 206))
                r.tekst(desno, kolona2, red, mali=True, boja=(142, 156, 180))
            red += 23