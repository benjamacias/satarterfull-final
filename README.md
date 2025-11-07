# Django + Angular - AFIP CPE & Facturación (Pack completo)

Contiene:
- Backend Django (REST): consulta CPE por CTG, emitir CAE, generar PDF, enviar por email.
- Frontend Angular: formularios para consultar CTG, emitir factura y listar/enviar.
- Migraciones iniciales incluidas + comando `seed_demo`.

## Pasos rápidos
1) Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo   # crea Cliente Demo
python manage.py runserver 0.0.0.0:8000
```

2) Frontend
```bash
cd frontend/angular
npm i
npm start  # http://localhost:4200
```

3) Ajustes
- Colocar certificados AFIP en `backend/secrets/`.
- Configurar `TU_CUIT_EMISOR` en `backend/afip/cpe_service.py` y `backend/afip/fe_service.py`.
- Configurar SMTP en `backend/.env.example` o variables de entorno.
