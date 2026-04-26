@echo off
setlocal
title SIGNUM SENTINEL - PIPELINE REPORTS
color 0A

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

if exist "%ROOT_DIR%venv\Scripts\activate.bat" (
    call "%ROOT_DIR%venv\Scripts\activate.bat"
)

echo ===============================================
echo SIGNUM SENTINEL - FULL PIPELINE REPORTS RUN
echo ===============================================
echo Running ingestion, validation, benchmark,
echo segmentation and dataset export...
echo.

python "%ROOT_DIR%run_pipeline_reports.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] Pipeline reports run failed (code %EXIT_CODE%).
) else (
    echo.
    echo [OK] Pipeline reports completed.
)

pause
exit /b %EXIT_CODE%
