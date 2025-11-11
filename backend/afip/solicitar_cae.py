import logging
import ssl
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Union
from zeep import Client
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from zeep.helpers import serialize_object
from zeep.transports import Transport



LOGGER = logging.getLogger(__name__)


# ======================
# Adaptador SSL
# ======================
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")  # baja seguridad para AFIP
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


import re
import requests
from zeep import Client, Settings
from zeep.transports import Transport
from zeep.helpers import serialize_object
from zeep.exceptions import Fault

def _only_digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))

def _deep_get(d, key):
    """Busca 'key' en cualquier nivel de un dict/list anidado."""
    if isinstance(d, dict):
        if key in d:
            return d[key]
        for v in d.values():
            r = _deep_get(v, key)
            if r is not None:
                return r
    elif isinstance(d, list):
        for v in d:
            r = _deep_get(v, key)
            if r is not None:
                return r
    return None

import re
import requests
from zeep import Client, Settings
from zeep.transports import Transport
from zeep.helpers import serialize_object
from zeep.exceptions import Fault

WSDL_PADRON = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13?WSDL"

def _only_digits(value) -> str:
    return re.sub(r"\D+", "", str(value or ""))

def _deep_get(d, key):
    """Busca 'key' en cualquier nivel de un dict/list anidado."""
    if isinstance(d, dict):
        if key in d:
            return d[key]
        for v in d.values():
            r = _deep_get(v, key)
            if r is not None:
                return r
    elif isinstance(d, list):
        for v in d:
            r = _deep_get(v, key)
            if r is not None:
                return r
    return None

def _extract_id_condicion_iva(data):
    """
    Intenta extraer persona->datosRegimenGeneral->idCondicionIva
    contemplando que datosRegimenGeneral puede ser dict o list.
    """
    persona = (data or {}).get("persona") or {}
    rg = persona.get("datosRegimenGeneral")

    # puede ser dict
    if isinstance(rg, dict):
        val = rg.get("idCondicionIva")
        if val is not None:
            return val

    # o lista de dicts
    if isinstance(rg, list):
        for nodo in rg:
            if isinstance(nodo, dict) and "idCondicionIva" in nodo:
                return nodo["idCondicionIva"]

    # último recurso: búsqueda profunda
    return _deep_get(persona, "idCondicionIva")



import requests
import xml.etree.ElementTree as ET

import requests
import xml.etree.ElementTree as ET

def consultar_cliente(cuit_cliente, token, sign):
    """
    Consulta Padrón A13 (getPersona) y devuelve TODOS los datos organizados en un dict.
    Regla de negocio: si NO existe 'razon_social', fijar condición como 'Consumidor Final' (id=5).
    - Requiere token/sign emitidos para 'ws_sr_padron_a13'
    - No inventa otros datos: solo organiza lo que AFIP publica
    - Si hay Fault, retorna None
    """
    CUIT_REP = "27225103440"  # tu CUIT emisor
    PADRON_A13_URL = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA13"

    ns = {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "a13":  "http://a13.soap.ws.server.puc.sr/",
    }

    # Operación en ns A13; los hijos sin ns
    soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:a13="http://a13.soap.ws.server.puc.sr/">
  <soapenv:Header/>
  <soapenv:Body>
    <a13:getPersona>
      <token>{token}</token>
      <sign>{sign}</sign>
      <cuitRepresentada>{int(CUIT_REP)}</cuitRepresentada>
      <idPersona>{int(cuit_cliente)}</idPersona>
    </a13:getPersona>
  </soapenv:Body>
