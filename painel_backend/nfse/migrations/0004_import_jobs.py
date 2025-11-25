from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("nfse", "0003_alter_municipal_taxation"),
        ("nfse", "0003_fix_seed_timezone"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImportJob",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendente"),
                            ("processing", "Processando"),
                            ("completed", "Concluído"),
                            ("failed", "Falhou"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("options", models.JSONField(blank=True, default=dict)),
                ("totals_total_files", models.PositiveIntegerField(default=0)),
                ("totals_processing", models.PositiveIntegerField(default=0)),
                ("totals_completed", models.PositiveIntegerField(default=0)),
                ("totals_failed", models.PositiveIntegerField(default=0)),
                ("totals_ignored", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ImportJobFile",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("file_name", models.CharField(max_length=255)),
                ("file_size", models.BigIntegerField(default=0)),
                ("stored_file", models.FileField(upload_to="nfse/uploads/%Y/%m/%d")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pendente"),
                            ("uploading", "Enviando"),
                            ("processing", "Processando"),
                            ("completed", "Concluído"),
                            ("error", "Erro"),
                            ("ignored", "Ignorado"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "stage",
                    models.CharField(
                        choices=[
                            ("queued", "Fila"),
                            ("ocr", "OCR"),
                            ("ai", "Llm"),
                            ("persisting", "Persistindo"),
                            ("done", "Finalizado"),
                            ("error", "Erro"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("progress", models.PositiveSmallIntegerField(default=0)),
                ("message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="files",
                        to="nfse.importjob",
                    ),
                ),
                (
                    "result",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="job_files",
                        to="nfse.reinfnfs",
                    ),
                ),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
    ]
