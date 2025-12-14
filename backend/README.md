# Backend (Django) - AFIP CPE + Facturación

## Instalación
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_admin  # crea admin inicial (admin@example.com / Admin123!)
python manage.py seed_demo   # crea Cliente Demo
python manage.py runserver 0.0.0.0:8000
```

### Autenticación y usuarios
- El modelo de usuario usa **email como credencial principal** y agrega el campo `phone`.
- JWT login: `POST /api/auth/login/` con `{ "email": "...", "password": "..." }`.
- Registro: `POST /api/auth/register/` con `{ "email", "phone", "password" }` (rol "user" por defecto).
- Perfil: `GET/PUT /api/auth/profile/` (requiere token) devuelve `email`, `phone` y `role` (`admin` si pertenece al grupo `admin` o tiene staff/superuser).
- Admin inicial: `python manage.py seed_admin` crea usuario `admin@example.com` (`Admin123!`) y asegura el grupo `admin`.

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
