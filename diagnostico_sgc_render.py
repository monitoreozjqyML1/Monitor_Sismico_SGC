
import os
import hmac
import requests

from flask import Flask, jsonify, request
from datetime import datetime, timedelta, timezone
from time import monotonic

app = Flask(__name__)

URL_SGC = "https://api.sgc.gov.co/biweekly/biweekly_earthquakes"


@app.route("/")
def inicio():
    return jsonify({
        "servicio": "Diagnostico independiente API SGC",
        "estado": "activo",
        "prueba": "/diagnostico-sgc",
        "api": "/api/sgc/eventos"
    })


def consultar_sgc(dias):
    ahora = datetime.now(timezone.utc)
    inicio = ahora - timedelta(days=dias)

    parametros = {
        "startdate": inicio.strftime("%Y-%m-%dT%H:%M:%S"),
        "enddate": ahora.strftime("%Y-%m-%dT%H:%M:%S")
    }

    encabezados = {
        "User-Agent": "Monitor-Sismico-SGC/1.0",
        "Accept": "application/json"
    }

    comienzo = monotonic()

    respuesta = requests.get(
        URL_SGC,
        params=parametros,
        headers=encabezados,
        timeout=45
    )

    duracion = round(monotonic() - comienzo, 2)

    respuesta.raise_for_status()
    datos = respuesta.json()

    if not isinstance(datos, dict):
        raise ValueError("La respuesta no es un objeto JSON")

    if datos.get("type") != "FeatureCollection":
        raise ValueError("La respuesta no es FeatureCollection")

    features = datos.get("features")

    if not isinstance(features, list) or not features:
        raise ValueError("El SGC no devolvio eventos validos")

    metadata = datos.get("metadata")

    if not isinstance(metadata, dict):
        raise ValueError("La respuesta no contiene metadata valida")

    total = metadata.get("count")

    if total is not None and total != len(features):
        raise ValueError(
            "El total de metadata no coincide con los eventos recibidos"
        )

    return datos, parametros, duracion


@app.route("/diagnostico-sgc")
def diagnostico_sgc():
    comienzo = monotonic()

    try:
        datos, parametros, duracion = consultar_sgc(1)

        return jsonify({
            "estado": "exito",
            "http_status": 200,
            "tiempo_segundos": duracion,
            "periodo_consultado": parametros,
            "tipo": datos.get("type"),
            "eventos_recibidos": len(datos["features"]),
            "total_metadata": datos["metadata"].get("count")
        }), 200

    except Exception as error:
        return jsonify({
            "estado": "error",
            "error": str(error),
            "tiempo_segundos": round(monotonic() - comienzo, 2)
        }), 502


@app.route("/api/sgc/eventos")
def api_sgc_eventos():

    clave_configurada = os.environ.get("SGC_PROXY_TOKEN")

    if not clave_configurada:
        return jsonify({
            "estado": "error",
            "error": "Servicio sin clave configurada"
        }), 503

    autorizacion = request.headers.get("Authorization", "")
    esquema, separador, clave_recibida = autorizacion.partition(" ")

    if (
        not separador
        or esquema.lower() != "bearer"
        or not hmac.compare_digest(
            clave_recibida,
            clave_configurada
        )
    ):
        return jsonify({
            "estado": "no_autorizado"
        }), 401

    try:
        datos, parametros, duracion = consultar_sgc(30)

        return jsonify({
            "estado": "exito",
            "periodo_consultado": parametros,
            "tiempo_segundos": duracion,
            "eventos_recibidos": len(datos["features"]),
            "datos": datos
        }), 200

    except Exception as error:
        print("ERROR API SGC:", error)

        return jsonify({
            "estado": "error",
            "error": str(error)
        }), 502
