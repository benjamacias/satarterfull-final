from unittest.mock import Mock, patch

import requests
from rest_framework import status
from rest_framework.test import APITestCase

from billing.models import Client


def _build_response(status_code: int, content: str) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response._content = content.encode("utf-8")
    response.url = "https://serviciosjava.afip.gob.ar/wscpe/services/soap"
    return response


class ConsultarCPEAPITestCase(APITestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(
            name="Cliente Test",
            email="cliente@example.com",
            tax_id="20-12345678-9",
            fiscal_address="Calle Falsa 123",
            tax_condition=Client.CONDICION_IVA_CHOICES[0][0],
        )

    @patch("afip.cpe_service.get_token_sign", return_value=("TOKEN", "SIGN"))
    @patch("afip.cpe_service.requests.post")
    def test_consultar_cpe_ok(self, mock_post: Mock, _mock_token):
        xml = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
          <soapenv:Body>
            <respuesta>
              <cabecera>
                <nroCTG>1234</nroCTG>
              </cabecera>
            </respuesta>
          </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = _build_response(status.HTTP_200_OK, xml)

        response = self.client.post(
            "/api/cpe/consultar/", {"nro_ctg": "1234"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nro_ctg"], "1234")
        mock_post.assert_called_once()

    @patch("afip.cpe_service.get_token_sign", return_value=("TOKEN", "SIGN"))
    @patch("afip.cpe_service.requests.post")
    def test_consultar_cpe_http_error(self, mock_post: Mock, _mock_token):
        mock_post.return_value = _build_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "")

        response = self.client.post(
            "/api/cpe/consultar/", {"nro_ctg": "9999"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data.get("code"), "AFIP_UNAVAILABLE")

    @patch("afip.cpe_service.get_token_sign", return_value=("TOKEN", "SIGN"))
    @patch("afip.cpe_service.requests.post")
    def test_consultar_cpe_token_expirado(self, mock_post: Mock, _mock_token):
        xml = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
          <soapenv:Body>
            <soapenv:Fault>
              <faultcode>soap:Client</faultcode>
              <faultstring>Token expirado</faultstring>
            </soapenv:Fault>
          </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = _build_response(status.HTTP_200_OK, xml)

        response = self.client.post(
            "/api/cpe/consultar/", {"nro_ctg": "1234"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data.get("code"), "TOKEN_EXPIRED")

    @patch("afip.cpe_service.get_token_sign", return_value=("TOKEN", "SIGN"))
    @patch("afip.cpe_service.requests.post")
    def test_consultar_cpe_ctg_invalido(self, mock_post: Mock, _mock_token):
        xml = """
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
          <soapenv:Body>
            <respuesta>
              <errores>
                <error>
                  <codigo>123</codigo>
                  <mensaje>CTG inexistente</mensaje>
                </error>
              </errores>
            </respuesta>
          </soapenv:Body>
        </soapenv:Envelope>
        """
        mock_post.return_value = _build_response(status.HTTP_200_OK, xml)

        response = self.client.post(
            "/api/cpe/consultar/", {"nro_ctg": "0000"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data.get("code"), "INVALID_CTG")

