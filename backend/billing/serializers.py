from rest_framework import serializers
from billing.models import Client, Invoice, Product, Provider
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


class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ["id", "name", "email", "tax_id", "fiscal_address"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "afip_code", "default_tariff"]
        extra_kwargs = {
            "name": {"allow_blank": False},
            "afip_code": {"required": False, "allow_blank": True, "allow_null": True},
            "default_tariff": {"required": False},
        }

    def validate_name(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError(
                "Ingresá el nombre del producto."
            )
        return value

    def validate_afip_code(self, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        return value

    def validate_default_tariff(self, value):
        if value is None:
            return value
        if value < 0:
            raise serializers.ValidationError(
                "La tarifa predeterminada no puede ser negativa."
            )
        return value


class CPEInvoiceSerializer(serializers.ModelSerializer):
    client_id = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()
    provider_id = serializers.SerializerMethodField()
    provider_name = serializers.SerializerMethodField()
    product_id = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    product_code = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = CPEAutomotor
        fields = [
            "id",
            "nro_ctg",
            "fecha_emision",
            "nro_orden",
            "product_description",
            "procedencia",
            "destino",
            "peso_bruto_descarga",
            "tariff",
            "total_amount",
            "client_id",
            "client_name",
            "provider_id",
            "provider_name",
            "product_id",
            "product_name",
            "product_code",
        ]

    def get_total_amount(self, obj: CPEAutomotor):
        if obj.tariff is None:
            return None
        if obj.peso_bruto_descarga in (None, 0):
            return obj.tariff
        return obj.tariff * obj.peso_bruto_descarga

    def get_client_id(self, obj: CPEAutomotor):
        return obj.client_id

    def get_client_name(self, obj: CPEAutomotor):
        return obj.client.name if obj.client else None

    def get_provider_id(self, obj: CPEAutomotor):
        return obj.provider_id

    def get_provider_name(self, obj: CPEAutomotor):
        return obj.provider.name if obj.provider else None

    def get_product_id(self, obj: CPEAutomotor):
        return obj.product_id

    def get_product_name(self, obj: CPEAutomotor):
        if obj.product:
            return obj.product.name
        return obj.product_description or None

    def get_product_code(self, obj: CPEAutomotor):
        if obj.product:
            return obj.product.afip_code
        return None


class CPETariffUpdateSerializer(serializers.Serializer):
    tariff = serializers.DecimalField(max_digits=12, decimal_places=2)
