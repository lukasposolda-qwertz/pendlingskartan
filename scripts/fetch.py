import json, time, urllib.request, urllib.parse, os, sys

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "raw")
os.makedirs(OUT, exist_ok=True)
BASE = "https://api.scb.se/ov0104/v2beta/api/v2/tables/{}/data"

def fetch(table, kon, year):
    fn = os.path.join(OUT, f"{table}_{year}.json")
    if os.path.exists(fn):
        return
    q = [("lang", "sv"), ("outputFormat", "json-stat2"),
         ("valueCodes[Kon]", kon), ("valueCodes[Tid]", year),
         ("valueCodes[Bostadskommun]", "*"), ("valueCodes[Arbetsstallekommun]", "*"),
         ("valueCodes[ContentsCode]", "*")]
    url = BASE.format(table) + "?" + urllib.parse.urlencode(q)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                data = r.read()
            open(fn, "wb").write(data)
            print(table, year, len(data), flush=True)
            return
        except Exception as e:
            print("retry", table, year, e, flush=True)
            time.sleep(5 * (attempt + 1))
    sys.exit(f"failed {table} {year}")

for y in range(2020, 2025):
    fetch("TAB1830", "1+2", str(y)); time.sleep(1)
for y in range(2004, 2019):
    fetch("TAB333", "4", str(y)); time.sleep(1)
fetch("TAB5850", "4", "2019")
