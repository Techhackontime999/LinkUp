@echo off
REM LinkUp v1.0.0 - Quick Deployment Script for Windows
REM Usage: deploy.bat [environment]
REM Example: deploy.bat production

setlocal enabledelayedexpansion

set ENVIRONMENT=%1
if "%ENVIRONMENT%"=="" set ENVIRONMENT=development

echo 🚀 Deploying LinkUp v1.0.0 to %ENVIRONMENT% environment...

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed. Please install Python 3.10 or higher.
    exit /b 1
)

echo [SUCCESS] Python detected

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    echo [SUCCESS] Virtual environment created
) else (
    echo [INFO] Virtual environment already exists
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo [INFO] Installing dependencies...
pip install -r requirements.txt
echo [SUCCESS] Dependencies installed

REM Set Django settings module based on environment
if "%ENVIRONMENT%"=="production" (
    set DJANGO_SETTINGS_MODULE=professional_network.settings.production
    echo [INFO] Using production settings
) else (
    set DJANGO_SETTINGS_MODULE=professional_network.settings.development
    echo [INFO] Using development settings
)

REM Check if .env file exists for production
if "%ENVIRONMENT%"=="production" (
    if not exist ".env" (
        echo [WARNING] .env file not found. Creating template...
        echo DEBUG=False > .env
        echo SECRET_KEY=change-this-to-a-secure-secret-key >> .env
        echo ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com >> .env
        echo DATABASE_URL=sqlite:///db.sqlite3 >> .env
        echo [WARNING] Please edit .env file with your production settings before continuing
        exit /b 1
    )
)

REM Run migrations
echo [INFO] Running database migrations...
python manage.py migrate
echo [SUCCESS] Database migrations completed

REM Collect static files for production
if "%ENVIRONMENT%"=="production" (
    echo [INFO] Collecting static files...
    python manage.py collectstatic --noinput
    echo [SUCCESS] Static files collected
)

REM Run tests
echo [INFO] Running tests...
python manage.py test --verbosity=1
echo [SUCCESS] All tests passed

REM Final deployment message
echo [SUCCESS] 🎉 LinkUp v1.0.0 deployment completed successfully!

if "%ENVIRONMENT%"=="development" (
    echo.
    echo [INFO] To start the development server, run:
    echo   venv\Scripts\activate.bat
    echo   python manage.py runserver
    echo.
    echo [INFO] Then visit: http://localhost:8000
) else (
    echo.
    echo [INFO] For production, start the server with:
    echo   python -m gunicorn professional_network.wsgi:application --bind 0.0.0.0:8000
    echo.
    echo [INFO] Or use your preferred WSGI server configuration
)

echo.
echo [SUCCESS] LinkUp v1.0.0 is ready! 🚀
echo [INFO] Repository: https://github.com/Techhackontime999/LinkUp.git
echo [INFO] Support: amitkumarkh010102006@gmail.com

pause