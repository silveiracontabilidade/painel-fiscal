from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nfse", "0004_import_jobs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="importjobfile",
            name="stored_file",
            field=models.FileField(max_length=500, upload_to="nfse/uploads/%Y/%m/%d"),
        ),
    ]
