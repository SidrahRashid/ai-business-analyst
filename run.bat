@echo off
cd /d "%~dp0"
echo ============================================================
echo   Starting Camellia Tea Atelier & Analytics Portal
echo ============================================================
echo   Local URL: http://127.0.0.1:8000
echo   Press Ctrl+C to stop the server
echo ============================================================
".venv\Scripts\python.exe" -m uvicorn server:app --host 127.0.0.1 --port 8000
