@echo off
echo ==========================================
echo SDPS Backend Launcher
echo ==========================================

echo [1/3] Changing directory...
cd /d "C:\Users\Nouran\Desktop\PR2\SDPS\Backend"
echo Current folder: %cd%

echo [2/3] Activating virtual environment...
call "C:\Users\Nouran\Desktop\PR2\SDPS\Backend\.venv\Scripts\activate.bat"
echo VENV activated. Python:
python --version

echo [3/3] Starting Django server on port 8000...
python manage.py runserver 8000

echo ==========================================
echo Server stopped (window was closed or error).
pause