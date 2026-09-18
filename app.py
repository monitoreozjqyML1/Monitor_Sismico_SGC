from flask import Flask, jsonify, render_template
import json
import math
import os
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

ARCHIVO_EVENTOS = "eventos_detectados.json"

LAT_BOGOTA = 4.7110
LON_BOGOTA = -74.0721

MAGNITUD_CANDIDATO_ACELEROGRAFICO = 4.0


# ============================================================
# DISTANCIA ENTRE DOS PUNTOS
# ============================================================

def distancia_km(lat1, lon1, lat2, lon2):

    radio_tierra = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    diferencia_lat = math.radians(lat2 - lat1)
    diferencia_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(diferencia_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(diferencia_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return radio_tierra * c


# ============================================================
# LEER FUENTE CANÃ“NICA
# ============================================================

def obtener_eventos_almacenados():

    if not os.path.exists(ARCHIVO_EVENTOS):
        return []

    try:

        with open(
            ARCHIVO_EVENTOS,
            "r",
            encoding="utf-8"
        ) as archivo:

            datos = json.load(archivo)

        if isinstance(datos, dict):

            eventos = datos.get("eventos", [])

            if isinstance(eventos, dict):
                return list(eventos.values())

            if isinstance(eventos, list):
                return eventos

        if isinstance(datos, list):
            return datos

        return []

    except Exception as error:

        print(
            "ERROR LEYENDO EVENTOS CANÃ“NICOS:",
            error
        )

        return []


# ============================================================
# NORMALIZACIÃ“N MÃNIMA PARA LA WEB
# ============================================================

def preparar_evento_web(evento):

    resultado = dict(evento)

    # --------------------------------------------------------
    # Coordenadas: conservar ambos nombres si existen.
    # No recalcular si ya vienen del monitor.
    # --------------------------------------------------------

    if resultado.get("latitud") is None and resultado.get("lat") is not None:
        resultado["latitud"] = resultado.get("lat")

    if resultado.get("longitud") is None and resultado.get("lon") is not None:
        resultado["longitud"] = resultado.get("lon")

    if resultado.get("lat") is None and resultado.get("latitud") is not None:
        resultado["lat"] = resultado.get("latitud")

    if resultado.get("lon") is None and resultado.get("longitud") is not None:
        resultado["lon"] = resultado.get("longitud")

    # --------------------------------------------------------
    # Distancia: usar siempre la calculada y almacenada
    # por el monitor.
    # --------------------------------------------------------

    if resultado.get("distancia_bogota") is None:

        if resultado.get("distancia_km") is not None:
            resultado["distancia_bogota"] = resultado.get(
                "distancia_km"
            )

        elif resultado.get("distancia") is not None:
            resultado["distancia_bogota"] = resultado.get(
                "distancia"
            )

    if resultado.get("distancia") is None:
        resultado["distancia"] = resultado.get(
            "distancia_bogota"
        )

    # --------------------------------------------------------
    # Hora: hora_local es la representación prioritaria.
    # fecha_local se mantiene como respaldo histórico.

        resultado["hora_local"] = resultado.get("fecha_local")


    # --------------------------------------------------------
    # Magnitud / tipo
    # --------------------------------------------------------

    if resultado.get("magnitud") is None and resultado.get("mag") is not None:
        resultado["magnitud"] = resultado.get("mag")

    if not resultado.get("tipo_magnitud") and resultado.get("magType"):
        resultado["tipo_magnitud"] = resultado.get("magType")

    # --------------------------------------------------------
    # Lugar / agencia
    # --------------------------------------------------------

    if not resultado.get("lugar") and resultado.get("place"):
        resultado["lugar"] = resultado.get("place")

    if not resultado.get("agencia"):
        resultado["agencia"] = "SGC"

    # --------------------------------------------------------
    # Estructuras que la interfaz espera.
    # No se generan datos PGA nuevos.
    # --------------------------------------------------------

    if "alertas" not in resultado:
        resultado["alertas"] = []

    if "acelerografia_bogota" not in resultado:
        resultado["acelerografia_bogota"] = None

    if "alerta_pga" not in resultado:
        resultado["alerta_pga"] = None

    # --------------------------------------------------------
    # Candidato visual para la interfaz.
    # Esto NO modifica la lÃ³gica del monitor.
    # --------------------------------------------------------

    magnitud = resultado.get("magnitud")

    try:
        es_candidato = (
            magnitud is not None
            and float(magnitud)
            >= MAGNITUD_CANDIDATO_ACELEROGRAFICO
        )
    except (TypeError, ValueError):
        es_candidato = False

    if "candidato_acelerografico" not in resultado:
        resultado["candidato_acelerografico"] = es_candidato

    return resultado


# ============================================================
# PÃGINA PRINCIPAL
# ============================================================

@app.route("/")
def monitor():

    return render_template(
        "monitor.html"
    )


# ============================================================
# API DE EVENTOS
#
# FUENTE ÃšNICA:
# eventos_detectados.json
#
# No consulta directamente al SGC.
# El monitor_sgc_cloud.py es quien consulta SGC,
# normaliza los eventos y actualiza este archivo.
# ============================================================

@app.route("/api/eventos")
def api_eventos():

    try:

        eventos = [
            preparar_evento_web(evento)
            for evento in obtener_eventos_almacenados()
            if isinstance(evento, dict)
        ]

        eventos_colombia = sum(
            1
            for evento in eventos
            if "colombia"
            in str(evento.get("lugar", "")).lower()
        )

        candidatos_acelerograficos = sum(1 for evento in eventos if evento.get("candidato_acelerografico") is True)

        fecha_consulta = datetime.now(
            ZoneInfo("America/Bogota")
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        return jsonify({

            "ok": True,

            "fecha_consulta": fecha_consulta,

            "eventos_recibidos": len(eventos),

            "eventos_validos": len(eventos),

            "eventos_invalidos": 0,

            "eventos_colombia": eventos_colombia,

            "candidatos_acelerograficos":
                candidatos_acelerograficos,

            "eventos_magnitud_4_o_mas":
                candidatos_acelerograficos,

            "eventos": eventos
        })

    except Exception as error:

        print(
            "ERROR GENERAL API:",
            error
        )

        return jsonify({

            "ok": False,

            "error": str(error),

            "eventos": []

        }), 500


# ============================================================
# INICIAR FLASK
# ============================================================

if __name__ == "__main__":

    puerto = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=puerto,
        debug=False
    )



