from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0003_provider_product"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="iva_rate",
            field=models.DecimalField(decimal_places=4, default=0.21, max_digits=5),
        ),
    ]
