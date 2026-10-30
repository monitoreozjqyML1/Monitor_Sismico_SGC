import unittest
from unittest.mock import Mock, patch
import requests
import monitor_sgc_cloud as monitor


class PruebasIntegracionSGC(unittest.TestCase):

    @patch.object(monitor.requests, "post")
    def test_http_403_lanza_error(self, mock_post):
        respuesta = Mock()
        respuesta.raise_for_status.side_effect = requests.HTTPError(
            "403 Forbidden"
        )
        mock_post.return_value = respuesta

        with self.assertRaises(monitor.ErrorConsultaSGC):
            monitor.obtener_eventos()

    @patch.object(monitor.requests, "post")
    def test_timeout_lanza_error(self, mock_post):
        mock_post.side_effect = requests.Timeout("Timeout simulado")

        with self.assertRaises(monitor.ErrorConsultaSGC):
            monitor.obtener_eventos()

    @patch.object(monitor.requests, "post")
    def test_html_invalido_lanza_error(self, mock_post):
        respuesta = Mock()
        respuesta.text = '{"error":"respuesta inesperada"}'
        respuesta.raise_for_status.return_value = None
        mock_post.return_value = respuesta

        with self.assertRaises(monitor.ErrorConsultaSGC):
            monitor.obtener_eventos()

    def test_fallo_sgc_no_limpia_ni_guarda_catalogo(self):
        catalogo = {
            "SGC2026TEST": {
                "id": "SGC2026TEST",
                "properties": {"mag": 3.0}
            }
        }

        with patch.object(
            monitor, "cargar_eventos_registrados",
            return_value=catalogo
        ) as mock_cargar, patch.object(
            monitor, "obtener_eventos",
            side_effect=monitor.ErrorConsultaSGC("Fallo simulado")
        ), patch.object(
            monitor, "limpiar_eventos_antiguos"
        ) as mock_limpiar, patch.object(
            monitor, "guardar_eventos_registrados"
        ) as mock_guardar:

            with self.assertRaises(monitor.ErrorConsultaSGC):
                monitor.realizar_consulta()

            mock_cargar.assert_called_once()
            mock_limpiar.assert_not_called()
            mock_guardar.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
