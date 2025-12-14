from decimal import Decimal
from unittest.mock import patch

import afip.fe_service  # noqa: F401
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from billing.models import Client, Invoice


class FacturacionAPITestCase(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="admin", password="password", is_staff=True
        )
        self.user = user_model.objects.create_user(
            username="user", password="password", is_staff=False
        )
        self.admin_token = str(RefreshToken.for_user(self.admin).access_token)
        self.user_token = str(RefreshToken.for_user(self.user).access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        self.client_obj = Client.objects.create(
            name="Cliente Test",
            email="cliente@example.com",
            tax_id="20-12345678-9",
            fiscal_address="Calle Falsa 123",
            tax_condition=Client.CONDICION_IVA_CHOICES[0][0],
        )

    def authenticate(self, token: str):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    @patch("afip.fe_service.fe.obtener_tipos_comprobante_validos", return_value=[11, 12, 13])
    @patch("afip.fe_service._render_pdf_to_bytes", return_value=b"PDF")
    @patch("afip.fe_service.fe.solicitar_cae")
    def test_emitir_nota_credito_con_cbtes_asoc(self, mock_solicitar_cae, _mock_pdf, mock_tipos):
        mock_solicitar_cae.return_value = {
            "cae": "12345678901234",
            "cae_due": "20251231",
            "cbte_nro": 42,
            "xml": "<xml></xml>",
            "observations": ["Obs"],
            "events": ["Evt"],
        }

        payload = {
            "client_id": self.client_obj.id,
            "amount": "100.00",
            "pto_vta": 3,
            "cbte_tipo": 13,
            "doc_tipo": 80,
            "doc_nro": "20-12345678-9",
            "cbtes_asoc": {
                "tipo": 11,
                "pto_vta": 3,
                "nro": 123,
                "cuit": "20-12345678-9",
                "cbte_fch": "2024-01-15",
            },
        }

        response = self.client.post("/api/facturas/emitir/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_solicitar_cae.assert_called_once()
        mock_tipos.assert_called_once_with(cuit="TU_CUIT_EMISOR", pto_vta=3)

        call_kwargs = mock_solicitar_cae.call_args.kwargs
        self.assertIn("cbtes_asoc", call_kwargs)
        self.assertEqual(
            call_kwargs["cbtes_asoc"],
            [{"tipo": 11, "pto_vta": 3, "nro": 123, "cuit": "20123456789", "cbte_fch": "20240115"}],
        )
        self.assertNotIn("periodo_asoc", call_kwargs)

        invoice = Invoice.objects.get()
        self.assertEqual(invoice.cbte_tipo, 13)
        self.assertEqual(invoice.amount, Decimal("100.00"))
        self.assertIn("cbtes_asoc", invoice.metadata)
        self.assertEqual(invoice.metadata["cbtes_asoc"][0]["cbte_fch"], "20240115")
        self.assertIn("observations", invoice.metadata)
        self.assertIn("events", invoice.metadata)

        self.assertIn("metadata", response.data)
        self.assertEqual(
            response.data["metadata"]["cbtes_asoc"][0]["cbte_fch"],
            "20240115",
        )

    @patch("afip.fe_service.fe.obtener_tipos_comprobante_validos", return_value=[11, 12, 13])
    @patch("afip.fe_service._render_pdf_to_bytes", return_value=b"PDF")
    @patch("afip.fe_service.fe.solicitar_cae")
    def test_emitir_nota_credito_con_periodo_asoc(self, mock_solicitar_cae, _mock_pdf, mock_tipos):
        mock_solicitar_cae.return_value = {
            "cae": "98765432109876",
            "cae_due": "20251231",
            "cbte_nro": 7,
            "xml": "<xml></xml>",
        }

        payload = {
            "client_id": self.client_obj.id,
            "amount": "150.00",
            "pto_vta": 4,
            "cbte_tipo": 12,
            "doc_tipo": 80,
            "doc_nro": "20-12345678-9",
            "periodo_asoc": {
                "desde": "2023-05-01",
                "hasta": "2023-05-31",
            },
        }

        response = self.client.post("/api/facturas/emitir/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_solicitar_cae.assert_called_once()
        mock_tipos.assert_called_once_with(cuit="TU_CUIT_EMISOR", pto_vta=4)

        call_kwargs = mock_solicitar_cae.call_args.kwargs
        self.assertNotIn("cbtes_asoc", call_kwargs)
        self.assertEqual(
            call_kwargs["periodo_asoc"],
            {"desde": "20230501", "hasta": "20230531"},
        )

        invoice = Invoice.objects.get(cbte_nro=7)
        self.assertEqual(invoice.cbte_tipo, 12)
        self.assertEqual(invoice.metadata.get("periodo_asoc"), {"desde": "20230501", "hasta": "20230531"})
        self.assertIn("metadata", response.data)
        self.assertEqual(
            response.data["metadata"]["periodo_asoc"],
            {"desde": "20230501", "hasta": "20230531"},
        )

    @patch("afip.fe_service.fe.obtener_tipos_comprobante_validos", return_value=[12])
    @patch("afip.fe_service.fe.solicitar_cae")
    def test_emitir_factura_tipo_no_habilitado(self, mock_solicitar_cae, mock_tipos):
        payload = {
            "client_id": self.client_obj.id,
            "amount": "100.00",
            "pto_vta": 3,
            "cbte_tipo": 11,
            "doc_tipo": 80,
            "doc_nro": "20-12345678-9",
        }

        response = self.client.post("/api/facturas/emitir/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cbte_tipo", response.data)
        mock_solicitar_cae.assert_not_called()
        mock_tipos.assert_called_once_with(cuit="TU_CUIT_EMISOR", pto_vta=3)

    def test_usuario_no_admin_no_puede_emitir(self):
        self.authenticate(self.user_token)

        payload = {
            "client_id": self.client_obj.id,
            "amount": "100.00",
            "pto_vta": 3,
            "cbte_tipo": 12,
            "doc_tipo": 80,
            "doc_nro": "20-12345678-9",
        }

        response = self.client.post("/api/facturas/emitir/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_listado_facturas_requiere_autenticacion(self):
        self.client.credentials()

        response = self.client.get("/api/facturas/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
