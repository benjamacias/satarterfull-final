from django.db import models

class CPEAutomotor(models.Model):
    nro_ctg = models.CharField(max_length=14, unique=True, db_index=True)
    tipo_carta_porte = models.CharField(max_length=10, blank=True, null=True)
    sucursal = models.IntegerField(blank=True, null=True)
    nro_orden = models.IntegerField(blank=True, null=True)
    estado = models.CharField(max_length=50, blank=True, null=True)
    fecha_emision = models.DateTimeField(blank=True, null=True)
    fecha_inicio_estado = models.DateTimeField(blank=True, null=True)
    fecha_vencimiento = models.DateTimeField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    raw_response = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.nro_ctg
