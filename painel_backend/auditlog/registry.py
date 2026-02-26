from django.db.models.signals import post_save, pre_delete, pre_save

_registered_models = set()


def register_model(model):
    from . import signals

    if model in _registered_models:
        return
    if model.__name__ == 'AuditLog' and model._meta.app_label == 'auditlog':
        return

    _registered_models.add(model)
    pre_save.connect(signals.before_save, sender=model, weak=False, dispatch_uid=f'audit_pre_{model.__name__}')
    post_save.connect(
        signals.after_save, sender=model, weak=False, dispatch_uid=f'audit_post_{model.__name__}'
    )
    pre_delete.connect(
        signals.before_delete,
        sender=model,
        weak=False,
        dispatch_uid=f'audit_delete_{model.__name__}',
    )
