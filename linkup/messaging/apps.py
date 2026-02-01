from django.apps import AppConfig


class MessagingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messaging'
    verbose_name = 'Messaging'
    
    def ready(self):
        """Initialize signal handlers when the app is ready"""
        try:
            from . import signals
            signals.setup_all_signals()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error setting up notification signals: {e}")