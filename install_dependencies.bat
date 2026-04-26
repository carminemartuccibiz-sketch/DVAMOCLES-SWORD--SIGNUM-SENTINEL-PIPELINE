@echo off
setlocal
title SIGNUM SENTINEL - Dependency Installer
echo ========================================================
echo        DVAMOCLES SWORD (TM) - MASTER DATA FORGE
echo           INSTALLAZIONE DIPENDENZE AI E CV
echo ========================================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

:: Python check
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python non trovato nel PATH.
    echo Installa Python 3.12 e riavvia questo script.
    pause
    exit /b 1
)

python -c "import sys; print(sys.version)"
echo.

:: Se esiste venv locale, usa quello.
if exist "%ROOT_DIR%venv\Scripts\activate.bat" (
    echo [INFO] Attivazione venv locale...
    call "%ROOT_DIR%venv\Scripts\activate.bat"
)

echo [STEP] Aggiorno pip/setuptools/wheel...
python -m pip install --upgrade pip setuptools wheel

echo [STEP] Installo dipendenze base da requirements.txt...
if exist "%ROOT_DIR%requirements.txt" (
    python -m pip install -r "%ROOT_DIR%requirements.txt"
) else (
    python -m pip install customtkinter psutil gputil pillow tkinterdnd2 pyexiftool opencv-python numpy
)

echo [STEP] Installo stack AI (Torch + Transformers)...
python -m pip install torch torchvision torchaudio transformers accelerate
if errorlevel 1 (
    echo [WARN] Installazione AI standard fallita. Riprovo con indice CPU...
    python -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
    python -m pip install transformers accelerate
)

echo.
echo ========================================================
echo ESITO INSTALLAZIONE:
echo Se vedi errori su torch/transformers, verifica:
echo  - Python 3.12 consigliato
echo  - venv attivo
echo  - connessione internet
echo.
echo Esegui il launcher:
echo   START_FORGE.bat
echo ========================================================
pause