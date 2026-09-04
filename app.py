from flask import Flask, render_template, jsonify
import requests
import math
import json
import os
from datetime import datetime


app = Flask(__name__)


# ============================================================
# CONFIGURACIÓN SGC
# ============================================================

URL_SGC = (
    "https://archive.sgc.gov.co/"
    "feed/v1.0.1/summary/five_days_all.json"
)

LAT_BOGOTA = 4.7110
LON_BOGOTA = -74.0721

ARCHIVO_EVENTOS = "eventos_detectados.json"


# ============================================================
# CRITERIO 1 - SISMO PROFUNDO
# ============================================================

MAG_PROFUNDO = 5.0
RADIO_PROFUNDO = 200.0
PROF_MIN_PROFUNDO = 100.0
PROF_MAX_PROFUNDO = 125.0


# ============================================================
# CRITERIO 2 - SISMO CERCANO Y SUPERFICIAL
# ============================================================

MAG_CERCANO = 4.0
RADIO_CERCANO = 100.0
PROF_MAX_CERCANO = 50.0


# ============================================================
# CALCULAR DISTANCIA ENTRE DOS PUNTOS
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
# OBTENER EVENTOS DEL SGC
# ============================================================

def obtener_eventos():

    respuesta = requests.get(
        URL_SGC,
        timeout=30
    )

    respuesta.raise_for_status()

    datos = respuesta.json()

    return datos.get("features", [])


# ============================================================
# LEER EVENTOS ALMACENADOS
# ============================================================

def obtener_alertas_almacenadas():

    if not os.path.exists(ARCHIVO_EVENTOS):
        return []

    try:

        with open(
            ARCHIVO_EVENTOS,
            "r",
            encoding="utf-8"
        ) as archivo:

            datos = json.load(archivo)

        # ----------------------------------------------------
        # FORMATO: LISTA
        # ----------------------------------------------------

        if isinstance(datos, list):
            return datos

        # ----------------------------------------------------
        # FORMATO: DICCIONARIO
        # ----------------------------------------------------

        if isinstance(datos, dict):

            eventos = datos.get("eventos")

            if isinstance(eventos, list):
                return eventos

            if isinstance(eventos, dict):
                return list(eventos.values())

            eventos = []

            for clave, valor in datos.items():

                if isinstance(valor, dict):

                    evento = valor.copy()

                    if not evento.get("id"):
                        evento["id"] = clave

                    eventos.append(evento)

            return eventos

        return []

    except Exception as error:

        print(
            "Error leyendo alertas almacenadas:",
            error
        )

        return []


# ============================================================
# NORMALIZAR EVENTO ALMACENADO
# ============================================================

def normalizar_alerta_almacenada(alerta):

    return {

        "id": alerta.get("id"),

        "lat": alerta.get(
            "latitud",
            alerta.get("lat")
        ),

        "lon": alerta.get(
            "longitud",
            alerta.get("lon")
        ),

        "magnitud": alerta.get(
            "magnitud"
        ),

        "tipo_magnitud": alerta.get(
            "tipo_magnitud",
            alerta.get("magType")
        ),

        "profundidad": alerta.get(
            "profundidad"
        ),

        "distancia": alerta.get(
            "distancia_bogota",
            alerta.get("distancia")
        ),

        "lugar": alerta.get(
            "lugar"
        ),

        "fecha_local": alerta.get(
            "fecha_local"
        ),

        "agencia": alerta.get(
            "agencia"
        ),

        "alertas": alerta.get(
            "alertas",
            []
        ),

        "categoria": alerta.get(
            "categoria"
        ),

        "fecha_deteccion": alerta.get(
            "fecha_deteccion"
        )
    }


# ============================================================
# ANALIZAR EVENTO DEL SGC
# ============================================================

