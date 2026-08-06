@echo off
echo.
echo ===========================================
echo   Installing requirements for LogiMind AI...
echo ===========================================
echo.

if exist .venv\Scripts\pip.exe (
    echo [INFO] Installing to virtual environment (.venv)...
    .venv\Scripts\pip.exe install -r requirements.txt
) else (
    echo [INFO] Installing to system python...
    pip install -r requirements.txt
)

echo.
echo ===========================================
echo   Installation completed!
echo ===========================================
pause
