import requests
import json
import os
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

URL_SGC = "https://archive.sgc.gov.co/feed/v1.0.1/summary/five_days_all.json"
URL_DETALLE_SGC = "https://archive.sgc.gov.co/events/"

ARCHIVO_EVENTOS = "eventos_detectados.json"
DIAS_RETENCION = 30

ZONA_HORARIA = ZoneInfo("America/Bogota")

LAT_BOGOTA = 4.7110
LON_BOGOTA = -74.0721

# Magnitud mínima para considerar un evento candidato
# a acelerografía automática.
MAGNITUD_CANDIDATO_ACELEROGRAFICO = 4.0


# ============================================================
# TELEGRAM
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

URL_MONITOR = "https://monitor-sismico-sgc.onrender.com"


# ============================================================
# CARGA Y GUARDADO DE EVENTOS
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

        if isinstance(datos, dict):
            eventos = datos.get("eventos", {})

            if isinstance(eventos, dict):
                return eventos

            if isinstance(eventos, list):
                return {
                    evento.get("id"): evento
                    for evento in eventos
                    if isinstance(evento, dict)
                    and evento.get("id")
                }

        if isinstance(datos, list):
            return {
                evento.get("id"): evento
                for evento in datos
                if isinstance(evento, dict)
                and evento.get("id")
            }

        return {}

    except Exception as error:
        print(
            f"?? No fue posible cargar eventos registrados: "
            f"{error}"
        )
        return {}


def guardar_eventos_registrados(eventos, resumen):
    datos = {
        "actualizado": datetime.now(
            ZONA_HORARIA
        ).isoformat(),
        "periodo_retencion_dias": DIAS_RETENCION,
        "resumen": resumen,
        "eventos": eventos
    }

    try:
        with open(
            ARCHIVO_EVENTOS,
            "w",
            encoding="utf-8"
        ) as archivo:
            json.dump(
                datos,
                archivo,
                ensure_ascii=False,
                indent=2
            )

    except Exception as error:
        print(
            f"?? No fue posible guardar eventos: "
            f"{error}"
        )


def limpiar_eventos_antiguos(eventos):
    fecha_limite = (
        datetime.now(ZONA_HORARIA)
        - timedelta(days=DIAS_RETENCION)
    )

    eventos_validos = {}

    for event_id, evento in eventos.items():
        try:
            fecha_texto = evento.get("fecha_deteccion")

            if not fecha_texto:
                eventos_validos[event_id] = evento
                continue

            fecha_evento = datetime.fromisoformat(
                fecha_texto
            )

            if fecha_evento.tzinfo is None:
                fecha_evento = fecha_evento.replace(
                    tzinfo=ZONA_HORARIA
                )

            if fecha_evento >= fecha_limite:
                eventos_validos[event_id] = evento

        except Exception:
            eventos_validos[event_id] = evento

    return eventos_validos




# ============================================================
# OBTENER EVENTOS DEL SGC
# ============================================================

def obtener_eventos():
    try:
        respuesta = requests.get(
            URL_SGC,
            timeout=30
        )

        respuesta.raise_for_status()

        datos = respuesta.json()

        if isinstance(datos, dict):
            eventos = datos.get(
                "features",
                []
            )

            if isinstance(eventos, list):
                return eventos

        return []

    except Exception as error:
        print(
            f"❌ Error consultando SGC: {error}"
        )
        return []


# ============================================================
# DISTANCIA A BOGOTÁ
# ============================================================

def calcular_distancia_km(lat, lon):
    try:
        lat = float(lat)
        lon = float(lon)

    except (TypeError, ValueError):
        return None

    radio_tierra_km = 6371.0

    lat1 = math.radians(LAT_BOGOTA)
    lon1 = math.radians(LON_BOGOTA)

    lat2 = math.radians(lat)
    lon2 = math.radians(lon)

    diferencia_lat = lat2 - lat1
    diferencia_lon = lon2 - lon1

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

    return radio_tierra_km * c


# ============================================================
# EVENTOS EN COLOMBIA
# ============================================================

def es_evento_colombia(lugar):
    if not lugar:
        return False

    return (
        str(lugar)
        .strip()
        .lower()
        .endswith(", colombia")
    )


# ============================================================
# OBTENER PGA DE BOG.11
# ============================================================

