import json
from typing import Any

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models.signals import post_save, pre_delete, pre_save
from django.forms.models import model_to_dict

from .middleware import get_current_request
from .models import AuditLog


def serialize_instance(instance) -> dict[str, Any]:
    """
    Convert a model instance to a JSON-serializable dict.
    """
    field_values = {}
    for field in instance._meta.fields:
        if field.is_relation and field.many_to_one and field.remote_field:
            value = getattr(instance, field.attname, None)
        else:
            value = getattr(instance, field.name, None)
        field_values[field.name] = value

    field_values['pk'] = getattr(instance, instance._meta.pk.attname)
    exclude_fields = set(getattr(settings, 'AUDITLOG_EXCLUDE_FIELDS', []))
    for exclude in exclude_fields:
        field_values.pop(exclude, None)

    serialized = json.dumps(field_values, cls=DjangoJSONEncoder)
    return json.loads(serialized)


def diff_changes(before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, Any]:
    before = before or {}
    after = after or {}
    changed_fields = {}
    for key, new_value in after.items():
        if before.get(key) != new_value:
            changed_fields[key] = {'before': before.get(key), 'after': new_value}
    for key, old_value in before.items():
        if key not in after:
            changed_fields[key] = {'before': old_value, 'after': None}
    return changed_fields


def _get_actor_meta():
    request = get_current_request()
    if not request:
        return None, {}

    user = getattr(request, 'user', None)
    meta = {
        'path': request.path,
        'method': request.method,
        'remote_addr': request.META.get('REMOTE_ADDR', ''),
    }
    return user if user and user.is_authenticated else None, meta


def _create_audit_log(instance, action: str, before: dict[str, Any] | None, after: dict[str, Any] | None):
    if instance.__class__ is AuditLog:
        return

    actor, meta = _get_actor_meta()
    changes = {}
    if action == AuditLog.Action.CREATE:
        changes = {'after': after}
    elif action == AuditLog.Action.DELETE:
        changes = {'before': before}
    else:
        diff = diff_changes(before, after)
        if not diff:
            return
        changes = diff

    AuditLog.objects.create(
        action=action,
        app_label=instance._meta.app_label,
        model_name=instance.__class__.__name__,
        object_pk=str(getattr(instance, instance._meta.pk.attname)),
        changes=changes,
        actor=actor if AuditLog.is_actor_logging_enabled() else None,
        actor_repr=str(actor) if actor else '',
        path=meta.get('path', ''),
        method=meta.get('method', ''),
        remote_addr=meta.get('remote_addr', ''),
    )


def before_save(sender, instance, **kwargs):
    if instance._state.adding:
        instance._audit_previous = None
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
        instance._audit_previous = serialize_instance(previous)
    except sender.DoesNotExist:
        instance._audit_previous = None


def after_save(sender, instance, created, **kwargs):
    previous = getattr(instance, '_audit_previous', None)
    after = serialize_instance(instance)
    action = AuditLog.Action.CREATE if created or previous is None else AuditLog.Action.UPDATE

    # Ensure log is written with the main transaction
    using_db = kwargs.get('using', None)
    if using_db:
        with transaction.atomic(using=using_db):
            _create_audit_log(instance, action, previous, after)
    else:
        _create_audit_log(instance, action, previous, after)


def before_delete(sender, instance, **kwargs):
    previous = serialize_instance(instance)
    using_db = kwargs.get('using', None)
    if using_db:
        with transaction.atomic(using=using_db):
            _create_audit_log(instance, AuditLog.Action.DELETE, previous, None)
    else:
        _create_audit_log(instance, AuditLog.Action.DELETE, previous, None)
