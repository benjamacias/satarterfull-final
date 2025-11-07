from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('email', models.EmailField(max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('pto_vta', models.IntegerField()),
                ('cbte_tipo', models.IntegerField(default=11)),
                ('cbte_nro', models.IntegerField(blank=True, null=True)),
                ('cae', models.CharField(blank=True, max_length=32, null=True)),
                ('cae_due', models.CharField(blank=True, max_length=8, null=True)),
                ('xml_raw', models.TextField(blank=True, null=True)),
                ('pdf', models.FileField(blank=True, null=True, upload_to='invoices/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='invoices', to='billing.client')),
            ],
        ),
    ]
