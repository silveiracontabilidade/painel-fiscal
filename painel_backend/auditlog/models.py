from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'

    action = models.CharField(max_length=10, choices=Action.choices)
    app_label = models.CharField(max_length=100, db_index=True)
    model_name = models.CharField(max_length=100, db_index=True)
    object_pk = models.CharField(max_length=100, db_index=True)
    changes = models.JSONField(default=dict, blank=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='audit_logs',
    )
    actor_repr = models.CharField(max_length=255, blank=True)
    path = models.CharField(max_length=500, blank=True)
    method = models.CharField(max_length=10, blank=True)
    remote_addr = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['app_label', 'model_name', 'object_pk']),
            models.Index(fields=['actor', 'created_at']),
        ]

    def __str__(self) -> str:
        return f'{self.app_label}.{self.model_name} ({self.action})'

    @classmethod
    def is_actor_logging_enabled(cls) -> bool:
        return getattr(settings, 'AUDITLOG_LOG_ACTOR', True)