def obtener_pga_bogota(evento_id):
    resultado_base = {
        "estado": "NO DISPONIBLE",
        "estaciones": [],
        "pga_maximo_cm_s2": None,
        "estacion_critica": None,
        "componente_critica": None
    }

    if not evento_id:
        return resultado_base

    url = (
        f"{URL_DETALLE_SGC}"
        f"{evento_id}/detail.json"
    )

    try:
        respuesta = requests.get(
            url,
            timeout=20
        )

        respuesta.raise_for_status()

        datos = respuesta.json()

        propiedades = datos.get(
            "properties",
            {}
        )

        productos = propiedades.get(
            "products",
            {}
        )

        registros = productos.get(
            "sm",
            []
        )

        if not isinstance(registros, list):
            return resultado_base

        for registro in registros:

            if not isinstance(registro, dict):
                continue

            # Solo BOG.11
            if registro.get("stationCode") != "BOG":
                continue

            if str(
                registro.get("locationCode")
            ) != "11":
                continue

            def convertir_pga(nombre):
                valor = registro.get(nombre)

                if valor is None:
                    return None

                try:
                    valor = float(valor)

                    if not math.isfinite(valor):
                        return None

                    return valor

                except (TypeError, ValueError):
                    return None

            pga_e = convertir_pga("pgaE")
            pga_n = convertir_pga("pgaN")
            pga_z = convertir_pga("pgaZ")

            componentes_horizontales = []

            if pga_e is not None:
                componentes_horizontales.append(
                    ("EW", pga_e)
                )

            if pga_n is not None:
                componentes_horizontales.append(
                    ("NS", pga_n)
                )

            if not componentes_horizontales:
                return resultado_base

            componente_critica, pga_maximo = max(
                componentes_horizontales,
                key=lambda item: item[1]
            )

            estacion = {
                "descripcion": registro.get(
                    "description"
                ),
                "stationCode": registro.get(
                    "stationCode"
                ),
                "locationCode": str(
                    registro.get("locationCode")
                ),
                "networkCode": registro.get(
                    "networkCode"
                ),
                "latitude": registro.get(
                    "latitude"
                ),
                "longitude": registro.get(
                    "longitude"
                ),
                "elevation": registro.get(
                    "elevation"
                ),
                "distanceEpicentral": registro.get(
                    "distanceEpicentral"
                ),
                "distanceHipocentral": registro.get(
                    "distanceHipocentral"
                ),
                "pgaE": pga_e,
                "pgaN": pga_n,
                "pgaZ": pga_z
            }

            return {
                "estado": "OK",
                "estaciones": [estacion],
                "pga_maximo_cm_s2": pga_maximo,
                "estacion_critica": "BOG.11",
                "componente_critica": componente_critica
            }

        return resultado_base

    except Exception as error:
        print(
            f"    ⚠️ No fue posible obtener PGA de BOG.11: "
            f"{error}"
        )

        return resultado_base


# ============================================================
# TELEGRAM
# ============================================================

