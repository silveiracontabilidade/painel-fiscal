from django.urls import path

from .api_views import AuditLogListView

urlpatterns = [
    path('audit/logs/', AuditLogListView.as_view(), name='auditlog_list'),
]
