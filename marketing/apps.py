from django.apps import AppConfig


class MarketingConfig(AppConfig):
    name = 'marketing'

    def ready(self):
        from . import handlers
        handlers.register_handlers()
