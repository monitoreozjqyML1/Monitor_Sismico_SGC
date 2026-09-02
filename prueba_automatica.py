import json
from datetime import datetime

evento = {
    "id": "PRUEBA_AUTOMATICA_001",
    "magnitud": 5.4,
    "profundidad": 115.0,
    "latitud": 4.50,
    "longitud": -74.70,
    "distancia_bogota": 80.0,
    "lugar": "PRUEBA AUTOMATICA - BOGOTA",
    "fecha_local": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "fecha_utc": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    "agencia": "PRUEBA",
    "felt": None,
    "cdi": None,
    "mmi": None,
    "tipo_magnitud": "Mw",
    "alertas": ["SISMO PROFUNDO"],
    "fecha_deteccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

archivo = "eventos_detectados.json"

try:
    with open(archivo, "r", encoding="utf-8") as f:
        datos = json.load(f)
except FileNotFoundError:
    datos = {}

datos[evento["id"]] = evento

with open(archivo, "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False, indent=4)

print("==============================================")
print(" PRUEBA AUTOMATICA EJECUTADA")
print("==============================================")
print("ID:", evento["id"])
print("Magnitud:", evento["magnitud"])
print("Profundidad:", evento["profundidad"], "km")
print("Distancia:", evento["distancia_bogota"], "km")
print("Alerta:", evento["alertas"][0])
print("Archivo:", archivo)
print("==============================================")
