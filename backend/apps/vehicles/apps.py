from django.apps import AppConfig


class VehiclesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.vehicles"
    label = "vehicles"

    def ready(self):
        from . import signals  # noqa: F401