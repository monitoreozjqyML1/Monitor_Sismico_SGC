import requests

url = "https://archive.sgc.gov.co/events/SGC2026sqaovc/detail.json"

headers = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Cache-Control": "no-cache",
    "Origin": "https://www.sgc.gov.co",
    "Pragma": "no-cache",
    "Referer": "https://www.sgc.gov.co/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
}

r = requests.get(url, headers=headers, timeout=30)

print("STATUS:", r.status_code)
print("BYTES:", len(r.content))
print("CONTENT-TYPE:", r.headers.get("Content-Type"))

if r.status_code == 200:
    print("SGC_ACCESS_OK")
else:
    print("SGC_ACCESS_ERROR")
