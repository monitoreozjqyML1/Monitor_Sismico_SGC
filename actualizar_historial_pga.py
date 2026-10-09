import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ARCHIVO_OPERATIVO = Path("eventos_detectados.json")
ARCHIVO_HISTORICO = Path("historial_candidatos_pga.json")
ZONA = ZoneInfo("America/Bogota")
MAGNITUD_MINIMA = 4.0
ESTADOS_CON_DATOS = {"OK"}
ESTADOS_SIN_RESULTADO = {"PENDIENTE", "NO DISPONIBLE", "SIN_DATOS"}


def leer_json(ruta):
    with ruta.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def obtener_eventos(datos):
    eventos = datos.get("eventos", {}) if isinstance(datos, dict) else {}
    if isinstance(eventos, list):
        eventos = {
            str(e.get("id")): e
            for e in eventos
            if isinstance(e, dict) and e.get("id")
        }
    if not isinstance(eventos, dict):
        raise ValueError("Formato de eventos inválido.")
    return eventos


def candidato_valido(evento):
    if not isinstance(evento, dict):
        return False
    try:
        magnitud = float(evento.get("magnitud"))
    except (TypeError, ValueError):
        return False
    return (
        evento.get("candidato_acelerografico") is True
        and magnitud >= MAGNITUD_MINIMA
        and bool(evento.get("id"))
    )


def pga_tiene_datos(pga):
    if not isinstance(pga, dict):
        return False
    estado = str(pga.get("estado", "")).upper()
    return (
        estado in ESTADOS_CON_DATOS
        or bool(pga.get("estaciones"))
        or pga.get("pga_maximo_cm_s2") is not None
    )


def fusionar_evento(anterior, nuevo):
    resultado = deepcopy(anterior)
    for clave, valor in nuevo.items():
        if clave == "acelerografia_bogota":
            continue
        if valor is not None and valor != "":
            resultado[clave] = deepcopy(valor)

    pga_anterior = anterior.get("acelerografia_bogota") or {}
    pga_nuevo = nuevo.get("acelerografia_bogota") or {}

    if pga_tiene_datos(pga_anterior) and not pga_tiene_datos(pga_nuevo):
        resultado["acelerografia_bogota"] = deepcopy(pga_anterior)
    elif pga_tiene_datos(pga_nuevo):
        resultado["acelerografia_bogota"] = deepcopy(pga_nuevo)
    elif pga_anterior:
        resultado["acelerografia_bogota"] = deepcopy(pga_anterior)
    elif pga_nuevo:
        resultado["acelerografia_bogota"] = deepcopy(pga_nuevo)

    return resultado


def main():
    if not ARCHIVO_OPERATIVO.exists():
        raise SystemExit("No existe eventos_detectados.json.")
    if not ARCHIVO_HISTORICO.exists():
        raise SystemExit("No existe historial_candidatos_pga.json.")

    operativo = leer_json(ARCHIVO_OPERATIVO)
    historico = leer_json(ARCHIVO_HISTORICO)
    actuales = obtener_eventos(operativo)
    guardados = historico.get("eventos")

    if not isinstance(guardados, dict):
        raise SystemExit("El histórico no contiene un diccionario de eventos.")

    fusionados = deepcopy(guardados)
    agregados = 0
    actualizados = 0

    for clave, evento in actuales.items():
        if not candidato_valido(evento):
            continue

        event_id = str(evento.get("id") or clave).strip()
        if event_id in fusionados:
            fusion_nueva = fusionar_evento(fusionados[event_id], evento)
            if fusion_nueva != fusionados[event_id]:
                fusionados[event_id] = fusion_nueva
                actualizados += 1
        else:
            fusionados[event_id] = deepcopy(evento)
            agregados += 1

    if len(fusionados) < len(guardados):
        raise SystemExit("ABORTADO: el total histórico no puede disminuir.")

    if agregados == 0 and actualizados == 0:
        print("El hist?rico ya est? al d?a; no se modifica el archivo.")
        print("Total hist?rico:", len(guardados))
        print("Monitor operativo ejecutado: NO")
        print("Telegram utilizado: NO")
        return

    ahora = datetime.now(ZONA).isoformat()
    historico["actualizado"] = ahora
    historico["total_candidatos"] = len(fusionados)
    historico["eventos"] = fusionados

    temporal = ARCHIVO_HISTORICO.with_suffix(".json.tmp")
    with temporal.open("w", encoding="utf-8") as archivo:
        json.dump(historico, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")
        archivo.flush()

    # Verificar el temporal antes de reemplazar el histórico.
    comprobacion = leer_json(temporal)
    if len(comprobacion.get("eventos", {})) != len(fusionados):
        temporal.unlink(missing_ok=True)
        raise SystemExit("ABORTADO: la verificación del archivo temporal falló.")

    temporal.replace(ARCHIVO_HISTORICO)

    estados = {}
    for evento in fusionados.values():
        pga = evento.get("acelerografia_bogota") or {}
        estado = str(pga.get("estado", "SIN_ESTADO"))
        estados[estado] = estados.get(estado, 0) + 1

    print("Actualización histórica completada.")
    print("Candidatos anteriores:", len(guardados))
    print("Candidatos agregados:", agregados)
    print("Registros actualizados:", actualizados)
    print("Total histórico:", len(fusionados))
    print("Estados PGA:", dict(sorted(estados.items())))
    print("Monitor operativo ejecutado: NO")
    print("Telegram utilizado: NO")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("ERROR:", error)
        sys.exit(1)
