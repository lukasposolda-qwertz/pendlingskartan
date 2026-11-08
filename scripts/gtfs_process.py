"""GTFS Sverige 2 -> rail stations, segments, connections for one weekday."""
import csv, json, os, collections, pickle, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.join(ROOT, "build")
FEED = os.path.join(HERE, "gtfs", "feed")
DAY = "20261117"  # tisdag
RAIL = {101: "fast", 102: "long", 106: "reg"}
t0 = time.time()

def rd(name):
    return csv.DictReader(open(os.path.join(FEED, name), encoding="utf-8", newline=""))

agency = {r["agency_id"]: r["agency_name"] for r in rd("agency.txt")}
routes = {}
for r in rd("routes.txt"):
    t = int(r["route_type"])
    if t in RAIL:
        routes[r["route_id"]] = (RAIL[t], agency.get(r["agency_id"], "?"), r["route_short_name"] or r["route_long_name"])
active = set()
for r in rd("calendar_dates.txt"):
    if r["date"] == DAY and r["exception_type"] == "1":
        active.add(r["service_id"])
trips = {}
for r in rd("trips.txt"):
    if r["route_id"] in routes and r["service_id"] in active:
        trips[r["trip_id"]] = r["route_id"]
print("rail routes", len(routes), "active trips", len(trips), time.time() - t0, flush=True)

def sec(s):
    h, m, x = s.split(":"); return int(h) * 3600 + int(m) * 60 + int(x)

st = collections.defaultdict(list)
with open(os.path.join(FEED, "stop_times.txt"), encoding="utf-8", newline="") as f:
    rdr = csv.reader(f); hdr = next(rdr)
    it, ia, idp, isd, isq = (hdr.index(k) for k in ("trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"))
    ipu = hdr.index("pickup_type"); ido = hdr.index("drop_off_type")
    for row in rdr:
        tid = row[it]
        if tid in trips:
            st[tid].append((int(row[isq]), row[isd], sec(row[ia]), sec(row[idp]), row[ipu], row[ido]))
print("stop_times read", sum(map(len, st.values())), time.time() - t0, flush=True)

used = set(s[1] for v in st.values() for s in v)
stops = {}
for r in rd("stops.txt"):
    if r["stop_id"] in used:
        stops[r["stop_id"]] = (r["stop_name"], float(r["stop_lon"]), float(r["stop_lat"]))
print("stations", len(stops))
pickle.dump({"routes": routes, "trips": trips, "st": dict(st), "stops": stops, "day": DAY},
            open(os.path.join(HERE, "gtfs", "rail.pkl"), "wb"))
print("done", time.time() - t0)
