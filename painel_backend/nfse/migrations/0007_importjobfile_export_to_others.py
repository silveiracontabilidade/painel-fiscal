from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nfse", "0006_reinfnfs_company_code_reinfnfs_competence_period_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="importjobfile",
            name="export_to_others",
            field=models.BooleanField(default=False),
        ),
    ]
