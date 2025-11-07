from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404
from billing.models import Client, Invoice
from billing.serializers import (
    CPEListSerializer,
    CPERequestSerializer,
    CPESerializer,
    ClientSerializer,
    EmitirFacturaSerializer,
    InvoiceSerializer,
)
from afip.cpe_service import consultar_cpe_por_ctg
from afip.fe_service import emitir_y_guardar_factura
from trips.models import CPEAutomotor

class FacturacionViewSet(viewsets.ViewSet):

    @action(detail=False, methods=["post"], url_path="cpe/consultar")
    def consultar_cpe(self, request):
        s = CPERequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            consultar_cpe_por_ctg(s.validated_data["nro_ctg"])
        except Exception as exc:  # pragma: no cover - defensive, depends on AFIP API
            return Response(
                {"detail": f"No fue posible consultar la carta de porte: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        nro_ctg = str(s.validated_data["nro_ctg"]).strip()
        cpe = get_object_or_404(CPEAutomotor, nro_ctg=nro_ctg)
        return Response(CPESerializer(cpe).data)

    @action(detail=False, methods=["post"], url_path="facturas/emitir")
    def emitir(self, request):
        s = EmitirFacturaSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        client = Client.objects.get(pk=s.validated_data["client_id"])
        inv = emitir_y_guardar_factura(
            client=client,
            amount=s.validated_data["amount"],
            pto_vta=s.validated_data["pto_vta"],
            cbte_tipo=s.validated_data["cbte_tipo"],
            doc_tipo=s.validated_data["doc_tipo"],
            doc_nro=s.validated_data["doc_nro"],
            condicion_iva_receptor_id=s.validated_data.get("condicion_iva_receptor_id", 5),
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
