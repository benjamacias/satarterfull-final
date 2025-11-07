from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_client_additional_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="Provider",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("email", models.EmailField(blank=True, default="", max_length=254)),
                ("tax_id", models.CharField(blank=True, default="", max_length=20)),
                ("fiscal_address", models.CharField(blank=True, default="", max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("afip_code", models.CharField(blank=True, max_length=50, null=True, unique=True)),
                ("default_tariff", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
            ],
        ),
    ]
