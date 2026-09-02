import urllib.request
import urllib.parse
import json
import math
from datetime import datetime, timezone


# ============================================================
# CONFIGURACIÓN
# ============================================================

SGC_URL = (
    "https://srvags.sgc.gov.co/arcgis/rest/services/"
    "catalogo_sismos/catalogo_de_sismos_2/FeatureServer/0/query"
)

# Coordenadas de Bogotá
BOGOTA_LAT = 4.7110
BOGOTA_LON = -74.0721

# Radio de monitoreo
RADIO_KM = 200.0


# ============================================================
# CALCULAR DISTANCIA ENTRE DOS COORDENADAS
# ============================================================

def distancia_km(lat1, lon1, lat2, lon2):

    radio_tierra = 6371.0

    # Convertir coordenadas a radianes
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Diferencias angulares
    diferencia_lat = lat2 - lat1
    diferencia_lon = lon2 - lon1

    # Fórmula de Haversine
    a = (
        math.sin(diferencia_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(diferencia_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return radio_tierra * c

# ============================================================
# CONSULTAR SGC
# ============================================================

def consultar_sgc():

    parametros = {
        "where": "1=1",
        "outFields": (
            "OBJECTID,"
            "ESP_ID_EVENTO_TXT,"
            "ESP_MAGNITUD,"
            "ESP_PROFUNDIDAD,"
            "ESP_FECHA_LONG,"
            "ESP_LATITUD,"
            "ESP_LONGITUD"
        ),
        "returnGeometry": "true",
        "f": "json",
    }

    url = SGC_URL + "?" + urllib.parse.urlencode(parametros)

    print("Conectando con el SGC...")
    print()

    try:

        with urllib.request.urlopen(
            url,
            timeout=30
        ) as respuesta:

            contenido = respuesta.read().decode("utf-8")

        datos = json.loads(contenido)

    except Exception as error:

        print("ERROR DE CONEXIÓN CON EL SGC")
        print(error)
        return []

    if "error" in datos:

        print("EL SGC DEVOLVIÓ UN ERROR")
        print(datos["error"])
        return []

    eventos = datos.get("features", [])

    # --------------------------------------------------------
    # ORDENAR EVENTOS POR FECHA
    # Más reciente primero
    # --------------------------------------------------------

    eventos.sort(
        key=lambda evento: (
            evento["attributes"].get("ESP_FECHA_LONG") or 0
        ),
        reverse=True
    )

    print(f"Eventos recibidos: {len(eventos)}")
    print()

    return eventos
# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print()
    print("=" * 60)
    print("       MONITOR SÍSMICO SGC - BOGOTÁ")
    print("=" * 60)
    print()

    print("Consultando información del SGC...")
    print()

    eventos = consultar_sgc()

    print(f"Eventos recibidos: {len(eventos)}")
    print()

    encontrados = 0

    for evento in eventos:

        atributos = evento["attributes"]

        latitud = atributos.get("ESP_LATITUD")
        longitud = atributos.get("ESP_LONGITUD")
        magnitud = atributos.get("ESP_MAGNITUD")
        profundidad = atributos.get("ESP_PROFUNDIDAD")
        id_evento = atributos.get("ESP_ID_EVENTO_TXT")

        if latitud is None or longitud is None:
            continue

        distancia = distancia_km(
            BOGOTA_LAT,
            BOGOTA_LON,
            latitud,
            longitud
        )

        if distancia <= RADIO_KM:

            encontrados += 1

            print("-" * 60)
            print("🔴 SISMO DENTRO DEL RADIO DE MONITOREO")
            print("-" * 60)

            print(f"ID evento   : {id_evento}")
            print(f"Magnitud    : {magnitud}")
            print(f"Profundidad : {profundidad} km")
            print(f"Latitud     : {latitud}")
            print(f"Longitud    : {longitud}")
            print(f"Distancia   : {distancia:.2f} km")
            print()

    print("=" * 60)

    if encontrados == 0:

        print("No se encontraron sismos dentro de")
        print(f"{RADIO_KM:.0f} km de Bogotá.")

    else:

        print(
            f"Se encontraron {encontrados} "
            f"evento(s) dentro de {RADIO_KM:.0f} km."
        )

    print("=" * 60)
    print()


if __name__ == "__main__":
    main()