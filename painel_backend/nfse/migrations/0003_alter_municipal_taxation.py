from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("nfse", "0002_sample_nf"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reinfnfs",
            name="municipal_taxation",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
