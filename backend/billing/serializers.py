from rest_framework import serializers
from billing.models import Client, Invoice
from trips.models import CPEAutomotor

class CPERequestSerializer(serializers.Serializer):
    nro_ctg = serializers.CharField()

class CPESerializer(serializers.ModelSerializer):
    class Meta:
        model = CPEAutomotor
        fields = "__all__"

class EmitirFacturaSerializer(serializers.Serializer):
    client_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    pto_vta = serializers.IntegerField()
    cbte_tipo = serializers.IntegerField(default=11)
    doc_tipo = serializers.IntegerField(default=80)  # 80 CUIT
    doc_nro = serializers.CharField()
    condicion_iva_receptor_id = serializers.IntegerField(required=False, allow_null=True)

class InvoiceSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    client_email = serializers.EmailField(source="client.email", read_only=True)
    class Meta:
        model = Invoice
        fields = ["id","client","client_name","client_email","amount","pto_vta","cbte_tipo",
                  "cbte_nro","cae","cae_due","pdf","created_at"]


class ClientSerializer(serializers.ModelSerializer):
    tax_condition_display = serializers.CharField(
        source="get_tax_condition_display", read_only=True
    )

    class Meta:
        model = Client
        fields = [
            "id",
            "name",
            "email",
            "tax_id",
            "fiscal_address",
            "tax_condition",
            "tax_condition_display",
        ]
        extra_kwargs = {
            "name": {"allow_blank": False},
            "email": {"allow_blank": False},
            "tax_id": {"allow_blank": False},
            "fiscal_address": {"allow_blank": False},
        }

    def validate_name(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Ingresá el nombre o razón social del cliente.")
        return value

    def validate_email(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Ingresá el email de contacto del cliente.")
        return value

    def validate_tax_id(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Ingresá el número de CUIT/CUIL del cliente.")
        return value

    def validate_fiscal_address(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Ingresá la dirección fiscal del cliente.")
        return value


class CPEListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CPEAutomotor
        fields = [
            "id",
            "nro_ctg",
            "tipo_carta_porte",
            "estado",
            "fecha_emision",
            "fecha_vencimiento",
            "sucursal",
            "nro_orden",
        ]
