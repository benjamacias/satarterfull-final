from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0003_provider_product"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
