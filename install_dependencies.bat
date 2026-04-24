@echo off
title SIGNUM SENTINEL - Dependency Installer
echo ========================================================
echo        DVAMOCLES SWORD (TM) - MASTER DATA FORGE
echo           INSTALLAZIONE DIPENDENZE AI E CV
echo ========================================================
echo.

:: Aggiorna pip
python -m pip install --upgrade pip

:: Dipendenze Core GUI e Hardware
pip install customtkinter psutil gputil pillow tkinterdnd2 pyexiftool

:: Dipendenze Computer Vision (OpenCV)
pip install opencv-python numpy

:: Tentativo installazione Torch (Rimosso indice CUDA specifico per massimizzare compatibilita)
echo Tentativo installazione modelli AI...
pip install torch torchvision torchaudio

echo.
echo ========================================================
echo ESITO INSTALLAZIONE:
echo Se leggi "ERROR: Could not find a version that satisfies the requirement torch",
echo significa che Python 3.14 e troppo nuovo per l'AI.
echo In quel caso, installa Python 3.12 dal sito ufficiale.
echo ========================================================
pause