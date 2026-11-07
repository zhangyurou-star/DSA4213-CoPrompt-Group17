@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
) else (
    python -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
)
if errorlevel 1 pause
endlocal
