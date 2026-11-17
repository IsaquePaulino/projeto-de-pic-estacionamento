@echo off
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python nao encontrado. Consulte docs\teste-ocupacao.md.
    pause
    exit /b 1
)
echo Abra http://127.0.0.1:8000 no navegador.
echo Mantenha esta janela aberta. Ctrl+C encerra o monitor.
".venv\Scripts\python.exe" -m uvicorn parking_monitor.app:app --host 127.0.0.1 --port 8000
if errorlevel 1 pause