def analizar_evento(evento):

    propiedades = evento.get(
        "properties",
        {}
    )

    geometria = evento.get(
        "geometry",
        {}
    )

    coordenadas = geometria.get(
        "coordinates",
        []
    )

    # --------------------------------------------------------
    # VALIDAR COORDENADAS
    # --------------------------------------------------------

    if len(coordenadas) < 3:
        return None

    # --------------------------------------------------------
    # IMPORTANTE:
    #
    # FEED DEL SGC:
    #
    # [LATITUD, LONGITUD, PROFUNDIDAD]
    # --------------------------------------------------------

    try:

        lat = float(coordenadas[0])
        lon = float(coordenadas[1])
        profundidad = float(coordenadas[2])

    except (TypeError, ValueError):

        return None

    # --------------------------------------------------------
    # VALIDAR COORDENADAS
    # --------------------------------------------------------

    if not (-90 <= lat <= 90):
        return None

    if not (-180 <= lon <= 180):
        return None

    # --------------------------------------------------------
    # MAGNITUD
    # --------------------------------------------------------

    magnitud_raw = propiedades.get(
        "mag"
    )

    if magnitud_raw is None:
        return None

    try:

        magnitud = float(
            magnitud_raw
        )

    except (TypeError, ValueError):

        return None

    # --------------------------------------------------------
    # DISTANCIA A BOGOTÁ
    # --------------------------------------------------------

    distancia = distancia_km(
        LAT_BOGOTA,
        LON_BOGOTA,
        lat,
        lon
    )

    # ========================================================
    # ALERTAS ESPECIALES
    # ========================================================

    alertas = []

    # --------------------------------------------------------
    # SISMO PROFUNDO
    # --------------------------------------------------------

    if (
        magnitud >= MAG_PROFUNDO
        and distancia <= RADIO_PROFUNDO
        and profundidad >= PROF_MIN_PROFUNDO
        and profundidad <= PROF_MAX_PROFUNDO
    ):

        alertas.append(
            "SISMO PROFUNDO"
        )

    # --------------------------------------------------------
    # SISMO CERCANO Y SUPERFICIAL
    # --------------------------------------------------------

    if (
        magnitud >= MAG_CERCANO
        and distancia <= RADIO_CERCANO
        and profundidad <= PROF_MAX_CERCANO
    ):

        alertas.append(
            "SISMO CERCANO Y SUPERFICIAL"
        )

    # ========================================================
    # CATEGORÍA GENERAL
    # ========================================================

    if (
        magnitud >= MAG_PROFUNDO
        and distancia <= RADIO_PROFUNDO
        and profundidad >= PROF_MIN_PROFUNDO
        and profundidad <= PROF_MAX_PROFUNDO
    ):

        categoria = "SISMO PROFUNDO"

    elif (
        magnitud >= MAG_CERCANO
        and distancia <= RADIO_CERCANO
        and profundidad <= PROF_MAX_CERCANO
    ):

        categoria = "SISMO CERCANO Y SUPERFICIAL"

    elif distancia <= 200:

        categoria = (
            "SISMO DENTRO DEL RADIO DE 200 KM"
        )

    else:

        categoria = None

    # ========================================================
    # DEVOLVER EVENTO
    # ========================================================

    return {

        "id": evento.get(
            "id"
        ),

        "lat": lat,

        "lon": lon,

        "magnitud": magnitud,

        "tipo_magnitud": propiedades.get(
            "magType"
        ),

        "profundidad": profundidad,

        "distancia": round(
            distancia,
            1
        ),

        "lugar": propiedades.get(
            "place"
        ),

        "fecha_local": propiedades.get(
            "localTime"
        ),

        "agencia": propiedades.get(
            "agency"
        ),

        "alertas": alertas,

        "categoria": categoria
    }


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.route("/")
def inicio():

    return render_template(
        "monitor.html"
    )


# ============================================================
# API DE EVENTOS
# ============================================================

@app.route("/api/eventos")
def api_eventos():

    try:

        # ----------------------------------------------------
        # OBTENER EVENTOS DEL SGC
        # ----------------------------------------------------

        eventos_sgc = obtener_eventos()

        eventos = []

        eventos_invalidos = 0

        # ----------------------------------------------------
        # PROCESAR EVENTOS
        # ----------------------------------------------------

        for evento in eventos_sgc:

            try:

                resultado = analizar_evento(
                    evento
                )

                if resultado is None:

                    eventos_invalidos += 1

                else:

                    eventos.append(
                        resultado
                    )

            except Exception as error:

                eventos_invalidos += 1

                print(
                    "ERROR PROCESANDO EVENTO:",
                    evento.get("id"),
                    error
                )

        # ====================================================
        # AGREGAR EVENTOS ALMACENADOS
        # ====================================================

        ids_eventos = {

            evento.get("id")

            for evento in eventos

            if evento.get("id")
        }

        alertas_almacenadas = (
            obtener_alertas_almacenadas()
        )

        print(
            "Eventos almacenados encontrados:",
            len(alertas_almacenadas)
        )

        for alerta in alertas_almacenadas:

            alerta_normalizada = (
                normalizar_alerta_almacenada(
                    alerta
                )
            )

            alerta_id = (
                alerta_normalizada.get("id")
            )

            if (
                alerta_id
                and alerta_id not in ids_eventos
            ):

                eventos.append(
                    alerta_normalizada
                )

                ids_eventos.add(
                    alerta_id
                )

        # ====================================================
        # CONTADORES
        # ====================================================

        profundos = sum(

            1

            for evento in eventos

            if (
                "SISMO PROFUNDO"
                in evento.get(
                    "alertas",
                    []
                )
            )
        )

        cercanos = sum(

            1

            for evento in eventos

            if (
                "SISMO CERCANO Y SUPERFICIAL"
                in evento.get(
                    "alertas",
                    []
                )
            )
        )

        dentro_radio = sum(

            1

            for evento in eventos

            if evento.get(
                "categoria"
            ) == (
                "SISMO DENTRO DEL RADIO DE 200 KM"
            )
        )

        # ====================================================
        # RESPUESTA
        # ====================================================

        return jsonify({

            "ok": True,

            "fecha_consulta":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),

            "eventos_recibidos":
                len(eventos_sgc),

            "eventos_validos":
                len(eventos),

            "eventos_invalidos":
                eventos_invalidos,

            "sismos_profundos":
                profundos,

            "sismos_cercanos":
                cercanos,

            "sismos_dentro_radio":
                dentro_radio,

            "eventos":
                eventos
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

    # --------------------------------------------------------
    # LOCAL:
    #   http://127.0.0.1:5000
    #
    # RENDER:
    #   utiliza la variable de entorno PORT
    # --------------------------------------------------------

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