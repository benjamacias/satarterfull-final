from io import BytesIO
from decimal import Decimal, ROUND_HALF_UP
import base64
import json
import os
from urllib.parse import quote_plus

from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone

from billing.models import Invoice
from . import solicitar_cae as fe

def _build_arca_qr_payload(
    *,
    fecha_emision,          # date
    cuit_emisor: str,       # "307..."
    pto_vta: int,
    cbte_tipo: int,
    cbte_nro: int,
    importe_total,          # Decimal
    moneda: str = "PES",
    cotizacion: Decimal = Decimal("1"),
    doc_tipo_rec: int | None = None,
    doc_nro_rec: str | None = None,
    tipo_cod_aut: str = "E",  # "E" = CAE, "A" = CAEA
    cod_aut: str | int | None = None,
) -> dict:
    """
    Payload QR según especificación ARCA (ver=1).
    La URL final queda: {URL}?p={JSON_BASE64_URLENCODED}
    """
    # Normalizaciones (ARCA define algunos campos como numéricos)
    importe_qr = Decimal(importe_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    payload = {
        "ver": 1,
        "fecha": fecha_emision.isoformat(),
        "cuit": int(str(cuit_emisor)),
        "ptoVta": int(pto_vta),
        "tipoCmp": int(cbte_tipo),
        "nroCmp": int(cbte_nro),
        "importe": float(importe_qr) if importe_qr % 1 else int(importe_qr),
        "moneda": str(moneda),
        "ctz": float(Decimal(cotizacion)),
        "tipoCodAut": str(tipo_cod_aut),
        "codAut": int(cod_aut) if cod_aut is not None else None,
    }

    if doc_tipo_rec is not None and doc_nro_rec:
        # “De corresponder”
        payload["tipoDocRec"] = int(doc_tipo_rec)
        # Puede ser CUIT/DNI; si trae guiones o espacios, limpiamos
        doc_nro_digits = "".join(ch for ch in str(doc_nro_rec) if ch.isdigit())
        payload["nroDocRec"] = int(doc_nro_digits) if doc_nro_digits else doc_nro_rec

    # Si codAut quedó None, lo sacamos (es obligatorio: mejor fallar antes que emitir QR inválido)
    if payload.get("codAut") is None:
        payload.pop("codAut", None)

    return payload


def _build_arca_qr_url(payload: dict) -> tuple[str, str]:
    """
    Devuelve:
      - url: URL completa para el QR
      - p_b64: el base64 (sin url-encode) del JSON
    """
    # JSON compacto
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    p_b64 = base64.b64encode(raw).decode("ascii")
    p_encoded = quote_plus(p_b64)

    # La especificación técnica menciona el endpoint ARCA. (ARCA mantiene redirects desde afip.gob.ar)
    base = getattr(settings, "ARCA_QR_BASE_URL", "https://www.arca.gob.ar/fe/qr/")
    url = f"{base}?p={p_encoded}"
    return url, p_b64


def _make_qr_png_data_uri(qr_url: str) -> str | None:
    """
    Genera un PNG embebible en HTML: <img src="data:image/png;base64,....">
    Requiere: pip install qrcode[pil]
    """
    try:
        import qrcode
    except Exception:
        return None

    img = qrcode.make(qr_url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def _render_pdf_to_bytes(template_name: str, context: dict) -> bytes:
    """
    Render HTML -> PDF con mejor soporte de CSS:
    - Preferido: WeasyPrint (recomendado para facturas: A4, tipografías, layout consistente)
    - Fallback: xhtml2pdf (mejorado con link_callback para static/media)
    """
    html = render_to_string(template_name, context)

    # 1) Preferir WeasyPrint si está disponible
    weasy_err = None
    try:
        from weasyprint import HTML, CSS  # type: ignore

        base_url = (
            getattr(settings, "WEASYPRINT_BASEURL", None)
            or getattr(settings, "STATIC_ROOT", None)
            or str(getattr(settings, "BASE_DIR", ""))
        )

        # Márgenes A4 razonables para impresión (ajustable desde el template también)
        default_css = CSS(string="""
            @page { size: A4; margin: 12mm 12mm 14mm 12mm; }
        """)

        return HTML(string=html, base_url=base_url).write_pdf(stylesheets=[default_css])
    except Exception as e:
        weasy_err = e

    # 2) Fallback xhtml2pdf
    from xhtml2pdf import pisa  # type: ignore

    def link_callback(uri: str, rel: str) -> str:
        # Permitir recursos remotos (si los usás)
        if uri.startswith(("http://", "https://")):
            return uri

        static_url = getattr(settings, "STATIC_URL", "/static/")
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        static_root = getattr(settings, "STATIC_ROOT", "")
        media_root = getattr(settings, "MEDIA_ROOT", "")

        if static_url and uri.startswith(static_url) and static_root:
            path = os.path.join(static_root, uri.replace(static_url, "", 1))
        elif media_url and uri.startswith(media_url) and media_root:
            path = os.path.join(media_root, uri.replace(media_url, "", 1))
        else:
            # Intentar ruta absoluta
            path = uri

        if not os.path.isfile(path):
            raise FileNotFoundError(f"Recurso no encontrado para PDF: {uri} -> {path}")

        return path

    out = BytesIO()
    status = pisa.CreatePDF(src=html, dest=out, encoding="utf-8", link_callback=link_callback)
    if status.err:
        extra = f" (WeasyPrint no disponible: {weasy_err})" if weasy_err else ""
        raise ValueError(f"Error generando PDF con xhtml2pdf{extra}")
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
    iva_rate=None,
    cbtes_asoc=None,
    periodo_asoc=None,
):
    iva_rate_value = iva_rate if iva_rate is not None else client.iva_rate
    cae_kwargs = {
        "cuit": "30716004720",
        "pto_vta": pto_vta,
        "importe": amount,
        "cbte_tipo": cbte_tipo,
        "concepto": 2,
        "doc_tipo": doc_tipo,
        "doc_nro": doc_nro,
        "condicion_iva_receptor_id": condicion_iva_receptor_id,
        "iva_rate": iva_rate_value,
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
        "iva_rate": str(iva_rate_value),
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

    # QR ARCA (payload + URL + imagen)
    qr_payload = _build_arca_qr_payload(
        fecha_emision=issue_date,
        cuit_emisor=cae_kwargs["cuit"],
        pto_vta=pto_vta,
        cbte_tipo=cbte_tipo,
        cbte_nro=int(inv.cbte_nro),
        importe_total=amount_dec,
        moneda="PES",
        cotizacion=Decimal("1"),
        doc_tipo_rec=doc_tipo,
        doc_nro_rec=doc_nro,
        tipo_cod_aut="E",
        cod_aut=str(inv.cae),
    )
    arca_qr_url, arca_qr_p_b64 = _build_arca_qr_url(qr_payload)
    arca_qr_img = _make_qr_png_data_uri(arca_qr_url)  # puede ser None si falta dependencia

    # Contexto para que el template cumpla con QR + datos ARCA (el layout se termina de ajustar en HTML/CSS)
    pdf_context = {
        "inv": inv,
        "client": client,
        "arca_qr_payload": qr_payload,
        "arca_qr_p_b64": arca_qr_p_b64,
        "arca_qr_url": arca_qr_url,
        "arca_qr_img": arca_qr_img,  # en el template: <img src="{{ arca_qr_img }}">
        "issue_date": issue_date,
    }

    pdf_bytes = _render_pdf_to_bytes("billing/invoice_template.html", pdf_context)
    inv.pdf.save(f"cbte_{inv.cbte_tipo}_{inv.pto_vta}_{inv.cbte_nro}.pdf", ContentFile(pdf_bytes), save=True)
    return inv 
