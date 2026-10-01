# -*- coding: utf-8 -*-
"""
PyInstaller za jedan .exe fajl.

Pokretanje:  build_exe.bat
(ili rucno:  pyinstaller --noconfirm --clean Rotacija3D.spec)

Tri stvari koje PyInstaller sam ne bi uhvatio, pa su ovde navedene:

1. mediapipe uz sebe nosi modele (.tflite) i opise grafova (.binarypb) koje
   ucitava po putanji u toku rada, a ne kroz import. Bez `collect_all` .exe se
   napravi uredno i pukne tek kad se upali kamera.

2. PyOpenGL bira svoju platformu i tip niza tek u toku rada, preko imena
   modula. Ti moduli se nabrajaju rucno, inace se dobija greska
   "Attempt to call an undefined function".

3. tkinter je potreban samo zbog dijaloga za izbor modela (taster o).
"""

from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for paket in ("mediapipe", "google.protobuf", "cv2"):
    d, b, h = collect_all(paket)
    datas += d
    binaries += b
    hiddenimports += h

hiddenimports += [
    # PyOpenGL: platforma i formati nizova se biraju u toku rada
    "OpenGL.platform.win32",
    "OpenGL.arrays.ctypesarrays",
    "OpenGL.arrays.ctypesparameters",
    "OpenGL.arrays.ctypespointers",
    "OpenGL.arrays.lists",
    "OpenGL.arrays.nones",
    "OpenGL.arrays.numbers",
    "OpenGL.arrays.numpymodule",
    "OpenGL.arrays.strings",
    "OpenGL.arrays.vbo",
    # dijalog za izbor 3D modela
    "tkinter",
    "tkinter.filedialog",
]

excludes = [
    "pandas", "scipy", "notebook", "IPython", "pytest",
    "PyQt5", "PyQt6", "PySide2", "PySide6", "sounddevice",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Rotacija3D",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                # UPX cesto podigne antivirus, ne koristimo ga
    runtime_tmpdir=None,
    console=True,             # ostavi True dok ne proradi, posle prebaci u False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
