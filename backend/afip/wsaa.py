from pathlib import Path
from datetime import datetime
from lxml import etree
from .obtener_token import AfipPaths, crear_TRA, firmar_TRA, obtener_token_sign

BASE_DIR = Path(__file__).resolve().parents[1]
SECRETS = BASE_DIR / "secrets"

def _paths():
    return AfipPaths(
        certificate=SECRETS / "afip_certificado.pem",
        private_key=SECRETS / "afip_private.key",
        credentials_dir=SECRETS,
    )

def _ta_valid(ta_path: Path) -> bool:
    if not ta_path.exists():
        return False
    try:
        root = etree.fromstring(ta_path.read_bytes())
        exp = root.findtext(".//expirationTime")
        if not exp:
            return False
        exp_dt = datetime.fromisoformat(exp.replace("Z",""))
        return exp_dt > datetime.utcnow()
    except Exception:
        return False

def get_token_sign(service="wsfe"):
    paths = _paths()
    if service in ("wsfe", "wscpe"):
        ta = paths.ta
        token_file, sign_file = paths.token, paths.sign
    else:
        ta = paths.ta_a13
        token_file, sign_file = paths.token_a13, paths.sign_a13

    if _ta_valid(ta):
        return token_file.read_text().strip(), sign_file.read_text().strip()

    if service in ("wsfe", "wscpe"):
        crear_TRA(paths, service=service)
        firmar_TRA(paths)
        return obtener_token_sign(paths)
    else:
        from .obtener_token import obtener_token_sign_a13
        return obtener_token_sign_a13(paths, homologacion=False)
