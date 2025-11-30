from datetime import datetime
from decimal import Decimal
import logging
import xml.etree.ElementTree as ET

import requests
from django.utils import timezone

from trips.models import CPEAutomotor, Vehicle
from billing.models import Client, Product, Provider
from .wsaa import get_token_sign

logger = logging.getLogger(__name__)

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


def _normalize_domain(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = "".join(ch for ch in str(value).strip().upper() if ch.isalnum())
    return cleaned or None


class CPEConsultationError(Exception):
    def __init__(self, message: str, code: str | None = None, is_transient: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.is_transient = is_transient


def _sanitize_payload(value: str, secrets: list[str]) -> str:
    sanitized = value or ""
    for secret in secrets:
        if secret:
            sanitized = sanitized.replace(secret, "***")
    return sanitized


def _extract_error_info(payload: dict) -> tuple[str | None, str | None]:
    if not isinstance(payload, dict):
        return None, None

    potential_containers = [payload]
    for key, value in payload.items():
        if not value:
            continue
        lower_key = key.lower()
        if "error" in lower_key or "fault" in lower_key:
            potential_containers.append(value)
        elif isinstance(value, (dict, list)):
            potential_containers.append(value)

    for container in potential_containers:
        code = _find_first(container, {"codigo", "code", "faultcode"})
        message = _find_first(
            container,
            {
                "mensaje",
                "descripcion",
                "faultstring",
                "detalle",
                "detail",
            },
        )
        if message:
            return (str(code).strip() if code else None, str(message).strip())
    return None, None


def _normalize_error_code(code: str | None, message: str | None) -> str | None:
    normalized_msg = (message or "").lower()
    if "token" in normalized_msg and "expir" in normalized_msg:
        return "TOKEN_EXPIRED"
    if "ctg" in normalized_msg and any(w in normalized_msg for w in ["no existe", "inexist", "inválid", "invalid"]):
        return "INVALID_CTG"
    if code:
        return str(code)
    return None


def consultar_cpe_por_ctg(nro_ctg: str, peso_bruto_descarga: Decimal | None = None) -> CPEAutomotor:
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
    sanitized_request = _sanitize_payload(body, [token, sign])
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "https://serviciosjava.afip.gob.ar/wscpe/consultarCPEAutomotor",
    }

    logger.info(
        "Consultando CPE en AFIP",
        extra={
            "event": "afip.cpe.consulta.request",
            "nro_ctg": str(nro_ctg),
            "payload": sanitized_request,
        },
    )

    try:
        r = requests.post(URL_PROD, data=body.encode("utf-8"), headers=headers, timeout=60)
        r.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - logged for debugging
        response_text = getattr(exc.response, "text", "") if hasattr(exc, "response") else ""
        logger.exception(
            "Error al consultar AFIP CPE",
            extra={
                "event": "afip.cpe.consulta.error",
                "nro_ctg": str(nro_ctg),
                "status_code": getattr(exc.response, "status_code", None),
                "payload": _sanitize_payload(response_text, [token, sign]),
            },
        )
        raise CPEConsultationError(
            "No fue posible contactar al servicio de AFIP",
            code="AFIP_UNAVAILABLE",
            is_transient=True,
        ) from exc

    sanitized_response = _sanitize_payload(r.text, [token, sign])
    logger.info(
        "Respuesta recibida de AFIP CPE",
        extra={
            "event": "afip.cpe.consulta.response",
            "nro_ctg": str(nro_ctg),
            "status_code": r.status_code,
            "payload": sanitized_response,
        },
    )

    root = ET.fromstring(r.text)

    fault = root.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Fault") or root.find(".//Fault")
    if fault is not None:
        fault_data = _element_to_dict(fault)
        code, message = _extract_error_info(fault_data)
        normalized_code = _normalize_error_code(code, message)
        raise CPEConsultationError(
            message or "Respuesta de error de AFIP",
            code=normalized_code,
            is_transient=False,
        )

    resp = root.find(".//respuesta")
    if resp is None:
        raise CPEConsultationError("Respuesta inválida del WS CPE", code="INVALID_RESPONSE")

    data = _element_to_dict(resp)
    error_code, error_message = _extract_error_info(data)
    if error_message:
        normalized_code = _normalize_error_code(error_code, error_message)
        raise CPEConsultationError(error_message, code=normalized_code)
    cab = data.get("cabecera", {}) or {}
    client_tax_id = _find_first(
        data,
        {
            "cuitDestinatario",
            "cuitDestino",
            "cuitDestinatarioFinal",
            "cuitDestinatarioComercial",
            "cuitPagadorFlete",
        },
    )

    client = _match_by_tax_id(Client, client_tax_id)
    if client is None:
        normalized_client_tax_id = _normalize_tax_id(client_tax_id)
        if normalized_client_tax_id:
            client, _ = Client.objects.get_or_create(
                tax_id=normalized_client_tax_id,
                defaults={
                    "name": f"Pagador {normalized_client_tax_id}",
                    "email": f"pagador{normalized_client_tax_id}@auto.example.com",
                },
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
            "codGrano",
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
    if peso is None and peso_bruto_descarga is not None:
        peso = _to_decimal(peso_bruto_descarga)
    dominio = _find_first(
        data,
        {
            "dominio",
            "patente",
            "dominioCamion",
            "dominioCamión",
            "dominioChasis",
            "dominioAcoplado",
            "patenteCamion",
            "patenteChasis",
            "patenteAcoplado",
        },
    )

    domain = _normalize_domain(dominio)
    vehicle = None
    if domain:
        vehicle, _ = Vehicle.objects.get_or_create(domain=domain)

    defaults_extra = {
        "client": client,
        "provider": provider,
        "product": product,
        "product_description": producto_descripcion or producto_codigo or "",
        "procedencia": str(procedencia).strip() if procedencia else "",
        "destino": str(destino).strip() if destino else "",
        "peso_bruto_descarga": peso,
        "vehicle": vehicle,
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
    return obj
