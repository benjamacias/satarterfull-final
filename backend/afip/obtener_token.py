from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta
from lxml import etree
import subprocess, requests, base64

BASE_DIR = Path(__file__).resolve().parent

@dataclass
class AfipPaths:
    certificate: Path
    private_key: Path
    credentials_dir: Path

    @property
    def tra(self) -> Path: return self.credentials_dir / "login_ticket_request.xml"
    @property
    def cms(self) -> Path: return self.credentials_dir / "login.cms.der"
    @property
    def token(self) -> Path: return self.credentials_dir / "token.txt"
    @property
    def sign(self) -> Path: return self.credentials_dir / "sign.txt"
    @property
    def ta(self) -> Path: return self.credentials_dir / "ta.xml"

    # --- Archivos específicos para A13 (MISMA UBICACIÓN, NOMBRES DIFERENTES) ---
    @property
    def token_a13(self) -> Path: return self.credentials_dir / "token_a13.txt"
    @property
    def sign_a13(self) -> Path: return self.credentials_dir / "sign_a13.txt"
    @property
    def ta_a13(self) -> Path: return self.credentials_dir / "ta_a13.xml"


def crear_TRA(paths: AfipPaths, service="wsfe"):
    tra = etree.Element("loginTicketRequest", version="1.0")
    header = etree.SubElement(tra, "header")
    etree.SubElement(header, "uniqueId").text = str(int(datetime.now().timestamp()))
    etree.SubElement(header, "generationTime").text = (datetime.now() - timedelta(minutes=10)).isoformat()
    etree.SubElement(header, "expirationTime").text = (datetime.now() + timedelta(minutes=10)).isoformat()
    etree.SubElement(tra, "service").text = service

    xml_string = etree.tostring(tra, pretty_print=True, xml_declaration=True, encoding="UTF-8")
    paths.tra.write_bytes(xml_string)
    print("=== TRA generado ===")
    print(xml_string.decode("utf-8"))


def firmar_TRA(paths: AfipPaths):
    subprocess.run(
        [
            "openssl", "smime", "-sign",
            "-signer", str(paths.certificate),
            "-inkey", str(paths.private_key),
            "-in", str(paths.tra),
            "-out", str(paths.cms),
            "-outform", "DER",
            "-nodetach"
        ],
        check=True
    )
    print("✔️ TRA firmado correctamente.")


