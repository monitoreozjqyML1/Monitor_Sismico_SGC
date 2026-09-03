import requests
import json
import os
import math
from datetime import datetime, timedelta


# ============================================================
# CONFIGURACIÓN
# ============================================================

URL_SGC = (
    "https://archive.sgc.gov.co/"
    "feed/v1.0.1/summary/five_days_all.json"
)

ARCHIVO_EVENTOS = "eventos_detectados.json"

DIAS_RETENCION = 30


# ============================================================
# TELEGRAM
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID"
)


# ============================================================
# BOGOTÁ
# ============================================================

LAT_BOGOTA = 4.7110
LON_BOGOTA = -74.0721


# ============================================================
# RADIO GENERAL DE SEGUIMIENTO
# ============================================================

DISTANCIA_REGISTRO = 200.0


# ============================================================
# CRITERIO 1 - SISMO PROFUNDO
# ============================================================

MAGNITUD_PROFUNDO = 5.0
DISTANCIA_PROFUNDO = 200.0
PROFUNDIDAD_MIN_PROFUNDO = 80.0
PROFUNDIDAD_MAX_PROFUNDO = 125.0


# ============================================================
# CRITERIO 2 - SISMO CERCANO Y SUPERFICIAL
# ============================================================

MAGNITUD_CERCANO = 4.0
DISTANCIA_CERCANO = 100.0
PROFUNDIDAD_MIN_CERCANO = 0.0
PROFUNDIDAD_MAX_CERCANO = 80.0


# ============================================================
# CARGAR EVENTOS REGISTRADOS
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

        # ----------------------------------------------------
        # FORMATO NUEVO
        # ----------------------------------------------------

        if isinstance(datos, dict):

            if "eventos" in datos:

                eventos = datos.get(
                    "eventos",
                    {}
                )

                if isinstance(eventos, dict):
                    return eventos

                if isinstance(eventos, list):

                    resultado = {}

                    for evento in eventos:

                        if isinstance(evento, dict):

                            evento_id = evento.get(
                                "id"
                            )

                            if evento_id:
                                resultado[
                                    evento_id
                                ] = evento

                    return resultado

            # ------------------------------------------------
            # COMPATIBILIDAD CON FORMATO ANTERIOR
            # ------------------------------------------------

            resultado = {}

            for evento_id, evento in datos.items():

                if isinstance(evento, dict):

                    if evento.get("id"):

                        resultado[
                            evento_id
                        ] = evento

            return resultado

        # ----------------------------------------------------
        # COMPATIBILIDAD SI EL JSON ES UNA LISTA
        # ----------------------------------------------------

        if isinstance(datos, list):

            resultado = {}

            for evento in datos:

                if isinstance(evento, dict):

                    evento_id = evento.get(
                        "id"
                    )

                    if evento_id:

                        resultado[
                            evento_id
                        ] = evento

            return resultado

    except Exception as error:

        print(
            f"⚠️ Error leyendo {ARCHIVO_EVENTOS}: {error}"
        )

        return {}

    return {}


# ============================================================
# GUARDAR EVENTOS Y RESUMEN
# ============================================================

def guardar_eventos_registrados(
    eventos,
    resumen
):

    datos = {

        "actualizado": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "periodo_retencion_dias": DIAS_RETENCION,

        "resumen": resumen,

        "eventos": eventos

    }

    with open(
        ARCHIVO_EVENTOS,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            datos,
            archivo,
            ensure_ascii=False,
            indent=4
        )


# ============================================================
# ELIMINAR EVENTOS ANTIGUOS
# ============================================================

def limpiar_eventos_antiguos(
    eventos
):

    limite = (
        datetime.now()
        -
        timedelta(
            days=DIAS_RETENCION
        )
    )

    eventos_limpios = {}

    eliminados = 0

    for evento_id, evento in eventos.items():

        if not isinstance(evento, dict):
            continue

        fecha_texto = evento.get(
            "fecha_deteccion"
        )

        if not fecha_texto:

            eventos_limpios[
                evento_id
            ] = evento

            continue

        try:

            fecha_evento = datetime.strptime(
                fecha_texto,
                "%Y-%m-%d %H:%M:%S"
            )

            if fecha_evento >= limite:

                eventos_limpios[
                    evento_id
                ] = evento

            else:

                eliminados += 1

        except ValueError:

            eventos_limpios[
                evento_id
            ] = evento

    print(
        f"    Eventos eliminados por antigüedad: "
        f"{eliminados}"
    )

    return eventos_limpios


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

    return datos.get(
        "features",
        []
    )


# ============================================================
# CALCULAR DISTANCIA A BOGOTÁ
# ============================================================

def calcular_distancia_km(
    lat,
    lon
):

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
        math.sin(
            diferencia_lat / 2
        ) ** 2

        +

        math.cos(lat1)
        *
        math.cos(lat2)
        *
        math.sin(
            diferencia_lon / 2
        ) ** 2
    )

    a = max(
        0.0,
        min(
            1.0,
            a
        )
    )

    distancia = (
        2
        *
        radio_tierra
        *
        math.asin(
            math.sqrt(a)
        )
    )

    return distancia


