from flask import Flask, jsonify
import requests
from datetime import datetime, timedelta, timezone
from time import monotonic

app = Flask(__name__)

URL_SGC = "https://api.sgc.gov.co/biweekly/biweekly_earthquakes"

@app.route("/")
def inicio():
    return jsonify({
        "servicio": "Diagnostico independiente API SGC",
        "estado": "activo",
        "prueba": "/diagnostico-sgc"
    })

@app.route("/diagnostico-sgc")
def diagnostico_sgc():
    ahora = datetime.now(timezone.utc)
    inicio = ahora - timedelta(days=1)

    parametros = {
        "startdate": inicio.strftime("%Y-%m-%dT%H:%M:%S"),
        "enddate": ahora.strftime("%Y-%m-%dT%H:%M:%S")
    }

    encabezados = {
        "User-Agent": "Monitor-Sismico-SGC/1.0",
        "Accept": "application/json"
    }

    comienzo = monotonic()

    try:
        respuesta = requests.get(
            URL_SGC,
            params=parametros,
            headers=encabezados,
            timeout=45
        )

        duracion = round(monotonic() - comienzo, 2)

        resultado = {
            "estado": "respuesta_recibida",
            "http_status": respuesta.status_code,
            "tiempo_segundos": duracion,
            "periodo_consultado": parametros
        }

        respuesta.raise_for_status()
        datos = respuesta.json()

        if not isinstance(datos, dict):
            raise ValueError("La respuesta no es un objeto JSON")

        features = datos.get("features")

        if not isinstance(features, list):
            raise ValueError("La respuesta no contiene una lista features")

        resultado.update({
            "estado": "exito",
            "tipo": datos.get("type"),
            "eventos_recibidos": len(features),
            "total_metadata": datos.get("metadata", {}).get("count")
                if isinstance(datos.get("metadata"), dict)
                else None
        })

        return jsonify(resultado), 200

    except Exception as error:
        return jsonify({
            "estado": "error",
            "error": str(error),
            "tiempo_segundos": round(monotonic() - comienzo, 2),
            "periodo_consultado": parametros
        }), 502
