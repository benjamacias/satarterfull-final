from django.db import models


class Client(models.Model):
    CONDICION_IVA_CHOICES = (
        (4, "Responsable Inscripto"),
        (5, "Consumidor Final"),
        (6, "Monotributo"),
    )

    name = models.CharField(max_length=120)
    email = models.EmailField()
    tax_id = models.CharField(max_length=20, default="", blank=True)
    fiscal_address = models.CharField(max_length=255, default="", blank=True)
    tax_condition = models.PositiveSmallIntegerField(
        choices=CONDICION_IVA_CHOICES,
        default=5,
    )
    iva_rate = models.DecimalField(max_digits=5, decimal_places=4, default=0.21)

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Provider(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True, default="")
    tax_id = models.CharField(max_length=20, default="", blank=True)
    fiscal_address = models.CharField(max_length=255, default="", blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=120)
    afip_code = models.CharField(max_length=50, null=True, blank=True, unique=True)
    default_tariff = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return self.name

class Invoice(models.Model):
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="invoices")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    pto_vta = models.IntegerField()
    cbte_tipo = models.IntegerField(default=11)  # 11=Factura C
    cbte_nro = models.IntegerField(null=True, blank=True)
    cae = models.CharField(max_length=32, blank=True, null=True)
    cae_due = models.CharField(max_length=8, blank=True, null=True)  # YYYYMMDD
    xml_raw = models.TextField(blank=True, null=True)
    pdf = models.FileField(upload_to="invoices/", blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        nro = self.cbte_nro if self.cbte_nro is not None else "s/n"
        return f"Cbte {self.cbte_tipo}-{self.pto_vta}-{nro}"
