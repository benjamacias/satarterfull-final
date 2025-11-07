from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="fiscal_address",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="client",
            name="tax_condition",
            field=models.PositiveSmallIntegerField(
                choices=[(4, "Responsable Inscripto"), (5, "Consumidor Final"), (6, "Monotributo")],
                default=5,
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="tax_id",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
    ]
