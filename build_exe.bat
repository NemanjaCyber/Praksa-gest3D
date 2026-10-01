@echo off
REM ====================================================================
REM  Pravljenje jednog .exe fajla
REM  Preduslov: setup.bat je vec odradjen i .venv postoji
REM  Rezultat:  dist\Rotacija3D.exe
REM ====================================================================
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [X] Nema virtuelnog okruzenja. Prvo pokreni setup.bat
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo [1/3] Proveravam PyInstaller...
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo     Instaliram PyInstaller...
    pip install pyinstaller
)

echo [2/3] Brisem stare rezultate...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/3] Pravim .exe (traje 2-5 minuta, ne prekidaj)...
pyinstaller --noconfirm --clean Rotacija3D.spec
if errorlevel 1 (
    echo [X] Pravljenje nije uspelo. Procitaj poruku iznad.
    pause
    exit /b 1
)

echo.
echo === GOTOVO ===
for %%F in ("dist\Rotacija3D.exe") do echo Fajl: %%~fF   velicina: %%~zF bajtova
echo.
pause
