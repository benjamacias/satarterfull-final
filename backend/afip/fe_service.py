from io import BytesIO
from django.template.loader import render_to_string
from django.core.files.base import ContentFile

from billing.models import Invoice
from . import solicitar_cae as fe

def _render_pdf_to_bytes(template_name: str, context: dict) -> bytes:
    from xhtml2pdf import pisa
    html = render_to_string(template_name, context)
    out = BytesIO()
    pisa.CreatePDF(src=html, dest=out, encoding="utf-8")
    return out.getvalue()

def emitir_y_guardar_factura(
    *,
    client,
    amount,
    pto_vta: int,
    cbte_tipo: int,
    doc_tipo: int,
    doc_nro: str,
    condicion_iva_receptor_id: int | None = 5,
    cbtes_asoc=None,
    periodo_asoc=None,
):
    cae_kwargs = {
        "cuit": "30716004720",
        "pto_vta": pto_vta,
        "importe": amount,
        "cbte_tipo": cbte_tipo,
        "concepto": 2,
        "doc_tipo": doc_tipo,
        "doc_nro": doc_nro,
        "condicion_iva_receptor_id": condicion_iva_receptor_id,
    }

    tipos_validos = fe.obtener_tipos_comprobante_validos(cuit=cae_kwargs["cuit"], pto_vta=pto_vta)
    if cbte_tipo not in tipos_validos:
        raise ValueError(
            f"El tipo de comprobante {cbte_tipo} no está habilitado para el punto de venta {pto_vta}."
        )
    if cbtes_asoc:
        cae_kwargs["cbtes_asoc"] = cbtes_asoc
    if periodo_asoc:
        cae_kwargs["periodo_asoc"] = periodo_asoc

    result = fe.solicitar_cae(**cae_kwargs)
    # No Mocked result to bypass external CAE request
    metadata = {
        "condicion_iva_receptor_id": condicion_iva_receptor_id,
    }
    if cbtes_asoc:
        metadata["cbtes_asoc"] = cbtes_asoc
    if periodo_asoc:
        metadata["periodo_asoc"] = periodo_asoc
    if result.get("observations"):
        metadata["observations"] = result["observations"]
    if result.get("events"):
        metadata["events"] = result["events"]

    inv = Invoice.objects.create(
        client=client,
        amount=amount,
        pto_vta=pto_vta,
        cbte_tipo=cbte_tipo,
        cbte_nro=result.get("cbte_nro"),
        cae=result.get("cae"),
        cae_due=result.get("cae_due"),
        xml_raw=result.get("xml"),
        metadata=metadata,
    )
    pdf_bytes = _render_pdf_to_bytes("billing/invoice_template.html", {"inv": inv, "client": client})
    inv.pdf.save(f"cbte_{inv.cbte_tipo}_{inv.pto_vta}_{inv.cbte_nro}.pdf", ContentFile(pdf_bytes), save=True)
    return inv
