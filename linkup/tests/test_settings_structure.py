"""
Unit tests for settings module structure.
Tests that settings modules load correctly based on environment.
"""

import os
import sys
import unittest
from pathlib import Path


class SettingsStructureTests(unittest.TestCase):
    """Test settings module structure and loading."""
    
    def setUp(self):
        """Set up test environment."""
        # Store original environment
        self.original_env = os.environ.get('DJANGO_ENVIRONMENT')
        
        # Remove settings from sys.modules to force reload
        modules_to_remove = [
            key for key in sys.modules.keys() 
            if key.startswith('professional_network.settings')
        ]
        for module in modules_to_remove:
            del sys.modules[module]
    
    def tearDown(self):
        """Restore original environment."""
        if self.original_env:
            os.environ['DJANGO_ENVIRONMENT'] = self.original_env
        elif 'DJANGO_ENVIRONMENT' in os.environ:
            del os.environ['DJANGO_ENVIRONMENT']
        
        # Clean up modules again
        modules_to_remove = [
            key for key in sys.modules.keys() 
            if key.startswith('professional_network.settings')
        ]
        for module in modules_to_remove:
            del sys.modules[module]
    
    def test_settings_init_loads_development_by_default(self):
        """Test that settings/__init__.py loads development settings by default."""
        # Ensure DJANGO_ENVIRONMENT is not set
        if 'DJANGO_ENVIRONMENT' in os.environ:
            del os.environ['DJANGO_ENVIRONMENT']
        
        # Import settings
        from professional_network import settings
        
        # Check that DEBUG is True (development setting)
        self.assertTrue(settings.DEBUG)
        self.assertIn('*', settings.ALLOWED_HOSTS)
    
    def test_settings_init_loads_production_when_env_set(self):
        """Test that settings/__init__.py loads production settings when DJANGO_ENVIRONMENT=production."""
        # Set environment to production
        os.environ['DJANGO_ENVIRONMENT'] = 'production'
        
        # Set required production environment variables
        os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
        os.environ['ALLOWED_HOSTS'] = 'example.com,www.example.com'
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost/testdb'
        
        try:
            # Import settings
            from professional_network import settings
            
            # Check that production settings are loaded
            # Note: DEBUG might still be True if DEBUG env var is set
            self.assertIsNotNone(settings.SECRET_KEY)
            self.assertNotEqual(settings.ALLOWED_HOSTS, ['*'])
        finally:
            # Clean up environment variables
            del os.environ['SECRET_KEY']
            del os.environ['ALLOWED_HOSTS']
            del os.environ['DATABASE_URL']
    
    def test_development_settings_inherits_from_base(self):
        """Test that development.py properly inherits from base.py."""
        os.environ['DJANGO_ENVIRONMENT'] = 'development'
        
        from professional_network import settings
        
        # Check base settings are present
        self.assertIsNotNone(settings.INSTALLED_APPS)
        self.assertIsNotNone(settings.MIDDLEWARE)
        self.assertIsNotNone(settings.TEMPLATES)
        self.assertEqual(settings.AUTH_USER_MODEL, 'users.User')
        
        # Check development-specific settings
        self.assertTrue(settings.DEBUG)
        self.assertEqual(settings.DATABASES['default']['ENGINE'], 'django.db.backends.sqlite3')
    
    def test_production_settings_inherits_from_base(self):
        """Test that production.py properly inherits from base.py."""
        os.environ['DJANGO_ENVIRONMENT'] = 'production'
        os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only'
        os.environ['ALLOWED_HOSTS'] = 'example.com'
        os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost/testdb'
        
        try:
            from professional_network import settings
            
            # Check base settings are present
            self.assertIsNotNone(settings.INSTALLED_APPS)
            self.assertIsNotNone(settings.MIDDLEWARE)
            self.assertIsNotNone(settings.TEMPLATES)
            self.assertEqual(settings.AUTH_USER_MODEL, 'users.User')
            
            # Check production-specific settings
            self.assertTrue(settings.SECURE_SSL_REDIRECT)
            self.assertTrue(settings.SESSION_COOKIE_SECURE)
        finally:
            del os.environ['SECRET_KEY']
            del os.environ['ALLOWED_HOSTS']
            del os.environ['DATABASE_URL']
    
    def test_settings_can_be_imported_without_errors(self):
        """Test that settings modules can be imported without errors."""
        try:
            # Test development settings
            os.environ['DJANGO_ENVIRONMENT'] = 'development'
            from professional_network.settings import development
            self.assertIsNotNone(development.DEBUG)
            
            # Clean up
            del sys.modules['professional_network.settings.development']
            del sys.modules['professional_network.settings.base']
            
            # Test production settings with required env vars
            os.environ['DJANGO_ENVIRONMENT'] = 'production'
            os.environ['SECRET_KEY'] = 'test-secret-key'
            os.environ['ALLOWED_HOSTS'] = 'example.com'
            os.environ['DATABASE_URL'] = 'postgresql://user:pass@localhost/testdb'
            
            from professional_network.settings import production
            self.assertIsNotNone(production.SECRET_KEY)
            
        finally:
            # Clean up environment variables
            if 'SECRET_KEY' in os.environ:
                del os.environ['SECRET_KEY']
            if 'ALLOWED_HOSTS' in os.environ:
                del os.environ['ALLOWED_HOSTS']
            if 'DATABASE_URL' in os.environ:
                del os.environ['DATABASE_URL']
    
    def test_settings_files_exist(self):
        """Test that all required settings files exist."""
        base_dir = Path(__file__).resolve().parent.parent
        settings_dir = base_dir / 'professional_network' / 'settings'
        
        self.assertTrue(settings_dir.exists(), "Settings directory should exist")
        self.assertTrue((settings_dir / '__init__.py').exists(), "__init__.py should exist")
        self.assertTrue((settings_dir / 'base.py').exists(), "base.py should exist")
        self.assertTrue((settings_dir / 'development.py').exists(), "development.py should exist")
        self.assertTrue((settings_dir / 'production.py').exists(), "production.py should exist")


if __name__ == '__main__':
    unittest.main()
