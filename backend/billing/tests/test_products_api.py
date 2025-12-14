from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from billing.models import Product


class ProductosAPITestCase(APITestCase):
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

    def authenticate(self, token: str):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_crear_producto_exitoso(self):
        self.authenticate(self.admin_token)
        payload = {
            "name": "Granos de Maíz",
            "afip_code": "MZ-001",
            "default_tariff": "150.50",
        }

        response = self.client.post("/api/productos/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertEqual(response.data["name"], payload["name"])
        self.assertEqual(response.data["afip_code"], payload["afip_code"])
        self.assertEqual(response.data["default_tariff"], "150.50")

        product = Product.objects.get(pk=response.data["id"])
        self.assertEqual(product.name, payload["name"])
        self.assertEqual(product.afip_code, payload["afip_code"])
        self.assertEqual(product.default_tariff, Decimal("150.50"))

    def test_usuario_no_admin_no_puede_crear(self):
        self.authenticate(self.user_token)
        payload = {
            "name": "Granos de Maíz",
            "afip_code": "MZ-001",
            "default_tariff": "150.50",
        }

        response = self.client.post("/api/productos/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_crear_producto_requiere_nombre(self):
        self.authenticate(self.admin_token)
        payload = {
            "name": "  ",
        }

        response = self.client.post("/api/productos/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_actualizar_producto_permite_limpiar_codigo(self):
        self.authenticate(self.admin_token)
        product = Product.objects.create(
            name="Soja",
            afip_code="SOJ-01",
            default_tariff=Decimal("200.00"),
        )

        payload = {
            "afip_code": "",
            "default_tariff": "250.00",
        }

        response = self.client.patch(
            f"/api/productos/{product.id}/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertIsNone(product.afip_code)
        self.assertEqual(product.default_tariff, Decimal("250.00"))

    def test_actualizar_producto_requiere_nombre_si_se_envia(self):
        self.authenticate(self.admin_token)
        product = Product.objects.create(
            name="Trigo",
            afip_code=None,
            default_tariff=Decimal("100.00"),
        )

        response = self.client.patch(
            f"/api/productos/{product.id}/",
            {"name": ""},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("name", response.data)

    def test_listado_requiere_autenticacion(self):
        response = self.client.get("/api/productos/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
