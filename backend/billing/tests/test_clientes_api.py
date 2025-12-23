from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from billing.models import Client


class ClientesAPITestCase(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="user@example.com", password="password", is_staff=False
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        self.cliente = Client.objects.create(
            name="Cliente Original",
            email="cliente@ejemplo.com",
            tax_id="20-12345678-9",
            fiscal_address="Calle Falsa 123",
            tax_condition=5,
        )

    def test_actualizar_cliente(self):
        payload = {
            "name": "Cliente Editado",
            "email": "nuevo@mail.com",
            "tax_id": "20123456789",
            "fiscal_address": "Siempre Viva 742",
            "tax_condition": 4,
        }

        response = self.client.put(
            f"/api/clientes/{self.cliente.id}/", payload, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.name, payload["name"])
        self.assertEqual(self.cliente.email, payload["email"])
        self.assertEqual(self.cliente.tax_id, payload["tax_id"])
        self.assertEqual(self.cliente.fiscal_address, payload["fiscal_address"])
        self.assertEqual(self.cliente.tax_condition, payload["tax_condition"])

    def test_validaciones_al_actualizar(self):
        response = self.client.patch(
            f"/api/clientes/{self.cliente.id}/", {"name": ""}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)
