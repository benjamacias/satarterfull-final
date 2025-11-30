from datetime import datetime
from decimal import Decimal

from rest_framework import serializers

from afip.cpe_service import _find_first, _to_decimal
from billing.models import Client, Invoice, Product, Provider
from trips.models import CPEAutomotor

class CPERequestSerializer(serializers.Serializer):
    nro_ctg = serializers.CharField()
    peso_bruto_descarga = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        allow_null=True,
        min_value=0,
    )

def _calculate_net_weight(cpe: CPEAutomotor) -> Decimal | None:
    raw = cpe.raw_response or {}
    gross = _to_decimal(
        _find_first(
            raw,
            {"pesoBrutoDescarga", "pesoBruto", "pesoBrutoTotal"},
        )
    )
    tare = _to_decimal(_find_first(raw, {"pesoTaraDescarga"}))

    if gross is None:
        gross = cpe.peso_bruto_descarga

    if gross is None:
        return None

    if tare not in (None, Decimal("0")):
        net = gross - tare
        if net > 0:
            return net

    return gross


class CPESerializer(serializers.ModelSerializer):
    net_weight = serializers.SerializerMethodField()
    vehicle_domain = serializers.SerializerMethodField()

    class Meta:
        model = CPEAutomotor
        fields = "__all__"

    def get_net_weight(self, obj: CPEAutomotor):
        return _calculate_net_weight(obj)

    def get_vehicle_domain(self, obj: CPEAutomotor):
        return obj.vehicle_domain

def _parse_afip_date(value: str, field_name: str) -> str:
    """Parse date strings accepted by AFIP (YYYYMMDD or YYYY-MM-DD)."""
    if not isinstance(value, str):
        raise serializers.ValidationError({field_name: "Debe ser una cadena de texto."})

    value = value.strip()
    if not value:
        raise serializers.ValidationError({field_name: "No puede estar vacío."})

    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%Y%m%d")
        except ValueError:
            continue

    raise serializers.ValidationError({field_name: "Formato de fecha inválido. Usá YYYYMMDD o YYYY-MM-DD."})


class CbtesAsocField(serializers.Field):
    default_error_messages = {
        "invalid": "cbtes_asoc debe ser un objeto o una lista de objetos.",
        "missing_required": "Cada comprobante asociado debe incluir 'tipo', 'pto_vta' y 'nro'.",
    }

    def to_internal_value(self, data):
        if isinstance(data, dict):
            items = [data]
        elif isinstance(data, list):
            items = data
        else:
            self.fail("invalid")

        normalized = []
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                raise serializers.ValidationError({
                    "cbtes_asoc": f"El elemento en la posición {idx} debe ser un objeto."
                })

            try:
                tipo = int(item["tipo"])
                pto_vta = int(item["pto_vta"])
                nro = int(item["nro"])
            except KeyError:
                self.fail("missing_required")
            except (TypeError, ValueError):
                raise serializers.ValidationError({
                    "cbtes_asoc": "'tipo', 'pto_vta' y 'nro' deben ser numéricos."
                })

            if tipo <= 0 or pto_vta < 0 or nro < 0:
                raise serializers.ValidationError({
                    "cbtes_asoc": "'tipo', 'pto_vta' y 'nro' deben ser mayores o iguales a cero (tipo > 0)."
                })

            cuit = item.get("cuit")
            cuit_digits = "".join(ch for ch in str(cuit or "") if ch.isdigit())
            cbte_fch = item.get("cbte_fch")
            if cbte_fch is not None:
                cbte_fch = _parse_afip_date(str(cbte_fch), "cbtes_asoc.cbte_fch")

            normalized.append(
                {
                    "tipo": tipo,
                    "pto_vta": pto_vta,
                    "nro": nro,
                    **({"cuit": cuit_digits} if cuit_digits else {}),
                    **({"cbte_fch": cbte_fch} if cbte_fch else {}),
                }
            )

        return normalized

    def to_representation(self, value):
        return value


class PeriodoAsocField(serializers.Field):
    default_error_messages = {
        "invalid": "periodo_asoc debe ser un objeto con 'desde' y 'hasta'.",
    }

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            self.fail("invalid")

        if "desde" not in data or "hasta" not in data:
            raise serializers.ValidationError({
                "periodo_asoc": "Debés enviar 'desde' y 'hasta'."
            })

        desde = _parse_afip_date(str(data["desde"]), "periodo_asoc.desde")
        hasta = _parse_afip_date(str(data["hasta"]), "periodo_asoc.hasta")

        return {"desde": desde, "hasta": hasta}

    def to_representation(self, value):
        return value


class EmitirFacturaSerializer(serializers.Serializer):
    client_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    pto_vta = serializers.IntegerField()
    cbte_tipo = serializers.IntegerField(default=11)
    doc_tipo = serializers.IntegerField(default=80)  # 80 CUIT
    doc_nro = serializers.CharField()
    condicion_iva_receptor_id = serializers.IntegerField(required=False, allow_null=True)
    cbtes_asoc = CbtesAsocField(required=False)
    periodo_asoc = PeriodoAsocField(required=False)

    def validate(self, attrs):
        cbtes_asoc = attrs.get("cbtes_asoc")
        periodo_asoc = attrs.get("periodo_asoc")
        cbte_tipo = attrs.get("cbte_tipo")

        if cbtes_asoc and periodo_asoc:
            raise serializers.ValidationError(
                "No podés enviar cbtes_asoc y periodo_asoc al mismo tiempo."
            )

        if cbte_tipo in (12, 13) and not (cbtes_asoc or periodo_asoc):
            raise serializers.ValidationError(
                "Las Notas de Débito/Crédito requieren cbtes_asoc o periodo_asoc."
            )

        return attrs

class InvoiceSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    client_email = serializers.EmailField(source="client.email", read_only=True)
    metadata = serializers.JSONField(read_only=True)
    class Meta:
        model = Invoice
        fields = [
            "id",
            "client",
            "client_name",
            "client_email",
            "amount",
            "pto_vta",
            "cbte_tipo",
            "cbte_nro",
            "cae",
            "cae_due",
            "pdf",
            "created_at",
            "metadata",
        ]


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
    vehicle_domain = serializers.CharField(read_only=True)

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
            "vehicle_domain",
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
    net_weight = serializers.SerializerMethodField()
    vehicle_domain = serializers.CharField(read_only=True)

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
            "net_weight",
            "tariff",
            "total_amount",
            "client_id",
            "client_name",
            "provider_id",
            "provider_name",
            "product_id",
            "product_name",
            "product_code",
            "vehicle_domain",
        ]

    def get_total_amount(self, obj: CPEAutomotor):
        if obj.tariff is None:
            return None
        net_weight = self.get_net_weight(obj)
        if net_weight in (None, 0):
            return obj.tariff
        return obj.tariff * net_weight

    def get_net_weight(self, obj: CPEAutomotor):
        return _calculate_net_weight(obj)

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
