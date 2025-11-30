import base64
import binascii
import json
from datetime import timedelta

from django.core.mail import EmailMessage
from django.db.models import Max
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
# from rest_framework.exceptions import ValidationError

from billing.models import Client, Invoice, Product, Provider
from billing.serializers import (
    CPEInvoiceSerializer,
    CPEListSerializer,
    CPERequestSerializer,
    CPETariffUpdateSerializer,
    CPESerializer,
    ClientSerializer,
    EmitirFacturaSerializer,
    InvoiceSerializer,
    ProductSerializer,
    ProviderSerializer,
)
from afip.cpe_service import _find_first, CPEConsultationError, consultar_cpe_por_ctg
# from afip.fe_service import emitir_y_guardar_factura
from trips.models import CPEAutomotor


def _normalize_tax_id(value: str | None) -> str:
    if not value:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())

class FacturacionViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["post"], url_path="cpe/consultar")
    def consultar_cpe(self, request):
        s = CPERequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            cpe = consultar_cpe_por_ctg(
                s.validated_data["nro_ctg"],
                peso_bruto_descarga=s.validated_data.get("peso_bruto_descarga"),
            )
        except CPEConsultationError as exc:
            detail = {"detail": str(exc)}
            if exc.code:
                detail["code"] = exc.code

            if exc.is_transient:
                return Response(detail, status=status.HTTP_502_BAD_GATEWAY)

            status_code = status.HTTP_400_BAD_REQUEST
            if exc.code == "TOKEN_EXPIRED":
                status_code = status.HTTP_401_UNAUTHORIZED
            elif exc.code == "INVALID_CTG":
                status_code = status.HTTP_404_NOT_FOUND

            return Response(detail, status=status_code)
        except Exception as exc:  # pragma: no cover - defensivo, depende de AFIP
            return Response(
                {"detail": f"No fue posible consultar la carta de porte: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(CPESerializer(cpe).data)

    @action(detail=False, methods=["post"], url_path="facturas/emitir")
    def emitir(self, request):
        s = EmitirFacturaSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        client = Client.objects.get(pk=s.validated_data["client_id"])

        # emisión real hacia AFIP deshabilitada para modo de prueba:
        # try:
        #     inv = emitir_y_guardar_factura(
        #         client=client,
        #         amount=s.validated_data["amount"],
        #         pto_vta=s.validated_data["pto_vta"],
        #         cbte_tipo=s.validated_data["cbte_tipo"],
        #         doc_tipo=s.validated_data["doc_tipo"],
        #         doc_nro=s.validated_data["doc_nro"],
        #         condicion_iva_receptor_id=s.validated_data.get("condicion_iva_receptor_id", 5),
        #         cbtes_asoc=s.validated_data.get("cbtes_asoc"),
        #         periodo_asoc=s.validated_data.get("periodo_asoc"),
        #     )
        # except ValueError as exc:
        #     raise ValidationError({"cbte_tipo": [str(exc)]})

        next_number = (
            Invoice.objects.filter(
                pto_vta=s.validated_data["pto_vta"],
                cbte_tipo=s.validated_data["cbte_tipo"],
            )
            .aggregate(Max("cbte_nro"))
            .get("cbte_nro__max")
            or 0
        )

        metadata = {
            "modo": "pruebas",
            "doc_tipo": s.validated_data["doc_tipo"],
            "doc_nro": s.validated_data["doc_nro"],
        }
        if s.validated_data.get("cbtes_asoc"):
            metadata["cbtes_asoc"] = s.validated_data["cbtes_asoc"]
        if s.validated_data.get("periodo_asoc"):
            metadata["periodo_asoc"] = s.validated_data["periodo_asoc"]

        inv = Invoice.objects.create(
            client=client,
            amount=s.validated_data["amount"],
            pto_vta=s.validated_data["pto_vta"],
            cbte_tipo=s.validated_data["cbte_tipo"],
            cbte_nro=next_number + 1,
            cae=f"TEST-CAE-{next_number + 1:08d}",
            cae_due=(timezone.now() + timedelta(days=30)).strftime("%Y%m%d"),
            metadata=metadata,
        )

        return Response(InvoiceSerializer(inv).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="facturas")
    def list_facturas(self, request):
        qs = Invoice.objects.select_related("client").order_by("-id")
        return Response(InvoiceSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], url_path="facturas/enviar")
    def enviar_mail(self, request, pk=None):
        inv = Invoice.objects.select_related("client").get(pk=pk)
        if not inv.client.email:
            return Response({"detail":"El cliente no tiene email"}, status=400)
        email = EmailMessage(
            subject=f"Factura {inv.cbte_tipo}-{inv.pto_vta}-{inv.cbte_nro}",
            body=f"Hola {inv.client.name}, te enviamos tu comprobante.",
            to=[inv.client.email],
        )
        if inv.pdf:
            email.attach_file(inv.pdf.path)
        email.send()
        return Response({"ok": True})

    @action(detail=False, methods=["get", "post"], url_path="clientes")
    def clientes(self, request):
        if request.method.lower() == "post":
            serializer = ClientSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            client = serializer.save()
            return Response(
                ClientSerializer(client).data,
                status=status.HTTP_201_CREATED,
            )

        qs = Client.objects.order_by("name")
        return Response(ClientSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="envios")
    def list_envios(self, request):
        qs = CPEAutomotor.objects.order_by("-fecha_emision", "-id")
        return Response(CPEListSerializer(qs, many=True).data)

    @action(detail=False, methods=["get", "post"], url_path="proveedores")
    def proveedores(self, request):
        if request.method.lower() == "post":
            serializer = ProviderSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            provider = serializer.save()
            return Response(
                ProviderSerializer(provider).data,
                status=status.HTTP_201_CREATED,
            )

        qs = Provider.objects.order_by("name")
        return Response(ProviderSerializer(qs, many=True).data)

    @action(detail=False, methods=["get", "post"], url_path="productos")
    def productos(self, request):
        if request.method.lower() == "post":
            serializer = ProductSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            product = serializer.save()
            return Response(
                ProductSerializer(product).data,
                status=status.HTTP_201_CREATED,
            )

        qs = Product.objects.order_by("name")
        return Response(ProductSerializer(qs, many=True).data)

    @action(detail=False, methods=["patch"], url_path="productos/(?P<product_id>[^/.]+)")
    def actualizar_producto(self, request, product_id=None):
        producto = get_object_or_404(Product, pk=product_id)
        serializer = ProductSerializer(producto, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProductSerializer(producto).data)

    @action(detail=False, methods=["get"], url_path="clientes/(?P<client_id>[^/.]+)/cpe")
    def cpe_por_cliente(self, request, client_id=None):
        client = get_object_or_404(Client, pk=client_id)
        qs = list(
            CPEAutomotor.objects.select_related("client", "provider", "product")
            .filter(client=client)
            .order_by("-fecha_emision", "-id")
        )
        normalized_tax_id = _normalize_tax_id(client.tax_id)
        if normalized_tax_id:
            candidatos = (
                CPEAutomotor.objects.select_related("client", "provider", "product")
                .filter(client__isnull=True)
                .order_by("-fecha_emision", "-id")
            )
            for cpe in candidatos:
                raw = json.dumps(cpe.raw_response or {}, ensure_ascii=False)
                if normalized_tax_id in _normalize_tax_id(raw):
                    qs.append(cpe)

        unicos = {cpe.id: cpe for cpe in qs}.values()
        ordenados = sorted(
            unicos,
            key=lambda c: (
                c.fecha_emision.timestamp() if c.fecha_emision else float("-inf"),
                c.id,
            ),
            reverse=True,
        )
        return Response(CPEInvoiceSerializer(ordenados, many=True).data)

    @action(detail=False, methods=["patch"], url_path="cpe/(?P<cpe_id>[^/.]+)/tarifa")
    def actualizar_tarifa_cpe(self, request, cpe_id=None):
        cpe = get_object_or_404(CPEAutomotor, pk=cpe_id)
        serializer = CPETariffUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cpe.tariff = serializer.validated_data["tariff"]
        cpe.save(update_fields=["tariff"])
        if cpe.product:
            product = cpe.product
            if product.default_tariff != cpe.tariff:
                product.default_tariff = cpe.tariff
                product.save(update_fields=["default_tariff"])
        return Response(CPEInvoiceSerializer(cpe).data)

    @action(detail=False, methods=["get"], url_path="cpe/(?P<cpe_id>[^/.]+)/pdf")
    def descargar_pdf_cpe(self, request, cpe_id=None):
        cpe = get_object_or_404(CPEAutomotor, pk=cpe_id)
        pdf_base64 = _find_first(cpe.raw_response or {}, {"pdf"})
        if not pdf_base64:
            return Response(
                {"detail": "El PDF no está disponible para esta carta de porte."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            pdf_content = base64.b64decode(pdf_base64)
        except (binascii.Error, ValueError):
            return Response(
                {"detail": "No se pudo decodificar el PDF de la carta de porte."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="cpe-{cpe.nro_ctg}.pdf"'
        return response
