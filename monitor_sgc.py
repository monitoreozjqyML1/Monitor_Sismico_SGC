import requests
import json
import os
import time
import math
from datetime import datetime


# ============================================================
# CONFIGURACIÓN
# ============================================================

URL_SGC = (
    "https://archive.sgc.gov.co/"
    "feed/v1.0.1/summary/five_days_all.json"
)

ARCHIVO_EVENTOS = "eventos_detectados.json"

# Consulta cada 60 minutos
INTERVALO_CONSULTA = 60 * 60


# ============================================================
# BOGOTÁ
# ============================================================

LAT_BOGOTA = 4.7110
LON_BOGOTA = -74.0721


# ============================================================
# CRITERIO 1 - SISMO PROFUNDO
# ============================================================

MAGNITUD_PROFUNDO = 5.0
DISTANCIA_PROFUNDO = 200.0

PROFUNDIDAD_MIN_PROFUNDO = 100.0
PROFUNDIDAD_MAX_PROFUNDO = 125.0


# ============================================================
# CRITERIO 2 - SISMO CERCANO Y SUPERFICIAL
# ============================================================

MAGNITUD_CERCANO = 4.0
DISTANCIA_CERCANO = 100.0
PROFUNDIDAD_MAX_CERCANO = 50.0


# ============================================================
# CARGAR EVENTOS YA REGISTRADOS
# ============================================================

def cargar_eventos_registrados():

    if not os.path.exists(ARCHIVO_EVENTOS):
        return {}

    try:

        with open(
            ARCHIVO_EVENTOS,
            "r",
            encoding="utf-8"
        ) as archivo:

            datos = json.load(archivo)

        # Si el archivo tiene formato diccionario
        if isinstance(datos, dict):
            return datos

        # Si tiene formato lista
        if isinstance(datos, list):

            resultado = {}

            for evento in datos:

                if isinstance(evento, dict):

                    evento_id = evento.get("id")

                    if evento_id:
                        resultado[evento_id] = evento

            return resultado

    except Exception as error:

        print(
            f"⚠️ Error leyendo {ARCHIVO_EVENTOS}: {error}"
        )

        return {}

    return {}


# ============================================================
# GUARDAR EVENTOS
# ============================================================

def guardar_eventos_registrados(eventos):

    with open(
        ARCHIVO_EVENTOS,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            eventos,
            archivo,
            ensure_ascii=False,
            indent=4
        )


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
# CALCULAR DISTANCIA A BOGOTÁ
# ============================================================

def calcular_distancia_km(lat, lon):

    radio_tierra = 6371.0

    lat1 = math.radians(
        LAT_BOGOTA
    )

    lat2 = math.radians(
        lat
    )

    diferencia_lat = math.radians(
        lat - LAT_BOGOTA
    )

    diferencia_lon = math.radians(
        lon - LON_BOGOTA
    )

    a = (
        math.sin(diferencia_lat / 2) ** 2
        +
        math.cos(lat1)
        *
        math.cos(lat2)
        *
        math.sin(diferencia_lon / 2) ** 2
    )

    # Evitar errores numéricos
    a = max(
        0.0,
        min(1.0, a)
    )

    distancia = (
        2
        * radio_tierra
        * math.asin(
            math.sqrt(a)
        )
    )

    return distancia


# ============================================================
# ANALIZAR EVENTO
# ============================================================

