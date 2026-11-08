import json, os, re
import shapely
from shapely.geometry import shape, mapping
import topojson as tp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "build")
RAW = os.path.join(HERE, "raw")
OUT = ROOT
os.makedirs(OUT, exist_ok=True)

files = {y: f"TAB333_{y}.json" for y in range(2004, 2019)}
files[2019] = "TAB5850_2019.json"
files.update({y: f"TAB1830_{y}.json" for y in range(2020, 2025)})

codes = names = None
years = []
data = {}
MINFLOW = 10
for y, fn in sorted(files.items()):
    d = json.load(open(os.path.join(RAW, fn), encoding="utf-8"))
    ids, size, v = d["id"], d["size"], d["value"]
    bk = d["dimension"]["Bostadskommun"]["category"]
    ak = d["dimension"]["Arbetsstallekommun"]["category"]
    c = sorted(bk["index"], key=bk["index"].get)
    if codes is None:
        codes = c
        names = [re.sub(r"\s*\(bostad\)\s*$", "", bk["label"][k]) for k in c]
    assert c == codes and sorted(ak["index"], key=ak["index"].get) == codes
    n = len(codes)
    bi, ai = ids.index("Bostadskommun"), ids.index("Arbetsstallekommun")
    strides = [1] * len(ids)
    for k in range(len(ids) - 2, -1, -1):
        strides[k] = strides[k + 1] * size[k + 1]
    workers = [0] * n; jobs = [0] * n; internal = [0] * n
    flows = []
    for i in range(n):
        for j in range(n):
            x = v[i * strides[bi] + j * strides[ai]] or 0
            if not x:
                continue
            workers[i] += x; jobs[j] += x
            if i == j:
                internal[i] = x
            elif x >= MINFLOW:
                flows += [i, j, x]
    data[y] = {"w": workers, "j": jobs, "s": internal, "f": flows}
    years.append(y)
    print(y, sum(workers), len(flows) // 3)

# geometry
g = json.load(open(os.path.join(RAW, "geo.json"), encoding="utf-8"))
feats = {f["properties"]["id"]: f for f in g["features"]}
assert set(feats) == set(codes), set(feats) ^ set(codes)
geoms = [shape(feats[k]["geometry"]) for k in codes]
geoms = [shapely.make_valid(x) for x in geoms]
simp = shapely.coverage_simplify(geoms, tolerance=0.004)
anchors = []
for k, gm in zip(codes, geoms):
    p = feats[k]["properties"].get("geo_point_2d")
    pt = gm.representative_point() if not p else None
    anchors.append([round(p[1], 4), round(p[0], 4)] if p else [round(pt.x, 4), round(pt.y, 4)])
from shapely.geometry.polygon import orient
from shapely.geometry import MultiPolygon, Polygon
def cw(gm):
    # d3-geo wants clockwise exterior rings (spherical winding)
    if isinstance(gm, Polygon):
        return orient(gm, sign=-1.0)
    if isinstance(gm, MultiPolygon):
        return MultiPolygon([orient(p, sign=-1.0) for p in gm.geoms])
    polys = [p for p in getattr(gm, "geoms", []) if isinstance(p, (Polygon, MultiPolygon))]
    return cw(shapely.union_all(polys))
simp = [cw(s) for s in simp]
fc = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "properties": {"i": i}, "geometry": mapping(s)} for i, s in enumerate(simp)]}
topo = tp.Topology(fc, prequantize=4e5, toposimplify=False, topology=True)
topo_json = json.loads(topo.to_json())
topo_json["objects"] = {"k": topo_json["objects"].pop(list(topo_json["objects"])[0])}
for g in topo_json["objects"]["k"]["geometries"]:
    g["id"] = g["properties"]["i"]; del g["properties"]
    if "bbox" in g: del g["bbox"]
assert [g["id"] for g in topo_json["objects"]["k"]["geometries"]] == list(range(len(codes)))

out = {
    "codes": codes, "names": names, "lan": [k[:2] for k in codes], "anchor": anchors,
    "years": years, "data": {str(y): data[y] for y in years}, "minflow": MINFLOW,
    "topo": topo_json,
}
s = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
open(os.path.join(OUT, "data.js"), "w", encoding="utf-8").write("window.PENDLA=" + s + ";")
print("bytes", len(s.encode()), "topo", len(json.dumps(topo_json, separators=(",", ":"))))
print(names[:5], names[codes.index("0180")])
