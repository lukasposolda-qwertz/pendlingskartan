import json, os, pickle
import shapely
from shapely.geometry import LineString, MultiLineString, shape
from shapely.ops import linemerge, unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "build")
o = json.load(open(os.path.join(HERE, "gtfs", "osm_rail.json"), encoding="utf-8"))
lines = [LineString([(p["lon"], p["lat"]) for p in e["geometry"]]) for e in o["elements"] if e.get("geometry") and len(e["geometry"]) > 1]
print("ways", len(lines))
g = json.load(open(os.path.join(HERE, "raw", "geo.json"), encoding="utf-8"))
se = unary_union([shape(f["geometry"]) for f in g["features"]]).buffer(0.02)
merged = linemerge(unary_union(lines))
merged = merged.intersection(se)
merged = linemerge(merged) if merged.geom_type == "MultiLineString" else merged
simp = merged.simplify(0.0025)
parts = list(simp.geoms) if hasattr(simp, "geoms") else [simp]
out = []
for p in parts:
    if p.geom_type != "LineString" or p.length < 0.01:
        continue
    flat = []
    for x, y in p.coords:
        flat += [round(x, 3), round(y, 3)]
    out.append(flat)
print("lines", len(out), "points", sum(len(x) for x in out) // 2)
R = json.load(open(os.path.join(HERE, "gtfs", "rail_partial.json"), encoding="utf-8"))
d = pickle.load(open(os.path.join(HERE, "gtfs", "rail.pkl"), "rb"))
R["osm"] = out
R["ntrains"] = len(d["st"])
s = json.dumps(R, ensure_ascii=False, separators=(",", ":"))
open(os.path.join(ROOT, "rail.js"), "w", encoding="utf-8").write("window.RAIL=" + s + ";")
print("rail.js bytes", len(s.encode()))