def enviar_alerta_telegram(resultado):

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

    magnitud = resultado.get(
        "magnitud"
    )

    profundidad = resultado.get(
        "profundidad"
    )

    distancia = resultado.get(
        "distancia_km"
    )

    lugar = resultado.get(
        "lugar"
    )

    hora_local = resultado.get("hora_local") or resultado.get("fecha_local")

    mensaje = (
        "🚨 MONITOR SÍSMICO ML1\n\n"
        "Alerta\n"
        f"Magnitud: {magnitud}\n"
        f"Profundidad: {profundidad} km\n"
    )

    if distancia is not None:
        mensaje += (
            f"Distancia a Bogotá: "
            f"{distancia:.1f} km\n"
        )

    mensaje += (
        f"Ubicación: {lugar}\n"
        f"Hora local: {hora_local}\n"
    )

    # --------------------------------------------------------
    # PGA BOG.11
    # --------------------------------------------------------

    acelerografia = resultado.get(
        "acelerografia_bogota"
    )

    if acelerografia:

        estado = acelerografia.get(
            "estado"
        )

        if estado == "OK":

            estaciones = acelerografia.get(
                "estaciones",
                []
            )

            if estaciones:

                estacion = estaciones[0]

                pga_e = estacion.get(
                    "pgaE"
                )

                pga_n = estacion.get(
                    "pgaN"
                )

                pga_z = estacion.get(
                    "pgaZ"
                )

                mensaje += (
                    "\n📊 PGA Bogotá BOG.11\n"
                )

                if pga_e is not None:
                    mensaje += (
                        f"EW: {pga_e:.3f} cm/s²\n"
                    )

                if pga_n is not None:
                    mensaje += (
                        f"NS: {pga_n:.3f} cm/s²\n"
                    )

                if pga_z is not None:
                    mensaje += (
                        f"Z: {pga_z:.3f} cm/s²\n"
                    )

                pga_horizontal = acelerografia.get(
                    "pga_maximo_cm_s2"
                )

                componente = acelerografia.get(
                    "componente_critica"
                )

                if pga_horizontal is not None:

                    mensaje += (
                        f"Horizontal máx.: "
                        f"{pga_horizontal:.3f} cm/s²"
                    )

                    if componente:
                        mensaje += (
                            f" ({componente})"
                        )

                    mensaje += "\n"

        else:
            mensaje += (
                "\n📊 PGA Bogotá BOG.11\n"
                "No disponible en el detalle SGC.\n"
            )

    mensaje += (
        "\nFuente: SGC\n"
        f"{URL_MONITOR}\n\n"
        "Desarrollado por: ML1 - TQMD - ZJQY"
    )

    url_telegram = (
        "https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    datos = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje
    }

    try:
        respuesta = requests.post(
            url_telegram,
            data=datos,
            timeout=20
        )

        respuesta.raise_for_status()

        print(
            "    📱 Alerta enviada a Telegram."
        )

        return True

    except Exception as error:
        print(
            f"    ❌ Error enviando alerta a Telegram: "
            f"{error}"
        )

        return False


# ============================================================
# ANALIZAR EVENTO
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

    try:
        latitud = float(
            coordenadas[0]
        )

        longitud = float(
            coordenadas[1]
        )

        if len(coordenadas) >= 3:
            profundidad = float(
                coordenadas[2]
            )
        else:
            profundidad = None

    except (
        IndexError,
        TypeError,
        ValueError
    ):
        longitud = None
        latitud = None
        profundidad = None

    magnitud = propiedades.get(
        "mag"
    )

    try:
        magnitud = float(
            magnitud
        )

    except (
        TypeError,
        ValueError
    ):
        magnitud = None

    lugar = propiedades.get(
        "place",
        "Ubicación no disponible"
    )

    event_id = (
        evento.get("id")
        or propiedades.get("id")
    )

    distancia = None

    if (
        latitud is not None
        and longitud is not None
    ):
        distancia = calcular_distancia_km(
            latitud,
            longitud
        )

    # --------------------------------------------------------
    # FECHA / HORA
    # --------------------------------------------------------

    hora_local = "No disponible"

    tiempo = propiedades.get(
        "time"
    )

    if tiempo:

        try:

            if isinstance(
                tiempo,
                (int, float)
            ):

                fecha_utc = datetime.fromtimestamp(
                    tiempo / 1000,
                    tz=ZoneInfo("UTC")
                )

            else:

                texto = str(tiempo)

                if texto.endswith("Z"):
                    texto = (
                        texto[:-1]
                        + "+00:00"
                    )

                fecha_utc = datetime.fromisoformat(
                    texto
                )

                if fecha_utc.tzinfo is None:
                    fecha_utc = fecha_utc.replace(
                        tzinfo=ZoneInfo("UTC")
                    )

            fecha_local = fecha_utc.astimezone(
                ZONA_HORARIA
            )

            hora_local = fecha_local.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        except Exception:
            hora_local = str(
                tiempo
            )

    # --------------------------------------------------------
    # CANDIDATO A ACELEROGRAFÍA
    # --------------------------------------------------------

    candidato_acelerografico = (
        magnitud is not None
        and magnitud >= MAGNITUD_CANDIDATO_ACELEROGRAFICO
    )

    resultado = {
        "id": event_id,
        "magnitud": magnitud,
        "profundidad": profundidad,
        "latitud": latitud,
        "longitud": longitud,
        "distancia_km": distancia,
        "lugar": lugar,
        "hora_local": hora_local,
        "candidato_acelerografico": (
            candidato_acelerografico
        ),
        "acelerografia_bogota": {
            "estado": "PENDIENTE",
            "estaciones": [],
            "pga_maximo_cm_s2": None,
            "estacion_critica": None,
            "componente_critica": None
        }
    }

    return resultado


