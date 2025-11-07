from datetime import datetime
import xml.etree.ElementTree as ET

import requests
from django.utils import timezone

from trips.models import CPEAutomotor
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
    obj, _ = CPEAutomotor.objects.update_or_create(
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
        }
    )
    return data
