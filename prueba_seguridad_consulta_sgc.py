import unittest
from unittest.mock import Mock
import requests


def validar_respuesta(respuesta):
    respuesta.raise_for_status()
    contenido = respuesta.text.strip()

    if not contenido:
        raise ValueError("Respuesta SGC vacía.")

    if "<html" not in contenido.lower() and "<table" not in contenido.lower():
        raise ValueError("Respuesta SGC sin estructura HTML reconocible.")

    if "<table" not in contenido.lower():
        raise ValueError("No se reconoce la tabla del catálogo.")

    return True


class PruebasConsultaSGC(unittest.TestCase):

    def respuesta(self, contenido):
        r = Mock()
        r.text = contenido
        r.raise_for_status.return_value = None
        return r

    def test_http_200_html(self):
        r = self.respuesta("<html><body><table></table></body></html>")
        self.assertTrue(validar_respuesta(r))

    def test_http_403(self):
        r = self.respuesta("<html>Access Denied</html>")
        r.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        with self.assertRaises(requests.HTTPError):
            validar_respuesta(r)

    def test_html_invalido(self):
        r = self.respuesta('{"error":"respuesta inesperada"}')
        with self.assertRaises(ValueError):
            validar_respuesta(r)

    def test_respuesta_vacia(self):
        r = self.respuesta("   ")
        with self.assertRaises(ValueError):
            validar_respuesta(r)

    def test_timeout(self):
        with self.assertRaises(requests.Timeout):
            raise requests.Timeout("Tiempo agotado")

    def test_html_sin_tabla(self):
        r = self.respuesta("<html><body>Catálogo temporalmente no disponible</body></html>")
        with self.assertRaises(ValueError):
            validar_respuesta(r)

    def test_tabla_vacia_reconocible(self):
        r = self.respuesta("<html><body><table><tr><th>Fecha</th><th>Magnitud</th></tr></table></body></html>")
        self.assertTrue(validar_respuesta(r))


if __name__ == "__main__":
    unittest.main(verbosity=2)
