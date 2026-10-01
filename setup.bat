@echo off
REM ====================================================================
REM  Virtuelno okruzenje i zavisnosti (Windows)
REM  Pokretanje: dvoklik ili   setup.bat
REM ====================================================================
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    echo [i] Virtuelno okruzenje vec postoji.
    goto install
)

echo [1/3] Pravim virtuelno okruzenje (.venv)...
py -3.11 -m venv .venv
if errorlevel 1 (
    echo [!] Python 3.11 nije nadjen, pokusavam 3.10...
    py -3.10 -m venv .venv
)
if errorlevel 1 (
    echo [!] Pokusavam sa podrazumevanim Python-om...
    python -m venv .venv
)
if errorlevel 1 (
    echo [X] Neuspesno. Instaliraj Python 3.10 ili 3.11 sa python.org.
    pause
    exit /b 1
)

:install
call ".venv\Scripts\activate.bat"
echo [2/3] Azuriram pip...
python -m pip install --upgrade pip
echo [3/3] Instaliram zavisnosti...
pip install -r requirements.txt
if errorlevel 1 (
    echo [X] Instalacija nije uspela. Najcesci uzrok: Python noviji od 3.11.
    pause
    exit /b 1
)

echo.
echo === Provera okruzenja ===
python -c "import sys, numpy, pygame, OpenGL, cv2, mediapipe; print('Python   ', sys.version.split()[0]); print('pygame   ', pygame.version.ver); print('PyOpenGL ', OpenGL.__version__); print('numpy    ', numpy.__version__); print('opencv   ', cv2.__version__); print('mediapipe', mediapipe.__version__); print(); print('Spremno.  python main.py')"
echo.
pause
