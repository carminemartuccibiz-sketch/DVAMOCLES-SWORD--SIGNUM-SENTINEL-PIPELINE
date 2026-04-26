@echo off
setlocal
title SIGNUM SENTINEL - Install (New root)
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python non nel PATH.
    pause
    exit /b 1
)

if exist "%ROOT_DIR%venv\Scripts\activate.bat" (
    call "%ROOT_DIR%venv\Scripts\activate.bat"
)

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r "%ROOT_DIR%requirements.txt"
if errorlevel 1 (
    echo [WARN] Full install failed; retry CPU torch...
    python -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio
    python -m pip install -r "%ROOT_DIR%requirements.txt" --no-deps
    python -m pip install transformers accelerate safetensors huggingface_hub tokenizers sentencepiece diffusers
)

echo.
echo Avvio GUI: START_FORGE.bat
pause