# ============================================================
# RESUMEN
# ============================================================

def generar_resumen(eventos):

    if isinstance(eventos, dict):
        eventos = eventos.values()

    eventos = list(eventos)

    total = len(eventos)

    eventos_m4 = 0
    candidatos = 0
    alertas = 0
    alertas_telegram = 0

    for evento in eventos:

        if not isinstance(evento, dict):
            continue

        magnitud = evento.get(
            "magnitud"
        )

        try:
            magnitud = float(
                magnitud
            )

        except (
            TypeError,
            ValueError
        ):
            magnitud = None

        if (
            magnitud is not None
            and magnitud >= 4.0
        ):
            eventos_m4 += 1

        if evento.get(
            "candidato_acelerografico"
        ):
            candidatos += 1

        if evento.get("alertas"):
            alertas += 1

        if evento.get("alerta_enviada"):
            alertas_telegram += 1

    porcentaje = 0

    if total > 0:
        porcentaje = (
            eventos_m4 / total
        ) * 100

    porcentaje_alertas = 0

    if total > 0:
        porcentaje_alertas = (
            alertas / total
        ) * 100

    return {
        "total_eventos": total,
        "eventos_m4_o_mayores": eventos_m4,
        "candidatos_acelerograficos": candidatos,
        "alertas_telegram": alertas_telegram,
        "porcentaje_m4_o_mayores": round(
            porcentaje,
            2
        ),
        "eventos_mayor_igual_4": eventos_m4,
        "total_candidatos_acelerograficos": candidatos,
        "total_alertas": alertas,
        "porcentaje_alertas": round(
            porcentaje_alertas,
            2
        )
    }


# ============================================================
# CONSULTA PRINCIPAL
# ============================================================

