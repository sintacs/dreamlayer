@echo off
setlocal
set PYTHONUTF8=1
set PYTHONUNBUFFERED=1

echo Starting DreamLayer Brain server...
start http://localhost:7777/

python --version >nul 2>&1
if %errorlevel% equ 0 (
    python -m dreamlayer.ai_brain.server --token rune-birch
) else (
    py -m dreamlayer.ai_brain.server --token rune-birch
)
pause
