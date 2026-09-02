import re

with open("sgc_app.js", encoding="utf-8") as archivo:
    texto = archivo.read()

urls = sorted(set(re.findall(r"https?://[^\s\"']+", texto)))

print("URL ENCONTRADAS:", len(urls))
print()

for url in urls:
    url_minuscula = url.lower()

    if any(palabra in url_minuscula for palabra in [
        "sgc",
        "arcgis",
        "sismo",
        "api",
        "server",
        "service",
        "rest"
    ]):
        print(url)