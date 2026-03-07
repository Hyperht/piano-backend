from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = 'inventory'

    def ready(self):
        import inventory.handlers
        inventory.handlers.register_handlers()
