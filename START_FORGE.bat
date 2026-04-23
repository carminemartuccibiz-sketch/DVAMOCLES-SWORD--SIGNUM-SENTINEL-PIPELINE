@echo off
title DVAMOCLES SWORD - SIGNUM SENTINEL
color 0c

echo ========================================================
echo        DVAMOCLES SWORD (TM) - MASTER DATA FORGE
echo ========================================================
echo Inizializzazione moduli Core e AI in corso...
echo.

:: Avvia l'interfaccia grafica
python main_gui.py

:: Se l'app si chiude per un errore critico, non fa chiudere subito la finestra
pause