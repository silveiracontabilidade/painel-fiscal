from datetime import datetime

from django.db import migrations
from django.utils import timezone


def fix_timezone(apps, schema_editor):
    ReinfNFS = apps.get_model('nfse', 'ReinfNFS')
    access_key = '31062001217276558000105250000000110125117518887650'
    try:
        record = ReinfNFS.objects.get(access_key=access_key)
    except ReinfNFS.DoesNotExist:
        return

    record.emission_datetime = timezone.make_aware(datetime(2025, 11, 4, 9, 49, 58))
    record.dps_emission_datetime = timezone.make_aware(datetime(2025, 11, 4, 0, 0, 0))
    record.save(update_fields=['emission_datetime', 'dps_emission_datetime'])


def reverse_fix_timezone(apps, schema_editor):
    ReinfNFS = apps.get_model('nfse', 'ReinfNFS')
    access_key = '31062001217276558000105250000000110125117518887650'
    try:
        record = ReinfNFS.objects.get(access_key=access_key)
    except ReinfNFS.DoesNotExist:
        return

    record.emission_datetime = datetime(2025, 11, 4, 9, 49, 58)
    record.dps_emission_datetime = datetime(2025, 11, 4, 0, 0, 0)
    record.save(update_fields=['emission_datetime', 'dps_emission_datetime'])


class Migration(migrations.Migration):
    dependencies = [
        ('nfse', '0002_sample_nf'),
    ]

    operations = [
        migrations.RunPython(fix_timezone, reverse_fix_timezone),
    ]
