@echo off
title DVAMOCLES SWORD (TM) - MASTER DATA FORGE
color 0B

echo ========================================================
echo        DVAMOCLES SWORD (TM) - MASTER DATA FORGE
echo ========================================================
echo Inizializzazione moduli Core e AI in corso...
echo.

:: Se usi un ambiente virtuale (es. cartella venv), lo attiva automaticamente
if exist venv\Scripts\activate (
    call venv\Scripts\activate
)

:: Avvia la GUI
python main_gui.py

:: Lascia la finestra aperta in caso di crash per leggere l'errore
pause