def analizar_evento(evento):

    try:

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

        # ----------------------------------------------------
        # VALIDAR COORDENADAS
        # ----------------------------------------------------

        if len(coordenadas) < 3:
            return None

        # ----------------------------------------------------
        # IMPORTANTE
        #
        # El feed utilizado del SGC entrega:
        #
        # [LATITUD, LONGITUD, PROFUNDIDAD]
        # ----------------------------------------------------

        lat = float(
            coordenadas[0]
        )

        lon = float(
            coordenadas[1]
        )

        profundidad = float(
            coordenadas[2]
        )

        # ----------------------------------------------------
        # VALIDAR RANGO DE COORDENADAS
        # ----------------------------------------------------

        if not (-90 <= lat <= 90):
            return None

        if not (-180 <= lon <= 180):
            return None

        # ----------------------------------------------------
        # MAGNITUD
        # ----------------------------------------------------

        valor_magnitud = propiedades.get(
            "mag"
        )

        if valor_magnitud is None:
            return None

        magnitud = float(
            valor_magnitud
        )

        # ----------------------------------------------------
        # ID DEL EVENTO
        # ----------------------------------------------------

        evento_id = evento.get(
            "id"
        )

        if not evento_id:
            return None

        # ----------------------------------------------------
        # DISTANCIA A BOGOTÁ
        # ----------------------------------------------------

        distancia = calcular_distancia_km(
            lat,
            lon
        )

        # ----------------------------------------------------
        # EVALUAR CRITERIOS
        # ----------------------------------------------------

        alertas = []

        # ====================================================
        # CRITERIO 1
        # SISMO PROFUNDO
        # ====================================================

        cumple_profundo = (
            magnitud >= MAGNITUD_PROFUNDO
            and
            distancia <= DISTANCIA_PROFUNDO
            and
            profundidad >= PROFUNDIDAD_MIN_PROFUNDO
            and
            profundidad <= PROFUNDIDAD_MAX_PROFUNDO
        )

        if cumple_profundo:

            alertas.append(
                "SISMO PROFUNDO"
            )

        # ====================================================
        # CRITERIO 2
        # SISMO CERCANO Y SUPERFICIAL
        # ====================================================

        cumple_cercano = (
            magnitud >= MAGNITUD_CERCANO
            and
            distancia <= DISTANCIA_CERCANO
            and
            profundidad <= PROFUNDIDAD_MAX_CERCANO
        )

        if cumple_cercano:

            alertas.append(
                "SISMO CERCANO Y SUPERFICIAL"
            )

        # ----------------------------------------------------
        # SI NO CUMPLE NINGÚN CRITERIO
        # ----------------------------------------------------

        if not alertas:
            return None

        # ----------------------------------------------------
        # CREAR REGISTRO
        # ----------------------------------------------------

        registro = {

            "id": evento_id,

            "magnitud": magnitud,

            "profundidad": profundidad,

            "latitud": lat,

            "longitud": lon,

            "distancia_bogota": round(
                distancia,
                2
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

            "tipo_magnitud": propiedades.get(
                "magType"
            ),

            "alertas": alertas,

            "fecha_deteccion": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        }

        return registro

    except (
        TypeError,
        ValueError,
        KeyError,
        IndexError
    ):

        return None


# ============================================================
# MOSTRAR ALERTA
# ============================================================

def mostrar_alerta(evento):

    print()
    print("=" * 70)
    print("🚨 NUEVA ALERTA SÍSMICA")
    print("=" * 70)

    print(
        f"ID:           {evento['id']}"
    )

    print(
        f"Magnitud:     {evento['magnitud']}"
    )

    print(
        f"Profundidad:  {evento['profundidad']} km"
    )

    print(
        f"Distancia:    {evento['distancia_bogota']} km"
    )

    print(
        f"Lugar:        {evento['lugar']}"
    )

    print(
        f"Fecha local:  {evento['fecha_local']}"
    )

    print(
        f"Alerta:       {', '.join(evento['alertas'])}"
    )

    print("=" * 70)
    print()


# ============================================================
# REALIZAR UNA CONSULTA
# ============================================================

def realizar_consulta(eventos_registrados):

    print()

    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        "Consultando SGC..."
    )

    try:

        eventos = obtener_eventos()

        print(
            f"    Eventos recibidos: {len(eventos)}"
        )

    except Exception as error:

        print(
            f"❌ Error consultando SGC: {error}"
        )

        return

    profundos = 0
    cercanos = 0
    nuevas_alertas = 0

    # ========================================================
    # ANALIZAR TODOS LOS EVENTOS
    # ========================================================

    for evento in eventos:

        resultado = analizar_evento(
            evento
        )

        # Evento que no cumple criterios
        if resultado is None:
            continue

        # ----------------------------------------------------
        # CONTADORES
        # ----------------------------------------------------

        if (
            "SISMO PROFUNDO"
            in resultado["alertas"]
        ):

            profundos += 1

        if (
            "SISMO CERCANO Y SUPERFICIAL"
            in resultado["alertas"]
        ):

            cercanos += 1

        # ----------------------------------------------------
        # ID
        # ----------------------------------------------------

        evento_id = resultado["id"]

        # ----------------------------------------------------
        # EVITAR DUPLICADOS
        # ----------------------------------------------------

        if evento_id in eventos_registrados:

            continue

        # ----------------------------------------------------
        # NUEVA ALERTA
        # ----------------------------------------------------

        eventos_registrados[
            evento_id
        ] = resultado

        guardar_eventos_registrados(
            eventos_registrados
        )

        nuevas_alertas += 1

        mostrar_alerta(
            resultado
        )

    # ========================================================
    # RESUMEN
    # ========================================================

    print(
        f"    Criterio 1 - profundos: {profundos}"
    )

    print(
        f"    Criterio 2 - cercanos/superficiales: {cercanos}"
    )

    print(
        f"    Nuevas alertas: {nuevas_alertas}"
    )

    print(
        f"    Alertas almacenadas: "
        f"{len(eventos_registrados)}"
    )


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print("=" * 70)
    print("        MONITOR SÍSMICO SGC - BOGOTÁ")
    print("=" * 70)

    print()

    # ========================================================
    # CRITERIO 1
    # ========================================================

    print(
        "CRITERIO 1 - SISMO PROFUNDO"
    )

    print(
        f"  Magnitud       >= {MAGNITUD_PROFUNDO}"
    )

    print(
        f"  Radio          <= {DISTANCIA_PROFUNDO} km"
    )

    print(
        f"  Profundidad    "
        f"{PROFUNDIDAD_MIN_PROFUNDO} - "
        f"{PROFUNDIDAD_MAX_PROFUNDO} km"
    )

    print()

    # ========================================================
    # CRITERIO 2
    # ========================================================

    print(
        "CRITERIO 2 - SISMO CERCANO Y SUPERFICIAL"
    )

    print(
        f"  Magnitud       >= {MAGNITUD_CERCANO}"
    )

    print(
        f"  Radio          <= {DISTANCIA_CERCANO} km"
    )

    print(
        f"  Profundidad    <= "
        f"{PROFUNDIDAD_MAX_CERCANO} km"
    )

    print()

    print(
        "Consulta cada 60 minutos."
    )

    # ========================================================
    # CARGAR HISTORIAL
    # ========================================================

    eventos_registrados = (
        cargar_eventos_registrados()
    )

    print(
        f"Eventos previamente registrados: "
        f"{len(eventos_registrados)}"
    )

    print()

    print(
        "Presiona CTRL+C para detener."
    )

    print()

    # ========================================================
    # BUCLE PRINCIPAL
    # ========================================================

    while True:

        realizar_consulta(
            eventos_registrados
        )

        print()

        print(
            "Esperando próxima consulta..."
        )

        print(
            f"Próxima consulta en "
            f"{INTERVALO_CONSULTA // 60} minutos."
        )

        try:

            time.sleep(
                INTERVALO_CONSULTA
            )

        except KeyboardInterrupt:

            print()
            print(
                "Monitor detenido."
            )

            break


