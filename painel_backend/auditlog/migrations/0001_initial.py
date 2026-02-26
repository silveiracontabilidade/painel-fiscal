from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', 'Create'), ('update', 'Update'), ('delete', 'Delete')], max_length=10)),
                ('app_label', models.CharField(db_index=True, max_length=100)),
                ('model_name', models.CharField(db_index=True, max_length=100)),
                ('object_pk', models.CharField(db_index=True, max_length=100)),
                ('changes', models.JSONField(blank=True, default=dict)),
                ('actor_repr', models.CharField(blank=True, max_length=255)),
                ('path', models.CharField(blank=True, max_length=500)),
                ('method', models.CharField(blank=True, max_length=10)),
                ('remote_addr', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['app_label', 'model_name', 'object_pk'], name='auditlog_ap_app_lab_0e10fa_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['actor', 'created_at'], name='auditlog_ac_actor_i_146147_idx'),
        ),
    ]
