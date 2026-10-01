"""
Ucitavanje i priprema 3D modela.

Podrzani formati bez dodatnih biblioteka: OBJ i STL (i tekstualni i binarni).
Ako je instaliran `trimesh`, preko njega rade i PLY, GLTF/GLB, 3MF i ostali.

Model se po ucitavanju NORMALIZUJE: pomeri se tako da mu je teziste u
koordinatnom pocetku i skalira da najveca dimenzija bude 1. Bez toga bi se
jedan model video kao tacka a drugi bi prekrio ceo ekran, jer modeli dolaze u
raznim jedinicama (milimetri, metri, inci).
"""

from __future__ import annotations

import math
import os
import struct
from typing import List, Optional, Tuple

import numpy as np


class Mesh:
    """Trouglasta mreza spremna za iscrtavanje."""

    def __init__(self, vertices: np.ndarray, faces: np.ndarray,
                 name: str = "model") -> None:
        self.vertices = np.asarray(vertices, dtype=np.float32).reshape(-1, 3)
        self.faces = np.asarray(faces, dtype=np.int32).reshape(-1, 3)
        self.name = name
        self._arrays: Optional[Tuple[np.ndarray, np.ndarray]] = None

    # ------------------------------------------------------------------
    @property
    def broj_temena(self) -> int:
        return int(self.vertices.shape[0])

    @property
    def broj_trouglova(self) -> int:
        return int(self.faces.shape[0])

    def normalize(self) -> "Mesh":
        """Centrira model i skalira ga na jedinicnu velicinu."""
        if self.broj_temena == 0:
            return self
        lo = self.vertices.min(axis=0)
        hi = self.vertices.max(axis=0)
        centar = (lo + hi) / 2.0
        self.vertices = self.vertices - centar
        najveca = float(np.max(hi - lo))
        if najveca > 1e-9:
            self.vertices = self.vertices / najveca
        self._arrays = None
        return self

    def build_arrays(self, smooth: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """Priprema nizove temena i normala za OpenGL.

        Vraca (temena, normale), oba oblika (3 * broj_trouglova, 3).
        Normale se racunaju iz vektorskog proizvoda stranica trougla; kod
        glatkog sencenja se usrednjavaju po temenu, pa povrsina deluje
        zaobljeno umesto fasetirano.
        """
        if self._arrays is not None:
            return self._arrays

        v = self.vertices
        f = self.faces
        if f.shape[0] == 0:
            prazno = np.zeros((0, 3), dtype=np.float32)
            self._arrays = (prazno, prazno)
            return self._arrays

        a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
        normale_stranica = np.cross(b - a, c - a)
        duzine = np.linalg.norm(normale_stranica, axis=1, keepdims=True)
        duzine[duzine < 1e-12] = 1.0
        normale_stranica = normale_stranica / duzine

        if smooth:
            po_temenu = np.zeros_like(v)
            for k in range(3):
                np.add.at(po_temenu, f[:, k], normale_stranica)
            duzine_v = np.linalg.norm(po_temenu, axis=1, keepdims=True)
            duzine_v[duzine_v < 1e-12] = 1.0
            po_temenu = po_temenu / duzine_v
            normals = po_temenu[f.reshape(-1)]
        else:
            normals = np.repeat(normale_stranica, 3, axis=0)

        verts = v[f.reshape(-1)]
        self._arrays = (np.ascontiguousarray(verts, dtype=np.float32),
                        np.ascontiguousarray(normals, dtype=np.float32))
        return self._arrays


# ======================== UCITAVANJE FORMATA ==========================
def _ucitaj_obj(path: str) -> Mesh:
    temena: List[Tuple[float, float, float]] = []
    stranice: List[Tuple[int, int, int]] = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for linija in f:
            if linija.startswith("v "):
                delovi = linija.split()
                temena.append((float(delovi[1]), float(delovi[2]), float(delovi[3])))
            elif linija.startswith("f "):
                delovi = linija.split()[1:]
                idx = []
                for d in delovi:
                    # oblik je v, v/vt, v//vn ili v/vt/vn - uzima se samo prvi broj
                    broj = d.split("/")[0]
                    if not broj:
                        continue
                    i = int(broj)
                    idx.append(i - 1 if i > 0 else len(temena) + i)
                # poligon sa vise od tri temena se deli na trouglove (lepeza)
                for k in range(1, len(idx) - 1):
                    stranice.append((idx[0], idx[k], idx[k + 1]))

    return Mesh(np.array(temena, dtype=np.float32),
                np.array(stranice, dtype=np.int32),
                os.path.basename(path))


def _ucitaj_stl(path: str) -> Mesh:
    with open(path, "rb") as f:
        glava = f.read(5)
        f.seek(0)
        tekstualni = glava[:5].lower() == b"solid"
        if tekstualni:
            # provera: binarni STL ume da pocne sa "solid", pa se gleda duzina
            podaci = f.read()
            if len(podaci) >= 84:
                broj = struct.unpack("<I", podaci[80:84])[0]
                if len(podaci) == 84 + broj * 50:
                    tekstualni = False
            f.seek(0)

        if tekstualni:
            temena = []
            for linija in f.read().decode("utf-8", errors="ignore").splitlines():
                linija = linija.strip()
                if linija.startswith("vertex"):
                    d = linija.split()
                    temena.append((float(d[1]), float(d[2]), float(d[3])))
            v = np.array(temena, dtype=np.float32)
            faces = np.arange(len(temena), dtype=np.int32).reshape(-1, 3)
            return Mesh(v, faces, os.path.basename(path))

        f.seek(80)
        broj = struct.unpack("<I", f.read(4))[0]
        podaci = np.frombuffer(f.read(broj * 50), dtype=np.uint8)
        if podaci.size < broj * 50:
            raise ValueError("STL fajl je nepotpun.")
        podaci = podaci.reshape(broj, 50)
        # svaki zapis: 12 bajtova normala + 36 bajtova tri temena + 2 bajta
        sirovi = podaci[:, 12:48].copy().view(np.float32).reshape(-1, 3)
        faces = np.arange(sirovi.shape[0], dtype=np.int32).reshape(-1, 3)
        return Mesh(sirovi, faces, os.path.basename(path))


def ucitaj_model(path: str) -> Mesh:
    """Ucitava model i normalizuje ga. Nepoznat format ide preko trimesh-a."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".obj":
        mesh = _ucitaj_obj(path)
    elif ext == ".stl":
        mesh = _ucitaj_stl(path)
    else:
        try:
            import trimesh                      # opciono
        except ImportError as exc:
            raise ValueError(
                f"Format {ext} trazi biblioteku trimesh "
                f"(pip install trimesh). Bez nje rade .obj i .stl."
            ) from exc
        ucitano = trimesh.load(path, force="mesh")
        mesh = Mesh(np.asarray(ucitano.vertices), np.asarray(ucitano.faces),
                    os.path.basename(path))

    if mesh.broj_trouglova == 0:
        raise ValueError(f"U fajlu {os.path.basename(path)} nema trouglova.")
    return mesh.normalize()


# ======================== PODRAZUMEVANI MODEL =========================
def podrazumevani_model(glavni: int = 64, sporedni: int = 28,
                        R: float = 0.33, r: float = 0.13) -> Mesh:
    """Torus koji se pravi u kodu, da aplikacija radi i bez ijednog fajla.

    Torus je biran namerno: nije simetrican po svim osama, pa se po njemu
    odmah vidi i smer i kolicina rotacije, za razliku od kocke ili lopte.
    """
    temena = []
    for i in range(glavni):
        u = 2.0 * math.pi * i / glavni
        for j in range(sporedni):
            v = 2.0 * math.pi * j / sporedni
            x = (R + r * math.cos(v)) * math.cos(u)
            y = r * math.sin(v)
            z = (R + r * math.cos(v)) * math.sin(u)
            temena.append((x, y, z))

    stranice = []
    for i in range(glavni):
        for j in range(sporedni):
            a = i * sporedni + j
            b = ((i + 1) % glavni) * sporedni + j
            c = ((i + 1) % glavni) * sporedni + (j + 1) % sporedni
            d = i * sporedni + (j + 1) % sporedni
            stranice.append((a, b, c))
            stranice.append((a, c, d))

    mesh = Mesh(np.array(temena, dtype=np.float32),
                np.array(stranice, dtype=np.int32), "torus (ugradjeni)")
    return mesh.normalize()
