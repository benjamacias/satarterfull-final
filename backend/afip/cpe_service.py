from datetime import datetime
from decimal import Decimal
import xml.etree.ElementTree as ET

import requests
from django.utils import timezone

from trips.models import CPEAutomotor
from billing.models import Client, Product, Provider
from .wsaa import get_token_sign

URL_PROD = "https://cpea-ws.afip.gob.ar/wscpe/services/soap"
CUIT_REP = "30716004720"  # ajustar

def _element_to_dict(element):
    children = list(element)
    if not children:
        return (element.text or "").strip()
    data = {}
    for c in children:
        k = c.tag.split('}')[-1]
        v = _element_to_dict(c)
        if k in data:
            if not isinstance(data[k], list):
                data[k] = [data[k]]
            data[k].append(v)
        else:
            data[k] = v
    return data

def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        value = str(value).strip()
        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    dt = datetime.strptime(normalized, fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _normalize_tax_id(value):
    if value is None:
        return ""
    return "".join(ch for ch in str(value) if ch.isdigit())


def _extract_first_leaf(value):
    if isinstance(value, dict):
        for v in value.values():
            leaf = _extract_first_leaf(v)
            if leaf not in (None, "", []):
                return leaf
        return None
    if isinstance(value, list):
        for item in value:
            leaf = _extract_first_leaf(item)
            if leaf not in (None, "", []):
                return leaf
        return None
    return value


def _find_first(data, keys):
    if not data:
        return None
    normalized_keys = {k for k in keys}
    stack = [data]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                short_key = key.split('}')[-1]
                if short_key in normalized_keys:
                    if isinstance(value, (dict, list)):
                        leaf = _extract_first_leaf(value)
                        if leaf not in (None, "", []):
                            return leaf
                    elif value not in (None, "", []):
                        return value
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(current, list):
            stack.extend(current)
    return None


def _to_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", "."))
    except (ArithmeticError, ValueError):
        return None


def _match_by_tax_id(model, tax_id_value):
    normalized = _normalize_tax_id(tax_id_value)
    if not normalized:
        return None
    candidates = model.objects.filter(tax_id__icontains=normalized)
    for candidate in candidates:
        if _normalize_tax_id(candidate.tax_id) == normalized:
            return candidate
    return None


def consultar_cpe_por_ctg(nro_ctg: str) -> dict:
    token, sign = get_token_sign(service="wscpe")
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:wsc="https://serviciosjava.afip.gob.ar/wscpe/">
  <soapenv:Header/>
  <soapenv:Body>
    <wsc:ConsultarCPEAutomotorReq>
      <auth>
        <token>{token}</token>
        <sign>{sign}</sign>
        <cuitRepresentada>{CUIT_REP}</cuitRepresentada>
      </auth>
      <solicitud>
        <nroCTG>{nro_ctg}</nroCTG>
      </solicitud>
    </wsc:ConsultarCPEAutomotorReq>
  </soapenv:Body>
</soapenv:Envelope>"""
    headers = {"Content-Type":"text/xml; charset=utf-8",
               "SOAPAction":"https://serviciosjava.afip.gob.ar/wscpe/consultarCPEAutomotor"}
    r = requests.post(URL_PROD, data=body.encode("utf-8"), headers=headers, timeout=60)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    resp = root.find(".//respuesta")
    if resp is None:
        raise RuntimeError("Respuesta inválida del WS CPE")
    data = _element_to_dict(resp)
    cab = data.get("cabecera", {}) or {}
    client = _match_by_tax_id(
        Client,
        _find_first(
            data,
            {
                "cuitDestinatario",
                "cuitDestino",
                "cuitDestinatarioFinal",
                "cuitDestinatarioComercial",
            },
        ),
    )
    provider = _match_by_tax_id(
        Provider,
        _find_first(
            data,
            {
                "cuitTransportista",
                "cuitInterviniente",
                "cuitSolicitante",
            },
        ),
    )

    producto_data = _find_first(
        data,
        {
            "descripcionProducto",
            "descProducto",
            "descripcionMercaderia",
            "mercaderia",
            "producto",
        },
    )
    producto_codigo = _find_first(
        data,
        {
            "codProducto",
            "codigoProducto",
            "idProducto",
        },
    )

    if isinstance(producto_data, dict):
        producto_descripcion = producto_data.get("descripcion") or producto_data.get("descripcionProducto")
    else:
        producto_descripcion = producto_data
    if producto_descripcion:
        producto_descripcion = str(producto_descripcion).strip()

    if producto_codigo:
        producto_codigo = str(producto_codigo).strip()

    product = None
    if producto_codigo:
        product, _ = Product.objects.get_or_create(
            afip_code=producto_codigo,
            defaults={"name": producto_descripcion or producto_codigo},
        )
    elif producto_descripcion:
        product = Product.objects.filter(name__iexact=producto_descripcion).first()
        if not product:
            product = Product.objects.create(name=producto_descripcion)

    if product and producto_descripcion and product.name != producto_descripcion:
        product.name = producto_descripcion
        product.save(update_fields=["name"])

    procedencia = _find_first(
        data,
        {"procedencia", "descripcionOrigen", "nombreEstablecimientoOrigen", "domicilioOrigen"},
    )
    destino = _find_first(
        data,
        {"destino", "descripcionDestino", "nombreEstablecimientoDestino", "domicilioDestino"},
    )
    peso = _to_decimal(
        _find_first(
            data,
            {"pesoBrutoDescarga", "pesoBruto", "pesoBrutoTotal"},
        )
    )

    defaults_extra = {
        "client": client,
        "provider": provider,
        "product": product,
        "product_description": producto_descripcion or producto_codigo or "",
        "procedencia": str(procedencia).strip() if procedencia else "",
        "destino": str(destino).strip() if destino else "",
        "peso_bruto_descarga": peso,
    }

    obj, created = CPEAutomotor.objects.update_or_create(
        nro_ctg=str(cab.get("nroCTG") or nro_ctg).strip(),
        defaults={
            "tipo_carta_porte": cab.get("tipoCartaPorte"),
            "sucursal": cab.get("sucursal"),
            "nro_orden": cab.get("nroOrden"),
            "estado": cab.get("estado"),
            "fecha_emision": _parse_datetime(cab.get("fechaEmision")),
            "fecha_inicio_estado": _parse_datetime(cab.get("fechaInicioEstado")),
            "fecha_vencimiento": _parse_datetime(cab.get("fechaVencimiento")),
            "observaciones": cab.get("observaciones"),
            "raw_response": data,
            **defaults_extra,
        },
    )
    if created and product and product.default_tariff and product.default_tariff != 0:
        obj.tariff = product.default_tariff
        obj.save(update_fields=["tariff"])
    elif obj.tariff in (None, Decimal("0")) and product and product.default_tariff:
        obj.tariff = product.default_tariff
        obj.save(update_fields=["tariff"])
    return data
