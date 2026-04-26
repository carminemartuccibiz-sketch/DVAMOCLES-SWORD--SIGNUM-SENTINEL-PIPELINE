@echo off
setlocal
title DVAMOCLES SWORD (TM) - SIGNUM SENTINEL (New root)
color 0B

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

if exist "%ROOT_DIR%venv\Scripts\activate.bat" (
    call "%ROOT_DIR%venv\Scripts\activate.bat"
)

set "SIGNUM_ICON=%ROOT_DIR%signum_icon.ico"

python "%ROOT_DIR%main_gui.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] main_gui.py exit %EXIT_CODE%.
)
pause
exit /b %EXIT_CODE%
