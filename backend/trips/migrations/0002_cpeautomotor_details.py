from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0003_provider_product"),
        ("trips", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="cpeautomotor",
            name="client",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="cpe_automotor", to="billing.client"),
        ),
        migrations.AddField(
            model_name="cpeautomotor",
            name="destino",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="cpeautomotor",
            name="peso_bruto_descarga",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="cpeautomotor",
            name="procedencia",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="cpeautomotor",
            name="product",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="cpe_automotor", to="billing.product"),
        ),
        migrations.AddField(
            model_name="cpeautomotor",
            name="product_description",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="cpeautomotor",
            name="provider",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="cpe_automotor", to="billing.provider"),
        ),
        migrations.AddField(
            model_name="cpeautomotor",
            name="tariff",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
    ]
