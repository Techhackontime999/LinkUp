@echo off
REM LinkUp - Local Development Setup for Windows
echo ============================================
echo  LinkUp - Local Development Setup
echo ============================================
echo.

if not exist "venv" (
    echo [1/5] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/5] Virtual environment already exists
)

echo [2/5] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo [OK] Dependencies installed

echo [3/5] Setting up environment...
if not exist ".env" (
    copy .env.example .env >nul
)
echo [OK] Environment configured

echo [4/5] Running migrations...
python manage.py migrate
echo [OK] Migrations complete

echo [5/5] Collecting static files...
python manage.py collectstatic --noinput
echo [OK] Static files collected

echo.
echo ============================================
echo  Setup complete!
echo ============================================
echo.
echo  To start the server:
echo    venv\Scripts\activate
echo    python manage.py runserver
echo.
echo  Then visit: http://127.0.0.1:8000
echo.
echo  To create an admin account:
echo    python manage.py createsuperuser
echo.
pause
