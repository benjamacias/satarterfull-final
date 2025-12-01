# Backend (Django) - AFIP CPE + Facturación

## Instalación
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo  # crea Cliente Demo
python manage.py runserver 0.0.0.0:8000
```

## Archivos sensibles
Coloca tus certificados/keys en `backend/secrets/`:
- `afip_certificado.pem`
- `afip_private.key`

El helper `afip/obtener_token.py` manejará `token.txt`, `sign.txt`, `ta.xml` en esa carpeta.

## Endpoints
- POST `http://localhost:8000/api/cpe/consultar/` → `{ "nro_ctg": "..." }`
- POST `http://localhost:8000/api/facturas/emitir/` → ver `billing/serializers.py`
- GET  `http://localhost:8000/api/facturas/`
- POST `http://localhost:8000/api/{id}/facturas/enviar/`
- GET  `http://localhost:8000/api/estadisticas/dominios/` → métricas de movimientos y facturación estimada por dominio

## Notas
- Ajusta `TU_CUIT_EMISOR` en `afip/cpe_service.py` y `afip/fe_service.py`.
- Si usas homologación, modifica URLs/flags en tus helpers.