</soapenv:Envelope>"""

    headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "getPersona"}
    r = requests.post(PADRON_A13_URL, data=soap_body.encode("utf-8"), headers=headers, timeout=60)

    root = ET.fromstring(r.content)

    # Fault → corto
    if root.find(".//soap:Fault", ns) is not None:
        return None

    # personaReturn/persona o persona directo
    persona = (root.find(".//a13:personaReturn/a13:persona", ns)
               or root.find(".//a13:persona", ns))
    if persona is None:
        return None

    def _tx(elem, tag):
        return (elem.findtext(f"a13:{tag}", default="", namespaces=ns) or "").strip()

    data = {}

    # Metadata (si viene)
    md = root.find(".//a13:personaReturn/a13:metadata", ns)
    if md is not None:
        data["metadata"] = {
            "fechaHora": _tx(md, "fechaHora"),
            "servidor":  _tx(md, "servidor"),
        }

    # Identificación básica
    data["id_persona"]   = _tx(persona, "idPersona")
    data["tipo_persona"] = _tx(persona, "tipoPersona")
    data["estado_clave"] = _tx(persona, "estadoClave")
    data["tipo_clave"]   = _tx(persona, "tipoClave")
    data["apellido"]     = _tx(persona, "apellido")
    data["nombre"]       = _tx(persona, "nombre")
    data["razon_social"] = _tx(persona, "razonSocial")

    # Documento
    doc_tipo = _tx(persona, "tipoDocumento")
    doc_nro  = _tx(persona, "numeroDocumento")
    if doc_tipo or doc_nro:
        data["documento"] = {"tipo": doc_tipo, "numero": doc_nro}

    # Domicilios (varios)
    domicilios = []
    for dom in persona.findall("a13:domicilio", ns):
        domicilios.append({
            "tipo":           _tx(dom, "tipoDomicilio"),
            "calle":          _tx(dom, "calle"),
            "numero":         _tx(dom, "numero"),
            "piso":           _tx(dom, "piso"),
            "oficinaDptoLocal": _tx(dom, "oficinaDptoLocal"),
            "direccion":      _tx(dom, "direccion"),
            "localidad":      _tx(dom, "localidad"),
            "codigo_postal":  _tx(dom, "codigoPostal"),
            "id_provincia":   _tx(dom, "idProvincia"),
            "provincia":      _tx(dom, "descripcionProvincia"),
            "estado":         _tx(dom, "estadoDomicilio"),
        })
    if domicilios:
        data["domicilios"] = domicilios

    # Datos de Régimen General (condición IVA, etc.)
    regimenes = []
    for rg in persona.findall("a13:datosRegimenGeneral", ns):
        item = {
            "idCondicionIva": _tx(rg, "idCondicionIva"),
            "periodo":        _tx(rg, "periodo"),
            "categoria":      _tx(rg, "categoria"),
            "impuesto":       _tx(rg, "impuesto"),
            "descripcion":    _tx(rg, "descripcion"),
        }
        item = {k: v for k, v in item.items() if v}
        if "idCondicionIva" in item and item["idCondicionIva"].isdigit():
            item["idCondicionIva"] = int(item["idCondicionIva"])
        if item:
            regimenes.append(item)
    if regimenes:
        data["datos_regimen_general"] = regimenes

    # Impuestos (si vienen)
    impuestos = []
    for it in persona.findall("a13:impTrib", ns):
        item = {
            "idImpuesto":  _tx(it, "idImpuesto"),
            "descripcion": _tx(it, "desc"),
            "periodo":     _tx(it, "periodo"),
            "estado":      _tx(it, "estado"),
        }
        item = {k: v for k, v in item.items() if v}
        if "idImpuesto" in item and item["idImpuesto"].isdigit():
            item["idImpuesto"] = int(item["idImpuesto"])
        if item:
            impuestos.append(item)
    if impuestos:
        data["impuestos"] = impuestos

    # Actividades (si vienen)
    actividades = []
    for ac in persona.findall("a13:actividad", ns):
        item = {
            "idActividad": _tx(ac, "idActividad"),
            "descripcion": _tx(ac, "descripcionActividad"),
            "orden":       _tx(ac, "orden"),
            "periodo":     _tx(ac, "periodo"),
        }
        item = {k: v for k, v in item.items() if v}
        if "idActividad" in item and item["idActividad"].isdigit():
            item["idActividad"] = int(item["idActividad"])
        if "orden" in item and item["orden"].isdigit():
            item["orden"] = int(item["orden"])
        if item:
            actividades.append(item)
    if actividades:
        data["actividades"] = actividades

    # Monotributo (si viene)
    monos = []
    for mt in persona.findall("a13:datosMonotributo", ns):
        item = {
            "categoria": _tx(mt, "categoriaMonotributo"),
            "periodo":   _tx(mt, "periodo"),
            "impuesto":  _tx(mt, "impuesto"),
            "estado":    _tx(mt, "estado"),
        }
        item = {k: v for k, v in item.items() if v}
        if item:
            monos.append(item)
    if monos:
        data["monotributo"] = monos

    # Empleador (si viene)
    empleador = persona.find("a13:empleador", ns)
    if empleador is not None:
        block = {"estado": _tx(empleador, "estado"), "periodo": _tx(empleador, "periodo")}
        data["empleador"] = {k: v for k, v in block.items() if v}

    # --------- SUMMARY con la condición IVA aplicada ---------
    def _cond_text(cid):
        return {1: "Responsable Inscripto", 5: "Consumidor Final", 6: "Monotributista"}.get(cid)

    condition_id = None
    condition_source = None

    # 1) Si A13 publica idCondicionIva, lo usamos
    for rg in data.get("datos_regimen_general", []):
        if isinstance(rg.get("idCondicionIva"), int):
            condition_id = rg["idCondicionIva"]
            condition_source = "a13"
            break

    # 2) Regla de negocio: si NO hay razón social, default a Consumidor Final (5)
    if condition_id is None and not data.get("razon_social"):
        condition_id = 5
        condition_source = "fallback_razon_social"

    data["summary"] = {
        "condition_id": condition_id,
        "condition_text": _cond_text(condition_id) if condition_id is not None else None,
        "source": condition_source,
    }

    return data





# ======================
# Consultar último comprobante autorizado
# ======================
def consultar_ultimo_comprobante(session, token, sign, cuit, pto_vta, cbte_tipo):
    url = "https://servicios1.afip.gov.ar/wsfev1/service.asmx"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://ar.gov.afip.dif.FEV1/FECompUltimoAutorizado",
    }

    soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:ar="http://ar.gov.afip.dif.FEV1/">
  <soap:Header/>
  <soap:Body>
    <ar:FECompUltimoAutorizado>
      <ar:Auth>
        <ar:Token>{token}</ar:Token>
        <ar:Sign>{sign}</ar:Sign>
        <ar:Cuit>{cuit}</ar:Cuit>
      </ar:Auth>
      <ar:PtoVta>{pto_vta}</ar:PtoVta>
      <ar:CbteTipo>{cbte_tipo}</ar:CbteTipo>
    </ar:FECompUltimoAutorizado>
  </soap:Body>
</soap:Envelope>"""

    response = session.post(url, data=soap_body.encode("utf-8"), headers=headers, timeout=60)
    response.raise_for_status()
    tree = ET.fromstring(response.text)
    ultimo = tree.find(".//{http://ar.gov.afip.dif.FEV1/}CbteNro")
    return int(ultimo.text) if ultimo is not None else 0