def obtener_token_sign(paths: AfipPaths):
    cms = paths.cms.read_bytes()
    cms_b64 = base64.b64encode(cms).decode("utf-8")

    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
      <soapenv:Header/>
      <soapenv:Body>
        <loginCms xmlns="http://wsaa.view.sua.dvadac.desein.afip.gov.ar">
          <in0>{cms_b64}</in0>
        </loginCms>
      </soapenv:Body>
    </soapenv:Envelope>"""

    headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "loginCms"}
    WSAA_URL = "https://wsaa.afip.gov.ar/ws/services/LoginCms"

    response = requests.post(WSAA_URL, data=envelope.encode("utf-8"), headers=headers, timeout=60)

    ns = {"wsaa": "http://wsaa.view.sua.dvadac.desein.afip.gov.ar"}
    tree = etree.fromstring(response.content)
    login_return = tree.find(".//wsaa:loginCmsReturn", namespaces=ns)

    inner_tree = etree.fromstring(login_return.text.encode("utf-8"))
    token = inner_tree.find(".//token").text
    sign = inner_tree.find(".//sign").text

    paths.token.write_text(token)
    paths.sign.write_text(sign)
    paths.ta.write_bytes(etree.tostring(inner_tree, pretty_print=True, encoding="utf-8"))

    print("✔️ Token y Sign guardados.")
    return token, sign


def crear_TRA_a13(paths: AfipPaths):
    """Convenience para A13 — llama a crear_TRA con el servicio correcto."""
    return crear_TRA(paths, service="ws_sr_padron_a13")


def obtener_token_sign_a13(paths: AfipPaths, homologacion: bool = False, wsaa_url: str | None = None):
    """
    Obtiene token/sign para ws_sr_padron_a13.
    - Genera TRA para 'ws_sr_padron_a13'
    - Firma con openssl
    - Intercambia en WSAA (producción u homologación)
    Retorna (token, sign) y guarda en token_a13.txt / sign_a13.txt / ta_a13.xml
    """
    # 1) TRA específica A13
    crear_TRA(paths, service="ws_sr_padron_a13")
    # 2) Firmar
    firmar_TRA(paths)

    # 3) Intercambio en WSAA
    cms_b64 = base64.b64encode(paths.cms.read_bytes()).decode("utf-8")

    envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Header/>
  <soapenv:Body>
    <loginCms xmlns="http://wsaa.view.sua.dvadac.desein.afip.gov.ar">
      <in0>{cms_b64}</in0>
    </loginCms>
  </soapenv:Body>
</soapenv:Envelope>"""

    headers = {"Content-Type": "text/xml; charset=utf-8", "SOAPAction": "loginCms"}

    # Selección de endpoint
    if wsaa_url:
        url = wsaa_url
    else:
        url = "https://wsaa.afip.gov.ar/ws/services/LoginCms" if not homologacion \
              else "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"

    resp = requests.post(url, data=envelope.encode("utf-8"), headers=headers, timeout=60)

    if not resp.ok:
        print(f"[WSAA] HTTP {resp.status_code} en {url}")
        try:
            print(resp.text[:2000])
        except Exception:
            pass
        (paths.credentials_dir / "wsaa_response_err.xml").write_bytes(resp.content)
        raise requests.HTTPError(f"WSAA error HTTP {resp.status_code}", response=resp)

    # Parseo de TA
    ns = {"wsaa": "http://wsaa.view.sua.dvadac.desein.afip.gov.ar"}
    root = etree.fromstring(resp.content)
    login_ret = root.find(".//wsaa:loginCmsReturn", namespaces=ns)
    if login_ret is None or not login_ret.text:
        (paths.credentials_dir / "wsaa_response_err.xml").write_bytes(resp.content)
        raise RuntimeError("WSAA no devolvió loginCmsReturn")

    ta_xml = etree.fromstring(login_ret.text.encode("utf-8"))
    token = ta_xml.findtext(".//token") or ""
    sign  = ta_xml.findtext(".//sign") or ""

    if not token or not sign:
        (paths.credentials_dir / "ta_a13_err.xml").write_bytes(etree.tostring(ta_xml, pretty_print=True, encoding="utf-8"))
        raise RuntimeError("Token/Sign vacíos en TA de A13")

    # --- Guardar en archivos ESPECÍFICOS de A13 ---
    paths.token_a13.write_text(token)
    paths.sign_a13.write_text(sign)
    paths.ta_a13.write_bytes(etree.tostring(ta_xml, pretty_print=True, encoding="utf-8"))

    print("✔️ Token y Sign (A13) guardados en archivos dedicados.")
    return token, sign


def obtener_credenciales_a13(paths: AfipPaths, homologacion: bool = False) -> dict:
    """
    Wrapper: retorna {"service": "ws_sr_padron_a13", "token": ..., "sign": ..., "ta_path": ...}
    (usa los archivos dedicados de A13)
    """
    token, sign = obtener_token_sign_a13(paths, homologacion=homologacion)
    return {
        "service": "ws_sr_padron_a13",
        "token": token,
        "sign": sign,
        "ta_path": str(paths.ta_a13),
    }


if __name__ == "__main__":
    paths = AfipPaths(
        certificate=BASE_DIR / 'secrets' / 'afip_certificado.pem',
        private_key=BASE_DIR / 'secrets' / 'afip_private.key',
        credentials_dir=BASE_DIR / 'secrets'
    )

    # === Token/Sign para WSFE (sin cambios) ===
    crear_TRA(paths, service="wsfe")
    firmar_TRA(paths)
    token, sign = obtener_token_sign(paths)
    print("=== Token (wsfe) ===")
    print(token[:80], "...")
    print("=== Sign  (wsfe) ===")
    print(sign[:80], "...")

    # === Token/Sign específicos para A13 (PRODUCCIÓN / HOMO según necesites) ===
    token_a13, sign_a13 = obtener_token_sign_a13(paths, homologacion=False)
    print("=== Token (A13) ===", token_a13[:80], "...")
    print("=== Sign  (A13) ===", sign_a13[:80], "...")
