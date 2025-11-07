from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='CPEAutomotor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nro_ctg', models.CharField(db_index=True, max_length=14, unique=True)),
                ('tipo_carta_porte', models.CharField(blank=True, max_length=10, null=True)),
                ('sucursal', models.IntegerField(blank=True, null=True)),
                ('nro_orden', models.IntegerField(blank=True, null=True)),
                ('estado', models.CharField(blank=True, max_length=50, null=True)),
                ('fecha_emision', models.DateTimeField(blank=True, null=True)),
                ('fecha_inicio_estado', models.DateTimeField(blank=True, null=True)),
                ('fecha_vencimiento', models.DateTimeField(blank=True, null=True)),
                ('observaciones', models.TextField(blank=True, null=True)),
                ('raw_response', models.JSONField(blank=True, default=dict)),
            ],
        ),
    ]