# ============================================================
# ENVIAR ALERTA POR TELEGRAM
# ============================================================

def enviar_alerta_telegram(
    resultado
):

    if not TELEGRAM_BOT_TOKEN:

        print(
            "⚠️ TELEGRAM_BOT_TOKEN no está configurado."
        )

        return False

    if not TELEGRAM_CHAT_ID:

        print(
            "⚠️ TELEGRAM_CHAT_ID no está configurado."
        )

        return False

    url = (
        "https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}"
        "/sendMessage"
    )

    alertas = resultado.get(
        "alertas",
        []
    )

    tipo_alerta = ", ".join(
        alertas
    )

    lugar = resultado.get(
        "lugar"
    ) or "No informado"

    fecha_local = resultado.get(
        "fecha_local"
    ) or "No informada"

    agencia = resultado.get(
        "agencia"
    ) or "No informada"

    tipo_magnitud = resultado.get(
        "tipo_magnitud"
    ) or "No informado"

    mensaje = (
        "🚨 <b>ALERTA SÍSMICA SGC</b>\n"
        "\n"
        f"<b>Magnitud:</b> {resultado['magnitud']}\n"
        f"<b>Profundidad:</b> {resultado['profundidad']} km\n"
        f"<b>Distancia a Bogotá:</b> "
        f"{resultado['distancia_bogota']} km\n"
        f"<b>Ubicación:</b> {lugar}\n"
        f"<b>Tipo de alerta:</b> {tipo_alerta}\n"
        f"<b>Hora local:</b> {fecha_local}\n"
        f"<b>ID SGC:</b> {resultado['id']}\n"
        f"<b>Agencia:</b> {agencia}\n"
        f"<b>Tipo de magnitud:</b> {tipo_magnitud}\n"
        "\n"
        "Fuente: Servicio Geológico Colombiano"
    )

    datos = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    try:

        respuesta = requests.post(
            url,
            data=datos,
            timeout=30
        )

        respuesta.raise_for_status()

        resultado_telegram = respuesta.json()

        if resultado_telegram.get("ok"):

            print(
                "    📱 Alerta enviada correctamente por Telegram."
            )

            return True

        print(
            "⚠️ Telegram respondió con error:"
        )

        print(
            resultado_telegram
        )

        return False

    except Exception as error:

        print(
            f"⚠️ Error enviando alerta por Telegram: {error}"
        )

        return False


# ============================================================
# ANALIZAR EVENTO
# ============================================================

def analizar_evento(
    evento
):

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

        if len(coordenadas) < 3:
            return None

        # ----------------------------------------------------
        # COORDENADAS DEL FEED SGC
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
        # VALIDAR COORDENADAS
        # ----------------------------------------------------

        if not (
            -90 <= lat <= 90
        ):
            return None

        if not (
            -180 <= lon <= 180
        ):
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
        # FILTRO GENERAL
        # ----------------------------------------------------

        if distancia > DISTANCIA_REGISTRO:

            return None

        # ====================================================
        # EVALUAR ALERTAS
        # ====================================================

        alertas = []

        # ----------------------------------------------------
        # CRITERIO 1 - SISMO PROFUNDO
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # CRITERIO 2 - SISMO CERCANO Y SUPERFICIAL
        # ----------------------------------------------------

        cumple_cercano = (

            magnitud >= MAGNITUD_CERCANO

            and

            distancia <= DISTANCIA_CERCANO

            and

            profundidad >= PROFUNDIDAD_MIN_CERCANO

            and

            profundidad < PROFUNDIDAD_MAX_CERCANO

        )

        if cumple_cercano:

            alertas.append(
                "SISMO CERCANO Y SUPERFICIAL"
            )

        # ----------------------------------------------------
        # CATEGORÍA GENERAL
        # ----------------------------------------------------

        if alertas:

            categoria = "ALERTA"

        else:

            categoria = "SIN ALERTA"

        # ----------------------------------------------------
        # REGISTRO
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

            "categoria": categoria,

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
# GENERAR RESUMEN
# ============================================================

def generar_resumen(
    eventos
):

    total_sismos = len(
        eventos
    )

    alertas_profundas = 0

    alertas_cercanas = 0

    total_alertas = 0

    sismos_sin_alerta = 0

    for evento in eventos.values():

        if not isinstance(
            evento,
            dict
        ):
            continue

        alertas = evento.get(
            "alertas",
            []
        )

        if (
            "SISMO PROFUNDO"
            in alertas
        ):

            alertas_profundas += 1

        if (
            "SISMO CERCANO Y SUPERFICIAL"
            in alertas
        ):

            alertas_cercanas += 1

        if (
            evento.get(
                "categoria"
            )
            == "ALERTA"
        ):

            total_alertas += 1

        else:

            sismos_sin_alerta += 1

    porcentaje_alertas = 0.0

    if total_sismos > 0:

        porcentaje_alertas = round(
            (
                total_alertas
                /
                total_sismos
            )
            *
            100,
            2
        )

    return {

        "sismos_200km": total_sismos,

        "total_alertas": total_alertas,

        "alertas_profundas": alertas_profundas,

        "alertas_cercanas_superficiales": alertas_cercanas,

        "sismos_sin_alerta": sismos_sin_alerta,

        "porcentaje_alertas": porcentaje_alertas

    }


