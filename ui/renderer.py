"""
Iscrtavanje: OpenGL kroz pygame prozor.

Namerno je koriscen jednostavan, siroko podrzan deo OpenGL-a (nizovi temena i
ugradjeno osvetljenje) umesto sejdera. Razlog je sto se u radu objasnjavaju
MATRICE ROTACIJE, a ne tehnike sencenja: ovako je svaki korak od ugla do
slike na ekranu vidljiv u tri poziva (glRotatef, glRotatef, glDrawArrays).
"""

from __future__ import annotations

import math
from typing import Dict, Optional, Tuple

import numpy as np
import pygame
from OpenGL.GL import *          # noqa: F401,F403


def matrica_perspektive(fov_deg: float, aspect: float, near: float,
                        far: float) -> np.ndarray:
    """Matrica perspektivne projekcije, ista kao gluPerspective.

    Pisana rucno namerno: biblioteka GLU nije svuda instalirana, a za rad je
    korisno da se vidi odakle dolazi projekcija, posto su matrice tema rada.

        f = 1 / tan(fov / 2)

        | f/aspect  0            0                      0 |
        |    0      f            0                      0 |
        |    0      0  (far+near)/(near-far)  2*far*near/(near-far) |
        |    0      0           -1                      0 |
    """
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    m = np.zeros((4, 4), dtype=np.float32)
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2.0 * far * near) / (near - far)
    m[3, 2] = -1.0
    # OpenGL cita matrice po kolonama, pa se salje transponovana
    return np.ascontiguousarray(m.T)