# ============================================================
# PRUEBA DE PERSISTENCIA Y DUPLICADOS
# ============================================================

def prueba_deduplicacion():

    archivo_prueba = "eventos_prueba.json"

    print()
    print("=" * 70)
    print("       PRUEBA DE PERSISTENCIA Y DUPLICADOS")
    print("=" * 70)
    print()

    # --------------------------------------------------------
    # Evento ficticio
    # --------------------------------------------------------

    evento_prueba = {

        "id": "PRUEBA_DEDUPLICACION_001",

        "magnitud": 5.2,

        "profundidad": 110.0,

        "latitud": 4.50,

        "longitud": -74.70,

        "distancia_bogota": 80.0,

        "lugar": "EVENTO DE PRUEBA",

        "fecha_local": "2026-09-02 12:00:00",

        "agencia": "PRUEBA",

        "tipo_magnitud": "Mw",

        "alertas": [
            "SISMO PROFUNDO"
        ],

        "fecha_deteccion": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    }

    # --------------------------------------------------------
    # Empezamos con un archivo limpio de prueba
    # --------------------------------------------------------

    eventos = {}

    print(
        "1. Guardando evento por primera vez..."
    )

    evento_id = evento_prueba["id"]

    if evento_id not in eventos:

        eventos[evento_id] = evento_prueba

        print(
            "   ✅ Evento guardado."
        )

    guardar_eventos_en_archivo = archivo_prueba

    with open(
        guardar_eventos_en_archivo,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            eventos,
            archivo,
            ensure_ascii=False,
            indent=4
        )

    print()
    print(
        "2. Intentando guardar nuevamente el mismo evento..."
    )

    if evento_id in eventos:

        print(
            "   🛑 DUPLICADO DETECTADO."
        )

        print(
            "   ✅ El evento NO se vuelve a guardar."
        )

    else:

        eventos[evento_id] = evento_prueba

        print(
            "   ❌ ERROR: el duplicado fue aceptado."
        )

    print()
    print(
        f"3. Eventos almacenados: {len(eventos)}"
    )

    print()
    print(
        f"Archivo creado: {archivo_prueba}"
    )

    print()
    print("=" * 70)
    print(
        "       PRUEBA FINALIZADA"
    )
    print("=" * 70)
    print()


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    main()