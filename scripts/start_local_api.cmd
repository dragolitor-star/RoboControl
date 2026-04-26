@echo off
cd /d "c:\Users\enesk\OneDrive\Masaüstü\cursor proje\RCS-2000 Middleware\rcs-middleware"
"c:\Users\enesk\OneDrive\Masaüstü\cursor proje\RCS-2000 Middleware\rcs-middleware\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8000
