from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'action',
            'app_label',
            'model_name',
            'object_pk',
            'changes',
            'actor',
            'actor_repr',
            'path',
            'method',
            'remote_addr',
            'created_at',
        ]