class Renderer:
    def __init__(self, cfg, width: int, height: int) -> None:
        self.cfg = cfg
        self.width = width
        self.height = height
        self.wireframe = cfg.WIREFRAME
        self.show_axes = cfg.SHOW_AXES
        self.show_grid = cfg.SHOW_GRID

        self._verts: Optional[np.ndarray] = None
        self._norms: Optional[np.ndarray] = None
        self._broj_temena = 0

        self._tex_cache: Dict[str, Tuple[int, int, int]] = {}
        self._preview_tex: Optional[int] = None
        self._preview_size = (0, 0)

        # Obican sistemski font interfejsa (na Windows-u Segoe UI), ne monospace.
        self._font = pygame.font.SysFont("segoeui,tahoma,arial", 17)
        self._font_small = pygame.font.SysFont("segoeui,tahoma,arial", 14)

        self._init_gl()

    # ============================ POSTAVKA ============================
    def _init_gl(self) -> None:
        cfg = self.cfg
        glClearColor(*cfg.BG_COLOR)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)
        glEnable(GL_NORMALIZE)
        glShadeModel(GL_SMOOTH if cfg.SMOOTH_SHADING else GL_FLAT)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [1.2, 1.5, 2.0, 0.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.95, 0.95, 0.95, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.22, 0.23, 0.26, 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [0.45, 0.45, 0.45, 1.0])

        glEnable(GL_LIGHT1)      # slabo svetlo sa druge strane, protiv crnih zona
        glLightfv(GL_LIGHT1, GL_POSITION, [-1.5, -0.6, -1.0, 0.0])
        glLightfv(GL_LIGHT1, GL_DIFFUSE, [0.25, 0.26, 0.32, 1.0])
        glLightfv(GL_LIGHT1, GL_AMBIENT, [0.0, 0.0, 0.0, 1.0])

        glEnable(GL_COLOR_MATERIAL)
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.35, 0.35, 0.35, 1.0])
        glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 32.0)

    def resize(self, width: int, height: int) -> None:
        self.width = max(1, width)
        self.height = max(1, height)
        glViewport(0, 0, self.width, self.height)

    def set_mesh(self, mesh) -> None:
        verts, norms = mesh.build_arrays(self.cfg.SMOOTH_SHADING)
        self._verts = verts
        self._norms = norms
        self._broj_temena = int(verts.shape[0])

    # ============================ 3D SCENA ============================
    def draw_scene(self, orientation) -> None:
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glLoadMatrixf(matrica_perspektive(
            self.cfg.FOV, self.width / float(self.height), 0.05, 50.0))

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        # posmatrac je ispred objekta i malo iznad njega
        glTranslatef(0.0, 0.0, -self.cfg.CAMERA_DIST)
        glRotatef(self.cfg.CAMERA_ELEV, 1.0, 0.0, 0.0)

        if self.show_grid:
            self._draw_grid()

        glPushMatrix()
        # REDOSLED JE BITAN: prvo preklapanje oko horizontalne ose (leva saka),
        # pa okretanje oko vertikalne (desna saka). Tako se objekat uvek okrece
        # oko svoje uspravne ose, kao da stoji na gramofonskoj ploci.
        glRotatef(orientation.pitch, 1.0, 0.0, 0.0)
        glRotatef(orientation.yaw, 0.0, 1.0, 0.0)

        if self.show_axes:
            self._draw_axes()
        self._draw_model()
        glPopMatrix()

    def _draw_model(self) -> None:
        if self._verts is None or self._broj_temena == 0:
            return
        glEnable(GL_LIGHTING)
        glColor3f(*self.cfg.MODEL_COLOR)
        if self.wireframe:
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glLineWidth(1.0)
        else:
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_NORMAL_ARRAY)
        glVertexPointer(3, GL_FLOAT, 0, self._verts)
        glNormalPointer(GL_FLOAT, 0, self._norms)
        glDrawArrays(GL_TRIANGLES, 0, self._broj_temena)
        glDisableClientState(GL_NORMAL_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)

        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

    def _draw_axes(self, duzina: float = 0.75) -> None:
        glDisable(GL_LIGHTING)
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glColor3f(0.90, 0.35, 0.35)      # X
        glVertex3f(0, 0, 0); glVertex3f(duzina, 0, 0)
        glColor3f(0.40, 0.85, 0.50)      # Y - osa oko koje okrece desna saka
        glVertex3f(0, 0, 0); glVertex3f(0, duzina, 0)
        glColor3f(0.40, 0.60, 0.95)      # Z
        glVertex3f(0, 0, 0); glVertex3f(0, 0, duzina)
        glEnd()
        glEnable(GL_LIGHTING)

    def _draw_grid(self, polovina: float = 1.6, korak: float = 0.2) -> None:
        glDisable(GL_LIGHTING)
        glLineWidth(1.0)
        glColor4f(0.25, 0.28, 0.34, 1.0)
        y = -0.75
        glBegin(GL_LINES)
        n = int(polovina / korak)
        for i in range(-n, n + 1):
            x = i * korak
            glVertex3f(x, y, -polovina); glVertex3f(x, y, polovina)
            glVertex3f(-polovina, y, x); glVertex3f(polovina, y, x)
        glEnd()
        glEnable(GL_LIGHTING)

    # ============================ 2D SLOJ =============================
    def begin_2d(self) -> None:
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, self.height, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)

    def end_2d(self) -> None:
        glEnable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    # --- tekst preko teksture (OpenGL sam ne zna za slova) ---
    def _tekst_tekstura(self, tekst: str, mali: bool = False,
                        boja=(220, 228, 240)) -> Tuple[int, int, int]:
        kljuc = f"{int(mali)}|{boja}|{tekst}"
        if kljuc in self._tex_cache:
            return self._tex_cache[kljuc]

        font = self._font_small if mali else self._font
        surf = font.render(tekst, True, boja).convert_alpha()
        w, h = surf.get_size()
        podaci = pygame.image.tostring(surf, "RGBA", True)

        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA,
                     GL_UNSIGNED_BYTE, podaci)
        glBindTexture(GL_TEXTURE_2D, 0)

        if len(self._tex_cache) > 400:          # jednostavno ciscenje kesa
            for stari in list(self._tex_cache.keys())[:200]:
                glDeleteTextures([self._tex_cache.pop(stari)[0]])
        self._tex_cache[kljuc] = (tex, w, h)
        return self._tex_cache[kljuc]

    def _crtaj_teksturu(self, tex: int, x: float, y: float, w: float, h: float) -> None:
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, tex)
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(x, y)
        glTexCoord2f(1, 1); glVertex2f(x + w, y)
        glTexCoord2f(1, 0); glVertex2f(x + w, y + h)
        glTexCoord2f(0, 0); glVertex2f(x, y + h)
        glEnd()
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

    def tekst(self, s: str, x: float, y: float, mali: bool = False,
              boja=(220, 228, 240)) -> None:
        tex, w, h = self._tekst_tekstura(s, mali, boja)
        self._crtaj_teksturu(tex, x, y, w, h)

    def tekst_centrirano(self, s: str, cx: float, y: float, mali: bool = False,
                         boja=(220, 228, 240)) -> None:
        """Crta tekst tako da mu je SREDINA na `cx`.

        Postoji zato sto OpenGL ne zna za slova: tekst se iscrtava kao slicica
        ciji je `x` leva ivica. Da bi bio centriran, mora mu se izmeriti sirina
        i pomeriti se za njenu polovinu."""
        tex, w, h = self._tekst_tekstura(s, mali, boja)
        self._crtaj_teksturu(tex, cx - w / 2.0, y, w, h)

    def pravougaonik(self, x, y, w, h, boja=(0.05, 0.06, 0.08, 1.0),
                     okvir=(0.23, 0.26, 0.34, 1.0)) -> None:
        glColor4f(*boja)
        glBegin(GL_QUADS)
        glVertex2f(x, y); glVertex2f(x + w, y)
        glVertex2f(x + w, y + h); glVertex2f(x, y + h)
        glEnd()
        if okvir:
            glColor4f(*okvir)
            glLineWidth(1.0)
            glBegin(GL_LINE_LOOP)
            glVertex2f(x, y); glVertex2f(x + w, y)
            glVertex2f(x + w, y + h); glVertex2f(x, y + h)
            glEnd()

    # --- pokazivac nagiba sake ---
    def pokazivac_nagiba(self, cx: float, cy: float, r: float, ugao: float,
                         prisutna: bool, zakljucana: bool, naslov: str,
                         boja=(0.45, 0.72, 0.95)) -> None:
        """Polukruzna skala sa iglom koja prati nagib sake.

        Osencen deo u sredini je mrtva zona: dok je igla u njoj, objekat miruje.
        """
        cfg = self.cfg
        self.tekst_centrirano(naslov, cx, cy - r - 34, mali=True,
                              boja=(150, 165, 190))

        # mrtva zona
        glColor4f(0.30, 0.33, 0.40, 0.55)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(cx, cy)
        n = 18
        for i in range(n + 1):
            a = math.radians(-cfg.DEAD_ZONE + 2 * cfg.DEAD_ZONE * i / n)
            glVertex2f(cx + r * math.sin(a), cy - r * math.cos(a))
        glEnd()

        # luk skale
        glColor4f(0.35, 0.38, 0.46, 1.0)
        glLineWidth(2.0)
        glBegin(GL_LINE_STRIP)
        for i in range(41):
            a = math.radians(-90.0 + 180.0 * i / 40.0)
            glVertex2f(cx + r * math.sin(a), cy - r * math.cos(a))
        glEnd()

        if not prisutna:
            self.tekst_centrirano("ruka nije u kadru", cx, cy + 14, mali=True,
                                  boja=(128, 118, 118))
            return

        a = math.radians(max(-90.0, min(90.0, ugao)))
        if zakljucana:
            glColor4f(0.95, 0.72, 0.30, 1.0)
        else:
            glColor4f(*boja, 1.0)
        glLineWidth(4.0)
        glBegin(GL_LINES)
        glVertex2f(cx, cy)
        glVertex2f(cx + r * math.sin(a), cy - r * math.cos(a))
        glEnd()

    # --- prikaz kamere ---
    def preview(self, frame, x: float, y: float) -> None:
        if frame is None:
            return
        h, w = frame.shape[:2]
        podaci = np.ascontiguousarray(frame[::-1]).tobytes()
        if self._preview_tex is None:
            self._preview_tex = glGenTextures(1)
            self._preview_size = (0, 0)
        glBindTexture(GL_TEXTURE_2D, self._preview_tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        if self._preview_size != (w, h):
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB,
                         GL_UNSIGNED_BYTE, podaci)
            self._preview_size = (w, h)
        else:
            glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, w, h, GL_RGB,
                            GL_UNSIGNED_BYTE, podaci)
        glBindTexture(GL_TEXTURE_2D, 0)
        self._crtaj_teksturu(self._preview_tex, x, y, w, h)