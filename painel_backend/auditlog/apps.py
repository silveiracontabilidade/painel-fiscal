from django.apps import AppConfig, apps
from django.conf import settings

from .registry import register_model


class AuditlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'auditlog'

    def ready(self):
        # Register models listed in settings for auditing
        models_to_track = getattr(settings, 'AUDITLOG_INCLUDE_MODELS', [])
        for dotted_path in models_to_track:
            try:
                model = apps.get_model(dotted_path)
            except LookupError:
                continue
            register_model(model)