def realizar_consulta():

    print("=" * 70)
    print(
        "MONITOR SÍSMICO SGC - CONSULTA"
    )
    print("=" * 70)

    fecha_consulta = datetime.now(
        ZONA_HORARIA
    )

    print(
        f"🕐 Consulta: "
        f"{fecha_consulta.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    eventos_registrados = (
        cargar_eventos_registrados()
    )

    print(
        f"📂 Eventos registrados previamente: "
        f"{len(eventos_registrados)}"
    )

    eventos_registrados = (
        limpiar_eventos_antiguos(
            eventos_registrados
        )
    )

    ids_registrados = set()

    for event_id in eventos_registrados:
        if event_id:
            ids_registrados.add(
                str(event_id)
            )

    print(
        "🌐 Consultando feed del SGC..."
    )

    eventos = obtener_eventos()

    if not eventos:

        print(
            "⚠️ No se recibieron eventos del SGC."
        )

        resumen = generar_resumen(
            eventos_registrados
        )

        guardar_eventos_registrados(
            eventos_registrados,
            resumen
        )

        return

    print(
        f"📡 Eventos recibidos del SGC: "
        f"{len(eventos)}"
    )

    nuevos = 0
    eventos_colombia = 0

    for evento in eventos:

        resultado = analizar_evento(
            evento
        )

        event_id = resultado.get(
            "id"
        )

        lugar = resultado.get(
            "lugar"
        )

        if not event_id:
            continue

        if not es_evento_colombia(
            lugar
        ):
            continue

        eventos_colombia += 1

        if str(event_id) in ids_registrados:

            evento_existente = eventos_registrados.get(
                str(event_id),
                {}
            )

            if resultado.get(
                "candidato_acelerografico"
            ):

                acelerografia_existente = evento_existente.get(
                    "acelerografia_bogota"
                ) or {}

                estado_existente = acelerografia_existente.get(
                    "estado"
                )

                if estado_existente != "OK":

                    print()
                    print(
                        f"?? Evento ya registrado: {event_id}"
                    )

                    print(
                        "    ?? Reconsultando PGA de BOG.11..."
                    )

                    acelerografia_actualizada = (
                        obtener_pga_bogota(
                            event_id
                        )
                    )

                    if acelerografia_actualizada.get(
                        "estado"
                    ) == "OK":

                        evento_existente[
                            "acelerografia_bogota"
                        ] = acelerografia_actualizada

                        print(
                            "    ? PGA de BOG.11 actualizada."
                        )

                        estaciones = (
                            acelerografia_actualizada.get(
                                "estaciones",
                                []
                            )
                        )

                        if estaciones:

                            estacion = estaciones[0]

                            print(
                                f"       PGA EW: "
                                f"{estacion.get('pgaE')} "
                                f"cm/s?"
                            )

                            print(
                                f"       PGA NS: "
                                f"{estacion.get('pgaN')} "
                                f"cm/s?"
                            )

                            print(
                                f"       PGA Z: "
                                f"{estacion.get('pgaZ')} "
                                f"cm/s?"
                            )

                            print(
                                f"       Horizontal m?x.: "
                                f"{acelerografia_actualizada.get('pga_maximo_cm_s2')} "
                                f"cm/s? "
                                f"({acelerografia_actualizada.get('componente_critica')})"
                            )

                    else:

                        print(
                            "    ?? PGA de BOG.11 "
                            "todav?a no disponible."
                        )

            continue

        print()

        print(
            f"🌎 Nuevo evento: {event_id}"
        )

        print(
            f"    Magnitud: "
            f"{resultado.get('magnitud')}"
        )

        print(
            f"    Profundidad: "
            f"{resultado.get('profundidad')} km"
        )

        print(
            f"    Ubicación: "
            f"{resultado.get('lugar')}"
        )

        distancia = resultado.get(
            "distancia_km"
        )

        if distancia is not None:

            print(
                f"    Distancia Bogotá: "
                f"{distancia:.1f} km"
            )

        # ----------------------------------------------------
        # PGA DE BOG.11
        # ----------------------------------------------------

        if resultado.get(
            "candidato_acelerografico"
        ):

            print(
                "    📊 Consultando PGA de BOG.11..."
            )

            resultado[
                "acelerografia_bogota"
            ] = obtener_pga_bogota(
                event_id
            )

            acelerografia = resultado[
                "acelerografia_bogota"
            ]

            if acelerografia.get(
                "estado"
            ) == "OK":

                estaciones = acelerografia.get(
                    "estaciones",
                    []
                )

                if estaciones:

                    estacion = estaciones[0]

                    print(
                        "    ✅ BOG.11 encontrada."
                    )

                    print(
                        f"       PGA EW: "
                        f"{estacion.get('pgaE')} "
                        f"cm/s²"
                    )

                    print(
                        f"       PGA NS: "
                        f"{estacion.get('pgaN')} "
                        f"cm/s²"
                    )

                    print(
                        f"       PGA Z: "
                        f"{estacion.get('pgaZ')} "
                        f"cm/s²"
                    )

                    print(
                        f"       Horizontal máx.: "
                        f"{acelerografia.get('pga_maximo_cm_s2')} "
                        f"cm/s² "
                        f"({acelerografia.get('componente_critica')})"
                    )

            else:

                print(
                    "    ⚠️ PGA de BOG.11 "
                    "no disponible."
                )

        # ----------------------------------------------------
        # ADAPTAR AL ESQUEMA DEL DASHBOARD
        # ----------------------------------------------------

        resultado["lat"] = resultado.get(
            "latitud"
        )

        resultado["lon"] = resultado.get(
            "longitud"
        )

        resultado["distancia_bogota"] = (
            round(resultado["distancia_km"], 1)
            if resultado.get("distancia_km") is not None
            else None
        )

        propiedades = evento.get(
            "properties",
            {}
        )

        resultado["tipo_magnitud"] = propiedades.get(
            "magType"
        )

        resultado["fecha_local"] = propiedades.get(
            "localTime",
            resultado.get("hora_local")
        )

        resultado["agencia"] = propiedades.get(
            "agency",
            "SGC"
        )

        if resultado.get(
            "candidato_acelerografico"
        ):

            resultado["alertas"] = [
                "SISMO M >= 4.0"
            ]

            resultado["categoria"] = (
                "SISMO CANDIDATO ACELEROGRAFICO (M >= 4.0)"
            )

        else:

            resultado["alertas"] = []

            resultado["categoria"] = (
                "SISMO SIN CRITERIO DE MAGNITUD"
            )

        resultado["fecha_deteccion"] = (
            fecha_consulta.isoformat()
        )

        # ----------------------------------------------------
        # TELEGRAM
        # ----------------------------------------------------

        if resultado.get(
            "candidato_acelerografico"
        ):

            alerta_enviada = (
                enviar_alerta_telegram(
                    resultado
                )
            )

            resultado[
                "alerta_enviada"
            ] = alerta_enviada

        else:

            resultado[
                "alerta_enviada"
            ] = False

        # ----------------------------------------------------
        # REGISTRO
        # ----------------------------------------------------

        eventos_registrados[str(event_id)] = resultado

        ids_registrados.add(
            str(event_id)
        )

        nuevos += 1

    # --------------------------------------------------------
    # RECONCILIACI?N HIST?RICA DE PGA
    # --------------------------------------------------------
    # Algunos eventos M >= 4.0 pueden haber sido registrados
    # cuando el producto de acelerograf?a todav?a no estaba
    # disponible en el SGC. Se reconsulta ?nicamente la PGA
    # pendiente, sin volver a enviar alertas Telegram.
    # --------------------------------------------------------

    pga_historica_actualizada = 0

    for evento_id_historico, evento_historico in (
        eventos_registrados.items()
    ):

        if not isinstance(
            evento_historico,
            dict
        ):
            continue

        if not evento_historico.get(
            "candidato_acelerografico"
        ):
            continue

        acelerografia_historica = (
            evento_historico.get(
                "acelerografia_bogota"
            ) or {}
        )

        if acelerografia_historica.get(
            "estado"
        ) == "OK":
            continue

        print()
        print(
            f"?? Reconciliaci?n PGA hist?rica: "
            f"{evento_id_historico}"
        )

        acelerografia_actualizada = (
            obtener_pga_bogota(
                evento_id_historico
            )
        )

        if acelerografia_actualizada.get(
            "estado"
        ) == "OK":

            evento_historico[
                "acelerografia_bogota"
            ] = acelerografia_actualizada

            pga_historica_actualizada += 1

            estaciones = (
                acelerografia_actualizada.get(
                    "estaciones",
                    []
                )
            )

            print(
                "    ? PGA hist?rica actualizada."
            )

            if estaciones:

                estacion = estaciones[0]

                print(
                    f"       Estaci?n: "
                    f"{estacion.get('stationCode')}."
                    f"{estacion.get('locationCode')}"
                )

                print(
                    f"       PGA EW: "
                    f"{estacion.get('pgaE')} "
                    f"cm/s?"
                )

                print(
                    f"       PGA NS: "
                    f"{estacion.get('pgaN')} "
                    f"cm/s?"
                )

                print(
                    f"       PGA Z: "
                    f"{estacion.get('pgaZ')} "
                    f"cm/s?"
                )

                print(
                    f"       Horizontal m?x.: "
                    f"{acelerografia_actualizada.get('pga_maximo_cm_s2')} "
                    f"cm/s? "
                    f"({acelerografia_actualizada.get('componente_critica')})"
                )

        else:

            print(
                "    ?? PGA hist?rica todav?a no disponible."
            )

    if pga_historica_actualizada:
        print()
        print(
            f"?? PGA hist?ricas actualizadas: "
            f"{pga_historica_actualizada}"
        )

    # --------------------------------------------------------
    # RESUMEN FINAL
    # --------------------------------------------------------

    resumen = generar_resumen(
        eventos_registrados.values()
    )

    guardar_eventos_registrados(
        eventos_registrados,
        resumen
    )

    print()

    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)

    print(
        f"📡 Eventos recibidos: "
        f"{len(eventos)}"
    )

    print(
        f"🇨🇴 Eventos Colombia: "
        f"{eventos_colombia}"
    )

    print(
        f"🆕 Eventos nuevos: "
        f"{nuevos}"
    )

    print(
        f"📊 Total registrados: "
        f"{resumen['total_eventos']}"
    )

    print(
        f"📈 M4.0 o mayores: "
        f"{resumen['eventos_m4_o_mayores']}"
    )

    print(
        f"📡 Candidatos acelerográficos: "
        f"{resumen['candidatos_acelerograficos']}"
    )

    print(
        f"📱 Alertas Telegram: "
        f"{resumen['alertas_telegram']}"
    )

    print(
        f"📊 Porcentaje M4+: "
        f"{resumen['porcentaje_m4_o_mayores']}%"
    )

    print(
        f"🕐 Última consulta: "
        f"{fecha_consulta.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    print("=" * 70)


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    realizar_consulta()


