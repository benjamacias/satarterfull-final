from django.test import SimpleTestCase
from unittest.mock import patch

from afip.solicitar_cae import solicitar_cae


class SolicitarCaeNotasTest(SimpleTestCase):
    @patch("afip.solicitar_cae.consultar_ultimo_comprobante", return_value=1)
    @patch("afip.solicitar_cae._read_wsaa_credentials", return_value=("token", "sign"))
    def test_notas_requieren_comprobantes_o_periodo_asociado(self, _mock_wsaa, _mock_ultimo):
        nota_tipos = [2, 3, 7, 8, 12, 13]

        for tipo in nota_tipos:
            with self.subTest(cbte_tipo=tipo):
                with self.assertRaisesMessage(
                    ValueError,
                    "Para Notas de Débito/Crédito debés enviar cbtes_asoc o periodo_asoc",
                ):
                    solicitar_cae(
                        cuit="20123456789",
                        pto_vta=1,
                        importe="100.00",
                        cbte_tipo=tipo,
                        concepto=2,
                        doc_tipo=80,
                        doc_nro="20-12345678-9",
                    )
