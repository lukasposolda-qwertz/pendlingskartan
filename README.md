# Pendlingskartan

Where do people live, and where do they work? Pendlingskartan maps how many people commute between Sweden's 290 municipalities, year by year from 2004 to 2024, and where the trains run today.

**Live site:** https://lukasposolda-qwertz.github.io/pendlingskartan/ (Swedish and English)

The map draws on two independent sources:

- **Commuting** from Statistics Sweden (SCB) counts everyone who lives in one municipality and works in another, by any mode of travel.
- **Rail supply** comes from the national GTFS timetable. It covers which trains run and how long the trip takes between municipalities.

When the two are placed side by side, they show where large commuter flows have a fast rail connection and where they do not. The map does **not** show how many people take the train, because neither source records that.

## What is in the repository

| Path | Content |
|---|---|
| `index.html` | The whole site: one page with D3 and TopoJSON, and no build step |
| `data.js` | Commuting matrices 2004–2024 and simplified municipal boundaries (TopoJSON) |
| `rail.js` | Stations, train counts, the travel-time matrix between municipalities, and the simplified rail network |
| `scripts/` | Python scripts that rebuild `data.js` and `rail.js` from the open sources |

## Rebuilding the data

You need Python 3.11+ with `shapely` (2.x), `topojson` and `numpy`. Intermediate files go to `build/`, which is not committed.

1. **Commuting.** Run `python scripts/fetch.py`. It downloads SCB tables TAB333 (2004–2018), TAB5850 (2019) and TAB1830 (2020–2024) through PxWebApi v2.
2. **Boundaries.** Save `swedish_municipalities.geojson` from [okfse/sweden-geojson](https://github.com/okfse/sweden-geojson) as `build/raw/geo.json`.
3. **Build the commuting data.** Run `python scripts/process.py`. It writes `data.js`.
4. **Timetable.** Download GTFS Sverige 2 from [Trafiklab](https://www.trafiklab.se/api/gtfs-datasets/gtfs-sverige-2/) or its [Mobility Database mirror](https://mobilitydatabase.org/feeds/gtfs/mdb-2661). Unzip it into `build/gtfs/feed/`.
5. **Pick a day.** Set `DAY` in `scripts/gtfs_process.py` to a regular weekday in the feed, then run the script.
6. **Travel times.** Run `python scripts/rail_build.py`. It assigns stations to municipalities and runs the connection scan.
7. **Rail network.** Save the OpenStreetMap rail lines as `build/gtfs/osm_rail.json`, for example with this Overpass query:
   ```
   [out:json][timeout:300];
   way["railway"="rail"]["usage"~"^(main|branch)$"][!"service"](55.2,10.9,69.1,24.2);
   out geom;
   ```
   Then run `python scripts/osm_build.py`. It writes `rail.js`.

## Method in brief

- **Commuting regions.** Each municipality joins the region of the municipality most of its out-commuters go to, as long as that share reaches a threshold (10 % by default).
- **Train time.** This is the fastest timetable journey between any station in one municipality and any station in the other. Departures are 06:00–08:45 on a regular Tuesday, transfers need at least 3 minutes, and up to 15 minutes of waiting is included. Metro and tram are excluded, and so is access time to and from the station.

The About page on the site has the full definitions and caveats.

## Licences

- **Code:** [MIT](LICENSE).
- **Processed data** in `data.js` and `rail.js`: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Credit "Lukas Posolda, Pendlingskartan".
- **The rail network geometry** in `rail.js` is derived from OpenStreetMap and is available under the [ODbL 1.0](https://opendatacommons.org/licenses/odbl/). © OpenStreetMap contributors.

| Source | Licence |
|---|---|
| Statistics Sweden (SCB), tables TAB333, TAB5850, TAB1830 | CC0 1.0 |
| Trafiklab GTFS Sverige 2 (Samtrafiken), via the Mobility Database | CC0 1.0 |
| OpenStreetMap | ODbL 1.0 |
| okfse/sweden-geojson (based on Swedish Election Authority data) | free to reuse |
| D3, TopoJSON client | ISC |
| IBM Plex Sans, IBM Plex Mono (Google Fonts) | SIL OFL 1.1 |

The figures are my own processing of these sources. They are not official statistics. The project has no partnership with Statistics Sweden, Trafiklab or any other organisation.

## Author

Made by [Lukas Posolda](https://github.com/lukasposolda-qwertz). This is a personal project. If you find an error, please open an issue.

**How to cite:** Posolda, L. (2026). *Pendlingskartan: commuting and rail in Sweden's municipalities.* https://lukasposolda-qwertz.github.io/pendlingskartan/
