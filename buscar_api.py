import re

with open("sgc_app.js", encoding="utf-8") as archivo:
    texto = archivo.read()

# Buscar URLs completas dentro del JavaScript
urls = set(re.findall(r'https?://[^"\'\s<>]+', texto))

# Palabras que nos interesan específicamente
palabras = [
    "eqevents",
    "earthquake",
    "earthquakes",
    "eventos",
    "events",
    "sismo",
    "sismos",
    "seismic",
    "catalogo",
    "catalog",
]

resultados = []

for url in urls:
    url_limpia = url.rstrip(".,;)")
    
    if any(palabra in url_limpia.lower() for palabra in palabras):
        resultados.append(url_limpia)

resultados = sorted(set(resultados))

print("==============================================")
print("CANDIDATAS RELACIONADAS CON EVENTOS SISMICOS")
print("==============================================")
print("TOTAL:", len(resultados))
print()

for url in resultados:
    print(url)