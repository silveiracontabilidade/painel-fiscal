from django.utils.dateparse import parse_datetime
from rest_framework import generics

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(generics.ListAPIView):
    """
    Read-only endpoint for audit logs with basic filters.
    """

    serializer_class = AuditLogSerializer
    queryset = AuditLog.objects.all().select_related('actor')

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params

        app_label = params.get('app')
        model_name = params.get('model')
        object_pk = params.get('object_pk')
        action = params.get('action')
        actor = params.get('actor')
        created_from = params.get('from')
        created_to = params.get('to')

        if app_label:
            qs = qs.filter(app_label=app_label)
        if model_name:
            qs = qs.filter(model_name=model_name)
        if object_pk:
            qs = qs.filter(object_pk=object_pk)
        if action in dict(AuditLog.Action.choices):
            qs = qs.filter(action=action)
        if actor:
            qs = qs.filter(actor_id=actor)
        if created_from:
            dt = parse_datetime(created_from)
            if dt:
                qs = qs.filter(created_at__gte=dt)
        if created_to:
            dt = parse_datetime(created_to)
            if dt:
                qs = qs.filter(created_at__lte=dt)
        return qs
