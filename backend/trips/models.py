from django.db import models

from billing.models import Client, Product, Provider


class Vehicle(models.Model):
    domain = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.domain


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
    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL, related_name="cpe_automotor", null=True, blank=True
    )
    provider = models.ForeignKey(
        Provider, on_delete=models.SET_NULL, related_name="cpe_automotor", null=True, blank=True
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL, related_name="cpe_automotor", null=True, blank=True
    )
    product_description = models.CharField(max_length=255, blank=True, default="")
    procedencia = models.CharField(max_length=255, blank=True, default="")
    destino = models.CharField(max_length=255, blank=True, default="")
    peso_bruto_descarga = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True
    )
    tariff = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cpe_automotor",
    )

    def __str__(self):
        return self.nro_ctg

    @property
    def vehicle_domain(self) -> str | None:
        return self.vehicle.domain if self.vehicle else None
