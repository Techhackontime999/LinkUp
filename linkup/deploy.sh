#!/bin/bash

# LinkUp v1.0.0 - Quick Deployment Script
# Usage: ./deploy.sh [environment]
# Example: ./deploy.sh production

set -e

ENVIRONMENT=${1:-development}
echo "🚀 Deploying LinkUp v1.0.0 to $ENVIRONMENT environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.10 or higher."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python $REQUIRED_VERSION or higher is required. Current version: $PYTHON_VERSION"
    exit 1
fi

print_success "Python $PYTHON_VERSION detected"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt
print_success "Dependencies installed"

# Set Django settings module based on environment
if [ "$ENVIRONMENT" = "production" ]; then
    export DJANGO_SETTINGS_MODULE="professional_network.settings.production"
    print_status "Using production settings"
else
    export DJANGO_SETTINGS_MODULE="professional_network.settings.development"
    print_status "Using development settings"
fi

# Check if .env file exists for production
if [ "$ENVIRONMENT" = "production" ] && [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating template..."
    cat > .env << EOF
DEBUG=False
SECRET_KEY=change-this-to-a-secure-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com
DATABASE_URL=sqlite:///db.sqlite3
EOF
    print_warning "Please edit .env file with your production settings before continuing"
    exit 1
fi

# Run migrations
print_status "Running database migrations..."
python manage.py migrate
print_success "Database migrations completed"

# Collect static files for production
if [ "$ENVIRONMENT" = "production" ]; then
    print_status "Collecting static files..."
    python manage.py collectstatic --noinput
    print_success "Static files collected"
fi

# Create superuser if it doesn't exist (only for development)
if [ "$ENVIRONMENT" = "development" ]; then
    print_status "Checking for superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    print('No superuser found. Please create one:')
    exit(1)
else:
    print('Superuser already exists')
" || {
    print_status "Creating superuser..."
    python manage.py createsuperuser
}
fi

# Run tests
print_status "Running tests..."
python manage.py test --verbosity=1
print_success "All tests passed"

# Final deployment message
print_success "🎉 LinkUp v1.0.0 deployment completed successfully!"

if [ "$ENVIRONMENT" = "development" ]; then
    echo ""
    print_status "To start the development server, run:"
    echo "  source venv/bin/activate"
    echo "  python manage.py runserver"
    echo ""
    print_status "Then visit: http://localhost:8000"
else
    echo ""
    print_status "For production, start the server with:"
    echo "  gunicorn professional_network.wsgi:application --bind 0.0.0.0:8000"
    echo ""
    print_status "Or use your preferred WSGI server configuration"
fi

echo ""
print_success "LinkUp v1.0.0 is ready! 🚀"
print_status "Repository: https://github.com/Techhackontime999/LinkUp.git"
print_status "Support: amitkumarkh010102006@gmail.com"