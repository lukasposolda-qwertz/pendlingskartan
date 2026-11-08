"""Rail layer for Pendlingskartan v2: stations, segments, kommun travel-time matrix (CSA)."""
import json, os, pickle, collections, re, time, base64
from shapely.geometry import shape, Point
from shapely import STRtree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "build")
t0 = time.time()
P = json.loads(open(os.path.join(ROOT, "data.js"), encoding="utf-8").read()[len("window.PENDLA="):-1])
codes = P["codes"]; N = len(codes)
g = json.load(open(os.path.join(HERE, "raw", "geo.json"), encoding="utf-8"))
gm = {f["properties"]["id"]: shape(f["geometry"]) for f in g["features"]}
polys = [gm[c] for c in codes]
tree = STRtree(polys)

d = pickle.load(open(os.path.join(HERE, "gtfs", "rail.pkl"), "rb"))
routes, trips, st, stops = d["routes"], d["trips"], d["st"], d["stops"]

def clean(n):
    n = re.sub(r"\s+station$", "", n)
    n = n.replace("Centralstation", "C")
    return n

sids = sorted(stops, key=lambda s: stops[s][0])
sidx = {s: i for i, s in enumerate(sids)}
S = len(sids)
skom = []
for s in sids:
    _, lon, lat = stops[s]
    p = Point(lon, lat); k = -1
    for c in tree.query(p):
        if polys[c].contains(p): k = int(c); break
    if k < 0:  # coast stations just outside simplified polygons
        c = tree.nearest(p)
        if polys[c].distance(p) < 0.02: k = int(c)
    skom.append(k)

# stations named after a municipality ("Sundbyberg", "Lund C") belong to it when it is close by
kname = {n.lower(): i for i, n in enumerate(P["names"])}
fixed = 0
for i, s in enumerate(sids):
    nm = re.sub(r"\s+(C|central|centralstation|station)$", "", clean(stops[s][0]), flags=re.I).lower()
    k = kname.get(nm)
    if k is not None and k != skom[i] and polys[k].distance(Point(stops[s][1], stops[s][2])) < 0.05:
        skom[i] = k; fixed += 1
print("name-matched stations moved", fixed)

CATS = ["fast", "long", "reg"]
dep = [[0, 0, 0] for _ in range(S)]; peak = [0] * S
ops = [collections.Counter() for _ in range(S)]
seg = collections.defaultdict(lambda: [0, 0, 0])
conns = []
trip_list = list(st)
pairs = collections.Counter()
for ti, tid in enumerate(trip_list):
    v = sorted(st[tid]); cat, agency, _ = routes[trips[tid]]; ci = CATS.index(cat)
    for a, b in zip(v, v[1:]):
        ia, ib = sidx[a[1]], sidx[b[1]]
        if ia == ib: continue
        dep[ia][ci] += 1; ops[ia][agency] += 1
        if 7 * 3600 <= a[3] < 9 * 3600: peak[ia] += 1
        key = (min(ia, ib), max(ia, ib)); seg[key][ci] += 1
        conns.append((a[3], b[2], ia, ib, ti))
    ks = []
    for s in v:
        k = skom[sidx[s[1]]]
        if k >= 0 and (not ks or ks[-1] != k) and k not in ks: ks.append(k)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            pairs[(ks[i], ks[j])] += 1
conns.sort()
print("stations", S, "conns", len(conns), "segments", len(seg), "kpairs", len(pairs), time.time() - t0, flush=True)

# ---- CSA: min door-less travel time kommun -> kommun, morning departures 06:00-08:45 ----
import bisect
cdep = [c[0] for c in conns]
kst = collections.defaultdict(list)
for i, k in enumerate(skom):
    if k >= 0: kst[k].append(i)
TR = 180; WIN = 180 * 60; INF = 10 ** 9
best = [[255] * N for _ in range(N)]
starts = list(range(6 * 3600, 9 * 3600, 15 * 60))
for o in range(N):
    if o not in kst: continue
    best[o][o] = 0
    src = kst[o]
    for t in starts:
        ea = [INF] * S
        for s in src: ea[s] = t - TR  # no transfer penalty at origin
        onb = set()
        i0 = bisect.bisect_left(cdep, t); lim = t + WIN
        for c in conns[i0:]:
            dt, at, a, b, ti = c
            if dt > lim: break
            if ti in onb or ea[a] + TR <= dt:
                onb.add(ti)
                if at < ea[b]: ea[b] = at
        row = best[o]
        for k, ss in kst.items():
            m = min(ea[s] for s in ss)
            if m < INF:
                mins = (m - t) // 60
                if mins < row[k]: row[k] = max(1, min(mins, 254)) if k != o else 0
    if o % 40 == 0: print("csa", o, time.time() - t0, flush=True)

flat = bytes(best[i][j] for i in range(N) for j in range(N))
rail = {
    "day": d["day"],
    "st": [[clean(stops[s][0]), round(stops[s][1], 4), round(stops[s][2], 4), skom[i], dep[i], peak[i],
            [a for a, _ in ops[i].most_common(4)]] for i, s in enumerate(sids)],
    "seg": [[a, b, c[0], c[1], c[2]] for (a, b), c in seg.items()],
    "tt": base64.b64encode(flat).decode(),
    "dir": [x for (a, b), n in pairs.items() for x in (a, b, n)],
}
print("trains/day", len(trip_list), "kommuner med station", len(kst))
json.dump(rail, open(os.path.join(HERE, "gtfs", "rail_partial.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("bytes", os.path.getsize(os.path.join(HERE, "gtfs", "rail_partial.json")), time.time() - t0)