# ============================================================
# CONSULTA ÚNICA
# ============================================================

def realizar_consulta():

    print("=" * 70)

    print(
        "       MONITOR SISMICO SGC - GITHUB ACTIONS"
    )

    print("=" * 70)

    print()

    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        "Consultando SGC..."
    )

    # ========================================================
    # CONSULTAR SGC
    # ========================================================

    try:

        eventos = obtener_eventos()

        print(
            f"    Eventos recibidos: "
            f"{len(eventos)}"
        )

    except Exception as error:

        print(
            f"❌ Error consultando SGC: {error}"
        )

        return 1

    # ========================================================
    # CARGAR REGISTROS EXISTENTES
    # ========================================================

    eventos_registrados_original = (
        cargar_eventos_registrados()
    )

    print(
        f"    Eventos registrados antes de limpiar: "
        f"{len(eventos_registrados_original)}"
    )

    eventos_registrados = dict(
        eventos_registrados_original
    )

    # ========================================================
    # LIMPIAR EVENTOS DE MÁS DE 30 DÍAS
    # ========================================================

    eventos_registrados = (
        limpiar_eventos_antiguos(
            eventos_registrados
        )
    )

    # ========================================================
    # CONTADORES
    # ========================================================

    sismos_200km_nuevos = 0

    nuevas_alertas = 0

    # ========================================================
    # ANALIZAR EVENTOS
    # ========================================================

    for evento in eventos:

        resultado = analizar_evento(
            evento
        )

        if resultado is None:
            continue

        evento_id = resultado[
            "id"
        ]

        # ----------------------------------------------------
        # EVITAR DUPLICADOS
        # ----------------------------------------------------

        if evento_id in eventos_registrados:

            continue

        # ----------------------------------------------------
        # REGISTRAR NUEVO EVENTO
        # ----------------------------------------------------

        eventos_registrados[
            evento_id
        ] = resultado

        sismos_200km_nuevos += 1

        # ----------------------------------------------------
        # SI ES ALERTA
        # ----------------------------------------------------

        if resultado[
            "categoria"
        ] == "ALERTA":

            nuevas_alertas += 1

            print()

            print(
                "🚨 NUEVA ALERTA SÍSMICA"
            )

            print(
                f"    ID:          "
                f"{resultado['id']}"
            )

            print(
                f"    Magnitud:    "
                f"{resultado['magnitud']}"
            )

            print(
                f"    Profundidad: "
                f"{resultado['profundidad']} km"
            )

            print(
                f"    Distancia:   "
                f"{resultado['distancia_bogota']} km"
            )

            print(
                f"    Lugar:       "
                f"{resultado['lugar']}"
            )

            print(
                f"    Categoría:   "
                f"{resultado['categoria']}"
            )

            print(
                f"    Alerta:      "
                f"{', '.join(resultado['alertas'])}"
            )

            # ------------------------------------------------
            # ENVIAR TELEGRAM
            # ------------------------------------------------

            enviar_alerta_telegram(
                resultado
            )

    # ========================================================
    # GENERAR RESUMEN
    # ========================================================

    resumen = generar_resumen(
        eventos_registrados
    )

    # ========================================================
    # DETECTAR CAMBIOS
    # ========================================================

    hubo_cambios = (
        eventos_registrados
        !=
        eventos_registrados_original
    )

    # ========================================================
    # GUARDAR
    # ========================================================

    if hubo_cambios:

        guardar_eventos_registrados(
            eventos_registrados,
            resumen
        )

        print()

        print(
            "    💾 Se actualizó eventos_detectados.json"
        )

    else:

        print()

        print(
            "    ℹ️ No hubo cambios en los eventos registrados."
        )

        print(
            "    ℹ️ No se modificó eventos_detectados.json."
        )

    # ========================================================
    # RESUMEN
    # ========================================================

    print()

    print(
        "---------------- RESUMEN ----------------"
    )

    print(
        f"    Sismos registrados <= 200 km: "
        f"{resumen['sismos_200km']}"
    )

    print(
        f"    Sismos sin alerta: "
        f"{resumen['sismos_sin_alerta']}"
    )

    print(
        f"    Alertas profundas: "
        f"{resumen['alertas_profundas']}"
    )

    print(
        f"    Alertas cercanas/superficiales: "
        f"{resumen['alertas_cercanas_superficiales']}"
    )

    print(
        f"    Total de alertas: "
        f"{resumen['total_alertas']}"
    )

    print(
        f"    Porcentaje de alertas: "
        f"{resumen['porcentaje_alertas']}%"
    )

    print(
        f"    Nuevos sismos <= 200 km: "
        f"{sismos_200km_nuevos}"
    )

    print(
        f"    Nuevas alertas: "
        f"{nuevas_alertas}"
    )

    print(
        "------------------------------------------"
    )

    print()

    print(
        "Consulta finalizada correctamente."
    )

    return 0


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        realizar_consulta()
    )