def _read_wsaa_credentials() -> tuple[str, str]:
    with open("secrets/token.txt") as f:
        token = f.read().strip()
    with open("secrets/sign.txt") as f:
        sign = f.read().strip()
    return token, sign


def consultar_tipos_comprobante(session, token, sign, cuit, pto_vta) -> List[int]:
    url = "https://servicios1.afip.gov.ar/wsfev1/service.asmx"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://ar.gov.afip.dif.FEV1/FEParamGetTiposCbte",
    }

    soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:ar="http://ar.gov.afip.dif.FEV1/">
  <soap:Header/>
  <soap:Body>
    <ar:FEParamGetTiposCbte>
      <ar:Auth>
        <ar:Token>{token}</ar:Token>
        <ar:Sign>{sign}</ar:Sign>
        <ar:Cuit>{cuit}</ar:Cuit>
      </ar:Auth>
    </ar:FEParamGetTiposCbte>
  </soap:Body>
</soap:Envelope>"""

    response = session.post(url, data=soap_body.encode("utf-8"), headers=headers, timeout=60)
    response.raise_for_status()
    tree = ET.fromstring(response.text)

    namespace = "{http://ar.gov.afip.dif.FEV1/}"
    tipos = []
    for node in tree.findall(f".//{namespace}CbteTipo"):
        tipo_id = node.findtext(f"{namespace}Id")
        try:
            if tipo_id is not None:
                tipos.append(int(tipo_id))
        except ValueError:
            continue

    if not tipos:
        errors = _extract_messages(tree, "Err")
        if errors:
            raise RuntimeError(
                "AFIP devolvió errores al consultar tipos de comprobante: " + "; ".join(errors)
            )
        raise RuntimeError(
            f"AFIP no devolvió tipos de comprobante habilitados para el CUIT {cuit} y punto de venta {pto_vta}"
        )

    return tipos


def obtener_tipos_comprobante_validos(*, cuit: str, pto_vta: int) -> List[int]:
    token, sign = _read_wsaa_credentials()
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    return consultar_tipos_comprobante(session, token, sign, cuit, pto_vta)


# ======================
# Solicitar CAE
# ======================
def _ensure_date(value: Union[None, date, datetime, str]) -> Optional[date]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value_str = str(value)

    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value_str, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Formato de fecha inválido: {value}")


def _format_decimal(value: Union[str, float, Decimal]) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _extract_messages(tree: ET.Element, tag: str) -> List[str]:
    namespace = "{http://ar.gov.afip.dif.FEV1/}"
    messages: List[str] = []
    for node in tree.findall(f".//{namespace}{tag}"):
        code = node.findtext(f"{namespace}Code") or ""
        msg = (node.findtext(f"{namespace}Msg") or "").strip()
        if code:
            messages.append(f"{code.strip()}: {msg}")
        elif msg:
            messages.append(msg)
    return messages


def solicitar_cae(
    cuit: str,
    pto_vta: int,
    importe: Union[str, float, Decimal],
    *,
    cbte_tipo: int = 11,                 # 11 = Factura C, 12 = ND C, 13 = NC C
    concepto: int = 2,
    doc_tipo: int = 80,
    doc_nro: Optional[Union[str, int]] = None,
    issue_date: Union[None, date, datetime, str] = None,
    service_start: Union[None, date, datetime, str] = None,
    service_end: Union[None, date, datetime, str] = None,
    payment_due: Union[None, date, datetime, str] = None,
    moneda_id: str = "PES",
    moneda_cotiz: Union[str, float, Decimal] = "1.00",
    cbte_nro: Optional[int] = None,
    # NUEVO
    condicion_iva_receptor_id: Optional[int] = 5,
    cbtes_asoc: Optional[Union[dict, List[dict]]] = None,   # {"tipo": 11, "pto_vta": 3, "nro": 8, "cuit": "...", "cbte_fch": "YYYYMMDD"}
    periodo_asoc: Optional[dict] = None,                    # {"desde": "YYYYMMDD|YYYY-MM-DD", "hasta": "..."}
):
    # Lee token/sign del WSAA previamente generados
    token, sign = _read_wsaa_credentials()
    url = "https://servicios1.afip.gov.ar/wsfev1/service.asmx"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "http://ar.gov.afip.dif.FEV1/FECAESolicitar",
    }

    session = requests.Session()
    session.mount("https://", SSLAdapter())

    # Trae el último número del tipo elegido (11/12/13, etc.)
    ultimo = consultar_ultimo_comprobante(session, token, sign, cuit, pto_vta, cbte_tipo)
    if cbte_nro is None:
        cbte_nro = ultimo + 1
    LOGGER.debug("Último comprobante autorizado: %s", ultimo)
    LOGGER.debug("Número de comprobante a solicitar: %s", cbte_nro)

    # ======================
    # Fechas automáticas
    # ======================
    today = datetime.now().date()
    issue_date_value = _ensure_date(issue_date) or today
    service_start_value = _ensure_date(service_start) or issue_date_value.replace(day=1)
    last_day = (service_start_value.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    service_end_value = _ensure_date(service_end) or last_day
    payment_due_value = _ensure_date(payment_due) or issue_date_value

    cbte_fch = issue_date_value.strftime("%Y%m%d")
    fch_desde = service_start_value.strftime("%Y%m%d")
    fch_hasta = service_end_value.strftime("%Y%m%d")
    fch_vto = payment_due_value.strftime("%Y%m%d")

    # ======================
    # Totales (C → sin IVA)
    # ======================
    total = _format_decimal(importe)
    moneda_cotizacion = Decimal(str(moneda_cotiz)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    doc_nro_digits = "".join(ch for ch in str(doc_nro or "") if ch.isdigit())
    if not doc_nro_digits:
        raise ValueError("El número de documento del receptor es obligatorio para solicitar el CAE")

    # Notas de Débito/Crédito requieren comprobante o período asociado
    if cbte_tipo in (12, 13) and not (cbtes_asoc or periodo_asoc):
        raise ValueError("Para Notas de Débito/Crédito debés enviar cbtes_asoc o periodo_asoc")

    if cbtes_asoc and periodo_asoc:
        raise ValueError(
            "No podés enviar cbtes_asoc y periodo_asoc simultáneamente; elegí solo una estructura."
        )

    # ----- Condición IVA del receptor (obligatorio desde 01/10/2025) -----
    if condicion_iva_receptor_id is None:
        condicion_iva_receptor_id = 5

    cond_iva_xml = (
        f"<ar:CondicionIVAReceptorId>{int(condicion_iva_receptor_id)}</ar:CondicionIVAReceptorId>"
        if condicion_iva_receptor_id is not None
        else ""
    )

    # ----- CbtesAsoc (para NC/ND contra una factura puntual) -----
    cbtes_asoc_xml = ""
    if cbtes_asoc:
        items = []
        if isinstance(cbtes_asoc, dict):
            cbtes_asoc = [cbtes_asoc]
        for it in cbtes_asoc:
            tipo = it["tipo"]; pv = it["pto_vta"]; nro = it["nro"]
            cuit_asoc = it.get("cuit") or cuit
            fch_asoc = it.get("cbte_fch")
            cuit_asoc = "".join(ch for ch in str(cuit_asoc) if ch.isdigit())
            items.append(
                "<ar:CbteAsoc>"
                f"<ar:Tipo>{tipo}</ar:Tipo>"
                f"<ar:PtoVta>{pv}</ar:PtoVta>"
                f"<ar:Nro>{nro}</ar:Nro>"
                f"{f'<ar:Cuit>{cuit_asoc}</ar:Cuit>' if cuit_asoc else ''}"
                f"{f'<ar:CbteFch>{fch_asoc}</ar:CbteFch>' if fch_asoc else ''}"
                "</ar:CbteAsoc>"
            )
        cbtes_asoc_xml = f"<ar:CbtesAsoc>{''.join(items)}</ar:CbtesAsoc>"

    # ----- PeriodoAsoc (para NC/ND por período) -----
    periodo_asoc_xml = ""
    if periodo_asoc:
        fd = _ensure_date(periodo_asoc.get("desde"))
        fh = _ensure_date(periodo_asoc.get("hasta"))
        if not (fd and fh):
            raise ValueError("PeriodoAsoc requiere 'desde' y 'hasta'")
        periodo_asoc_xml = (
            "<ar:PeriodoAsoc>"
            f"<ar:FchDesde>{fd.strftime('%Y%m%d')}</ar:FchDesde>"
            f"<ar:FchHasta>{fh.strftime('%Y%m%d')}</ar:FchHasta>"
            "</ar:PeriodoAsoc>"
        )

    # ======================
    # SOAP body
    # ======================
    soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ar="http://ar.gov.afip.dif.FEV1/">
  <soapenv:Header/>
  <soapenv:Body>
    <ar:FECAESolicitar>
      <ar:Auth>
        <ar:Token>{token}</ar:Token>
        <ar:Sign>{sign}</ar:Sign>
        <ar:Cuit>{cuit}</ar:Cuit>
      </ar:Auth>
      <ar:FeCAEReq>
        <ar:FeCabReq>
          <ar:CantReg>1</ar:CantReg>
          <ar:PtoVta>{pto_vta}</ar:PtoVta>
          <ar:CbteTipo>{cbte_tipo}</ar:CbteTipo>
        </ar:FeCabReq>
        <ar:FeDetReq>
          <ar:FECAEDetRequest>
            <ar:Concepto>{concepto}</ar:Concepto>
            <ar:DocTipo>{doc_tipo}</ar:DocTipo>
            <ar:DocNro>{doc_nro_digits}</ar:DocNro>
            <ar:CbteDesde>{cbte_nro}</ar:CbteDesde>
            <ar:CbteHasta>{cbte_nro}</ar:CbteHasta>
            <ar:CbteFch>{cbte_fch}</ar:CbteFch>
            <ar:ImpTotal>{total:.2f}</ar:ImpTotal>
            <ar:ImpTotConc>0.00</ar:ImpTotConc>
            <ar:ImpNeto>{total:.2f}</ar:ImpNeto>
            <ar:ImpOpEx>0.00</ar:ImpOpEx>
            <ar:ImpTrib>0.00</ar:ImpTrib>
            <ar:ImpIVA>0.00</ar:ImpIVA>
            {cond_iva_xml}
            <ar:FchServDesde>{fch_desde}</ar:FchServDesde>
            <ar:FchServHasta>{fch_hasta}</ar:FchServHasta>
            <ar:FchVtoPago>{fch_vto}</ar:FchVtoPago>
            <ar:MonId>{moneda_id}</ar:MonId>
            <ar:MonCotiz>{moneda_cotizacion:.3f}</ar:MonCotiz>
            {cbtes_asoc_xml}
            {periodo_asoc_xml}
          </ar:FECAEDetRequest>
        </ar:FeDetReq>
      </ar:FeCAEReq>
    </ar:FECAESolicitar>
  </soapenv:Body>
</soapenv:Envelope>"""

    
    response = session.post(url, data=soap_body.encode("utf-8"), headers=headers, timeout=60)
    response.raise_for_status()

    tree = ET.fromstring(response.text)

    fault = tree.find(".//faultstring")
    if fault is not None and fault.text:
        raise RuntimeError(fault.text.strip())

    errors = _extract_messages(tree, "Err")
    if errors:
        raise RuntimeError("AFIP devolvió errores: " + "; ".join(errors))

    observations = _extract_messages(tree, "Obs")

    # (Opcional) extraer eventos informativos
    def _extract_events(tt: ET.Element) -> List[str]:
        ns = "{http://ar.gov.afip.dif.FEV1/}"
        out: List[str] = []
        for evt in tt.findall(f".//{ns}Evt"):
            code = evt.findtext(f"{ns}Code") or ""
            msg = (evt.findtext(f"{ns}Msg") or "").strip()
            if code or msg:
                out.append(f"{code}: {msg}" if code else msg)
        return out

    events = _extract_events(tree)

    cae = tree.findtext(".//{http://ar.gov.afip.dif.FEV1/}CAE")
    if not cae:
        raise RuntimeError("AFIP no devolvió un CAE en la respuesta")

    cae_vto = tree.findtext(".//{http://ar.gov.afip.dif.FEV1/}CAEFchVto") or ""
    cbte_resp = tree.findtext(".//{http://ar.gov.afip.dif.FEV1/}CbteDesde") or str(cbte_nro)
    try:
        cbte_resp_int = int(cbte_resp)
    except (TypeError, ValueError):
        cbte_resp_int = cbte_nro or 0

    if observations:
        LOGGER.warning("AFIP devolvió observaciones para el comprobante %s: %s", cbte_resp_int, "; ".join(observations))

    return {
        "cae": cae,
        "cae_due": cae_vto,
        "cbte_nro": cbte_resp_int,
        "pto_vta": pto_vta,
        "cbte_tipo": cbte_tipo,
        "xml": response.text,
        "observations": observations,
        "events": events,
    }


# ======================
# Main
# ======================
# if __name__ == "__main__":
#     with open("secrets/token.txt") as f:
#         token = f.read().strip()
#     with open("secrets/sign.txt") as f:
#         sign = f.read().strip()
#
#     cuit = "27225103440"
#     pto_vta = 3  # ⚠️ Punto de venta autorizado en AFIP
#
#     # Si paso importe en argumentos → lo uso, si no → default 100.00
#     importe = float(sys.argv[1]) if len(sys.argv) > 1 else 100.00
#
#     resultado = solicitar_cae(
#         token=token,
#         sign=sign,
#         cuit=cuit,
#         pto_vta=pto_vta,
#         importe=importe,
#         doc_nro="20431255570",
#     )
#     print("✔️ CAE obtenido:", resultado["cae"])
#     if resultado.get("cae_due"):
#         print("Vencimiento CAE:", resultado["cae_due"])
