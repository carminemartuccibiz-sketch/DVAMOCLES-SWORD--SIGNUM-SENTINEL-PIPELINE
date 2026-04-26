@echo off
setlocal
title DVAMOCLES SWORD (TM) - MASTER DATA FORGE
color 0B

echo ========================================================
echo        DVAMOCLES SWORD (TM) - MASTER DATA FORGE
echo ========================================================
echo Inizializzazione moduli Core e AI in corso...
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

:: Se usi un ambiente virtuale (es. cartella venv), lo attiva automaticamente.
if exist "%ROOT_DIR%venv\Scripts\activate.bat" (
    call "%ROOT_DIR%venv\Scripts\activate.bat"
)

:: Icona launcher (usata anche da GUI via path assoluto)
set "SIGNUM_ICON=%ROOT_DIR%signum_icon.ico"
if not exist "%SIGNUM_ICON%" (
    echo [WARN] Icona non trovata: "%SIGNUM_ICON%"
    echo        Aggiungi signum_icon.ico nella root del progetto.
)

:: Avvia la GUI
python "%ROOT_DIR%main_gui.py"
set "EXIT_CODE=%ERRORLEVEL%"

:: Lascia la finestra aperta in caso di crash per leggere l'errore.
if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Uscita anomala di main_gui.py (code %EXIT_CODE%).
)
pause
exit /b %EXIT_CODE%