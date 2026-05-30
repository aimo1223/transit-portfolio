# Project Scope: Network Walk-Shed & Transit Access Gap Analysis
## Notebook 4b — DeKalb County, GA

### Objective
Extend the pedestrian infrastructure gap analysis (notebook 4) by measuring **actual walking 
distances** along the street network to MARTA bus stops, replacing the crow-flies buffers 
used in 4a. Quantify how dendritic street layouts (cul-de-sacs, dead ends, missing 
cut-throughs) inflate real walking distances and isolate neighborhoods from transit.

---

> **Findings update (2026-05-29).** After the full run across all 875 stops, detour-to-stop proved a *modest* barrier (median ≈ 1.2; few stops above 1.5) — MARTA stops sit on connected through-roads, so the grid near them is fairly direct. The sharper signal is **coverage**: the real network walk-shed reaches far fewer people than the crow-flies circle implies (see the walk-shed population work in Core Analysis 1). The dendritic 2–4× detours anticipated below live in outer-DeKalb sprawl not represented in this stop set. The sections below remain the original plan of record.

### Core Analyses

#### 1. Network Walk-Shed Isochrones (OSMnx)
**What:** For each MARTA bus stop in the study area, compute the 5-minute and 10-minute 
walking isochrones along the actual street network (assuming 5 km/h walk speed).

**Why:** A stop 200m away as the crow flies may be 800m+ by foot in a cul-de-sac 
neighborhood. The ratio of network distance to Euclidean distance (the "detour factor") 
directly quantifies how street layout affects transit access.

**Tool:** [OSMnx](https://osmnx.readthedocs.io/) v2.1 — download walkable network via 
`ox.graph_from_place()` or `ox.graph_from_bbox()`, compute travel times on edges, generate 
isochrones via NetworkX's `ego_graph()`.

**Key outputs:**
- Walk-shed polygons (5-min, 10-min) for every stop
- Detour factor per stop: `network_distance / euclidean_distance` to nearest stop
- Population within 5-min walk-shed (overlay with Census block-level pop)
- Interactive Folium map: walk-sheds colored by detour factor, worst-connected stops highlighted

**Reference code:** [gboeing/osmnx-examples notebook 13](https://github.com/gboeing/osmnx-examples/blob/main/notebooks/13-isolines-isochrones.ipynb)

#### 2. Street Connectivity Analysis
**What:** Compute network-level metrics for the area around each stop — intersection 
density, average block length, dead-end ratio, and circuity (ratio of actual edge lengths 
to straight-line distance between their endpoints).

**Why:** These metrics quantify the "dendritic vs. grid" spectrum. Stops surrounded by 
cul-de-sacs will have high circuity, low intersection density, and high dead-end ratios. 
This turns "this neighborhood is unwalkable" from a subjective claim into a measurable fact.

**Tool:** OSMnx's `stats.basic_stats()` and custom graph analysis.

#### 3. Suppressed Demand Proxy
**What:** Since MARTA APC (Automatic Passenger Counter) stop-level ridership data is not 
publicly downloadable, use proxy measures:
- **Population within walk-shed** vs. **transit commuter share** (from ACS) — stops where 
  many people live nearby but few commute by transit may indicate suppressed demand
- **MARTA Army Bus Stop Census (2020)** — crowdsourced ground-truth on 3,200+ stop 
  amenities, sidewalk presence, and rider behavior. Their finding that **25% of surveyed 
  stops lack any paved sidewalk** provides historical validation of our OSM-based approach. 
  Data is from 2020 and conditions may have changed since (SPLOST sidewalk investments 
  ongoing), so use as directional validation rather than primary data source.

**If APC data becomes available:** Direct test — regress boardings on PAS score, walk-shed 
population, and detour factor. Hypothesis: stops with high detour factors and low PAS have 
suppressed boardings relative to their catchment population.

#### 4. GDOT Traffic Volume Overlay
**What:** Download AADT (Annual Average Daily Traffic) counts from GDOT's traffic data 
portal and join to road segments near bus stops.

**Source:** [GDOT Traffic Data](https://gdottrafficdata.drakewell.com/publicmultinodemap.asp) 
— interactive map with data export. Also available as GIS layers from 
[GDOT public downloads](http://mydocs.dot.ga.gov/info/publicdownloads/).

**Why:** Allows proper crash rate modeling (crashes per vehicle-mile × pedestrian exposure) 
and identifies the most dangerous road crossings near bus stops. Resolves the confound from 
notebook 4a where "Good" infrastructure stops had the highest pop-normalized crash rates 
because they sit on high-traffic corridors.

#### 5. Planned Infrastructure Cross-Reference
**What:** Overlay identified gaps against DeKalb County's planned improvements:
- **SPLOST Transportation Projects** — sidewalk and Complete Streets investments funded by 
  the special purpose local option sales tax
- **DeKalb Sidewalk Mapping System** — interactive tool showing existing sidewalk network 
  and connectivity gaps (recently launched)
- **Safe Streets for All (SS4A) grant** — $1M federal grant for safety action plan
- Completed sidewalks on Flat Shoals Rd, Oxford Rd; planned for Scott Blvd, Medlock Rd, 
  Snapfinger Rd, Kensington Rd

**Source:** [DeKalb SPLOST Transportation](https://www.dekalbcountyga.gov/splost/splost-transportation), 
[Transportation Project List (PDF)](https://www.dekalbcountyga.gov/sites/default/files/TransportationProjectList.pdf)

**Why:** Shows which of the 266 underserved stops from notebook 4a are in the pipeline and 
which are being ignored. Makes the analysis immediately actionable for advocacy.

---

### Data Sources Summary

| Source | Type | Access | Status |
|--------|------|--------|--------|
| OpenStreetMap (via OSMnx) | Walk network graph | Free, API | Ready |
| MARTA GTFS | Stop locations | Free, download | Already have |
| Census ACS (block group) | Pop within walk-sheds | Free, API | Ready |
| MARTA APC ridership | Stop-level boardings | Not public | Need to request |
| MARTA Army Bus Stop Census | Ground-truth amenities (2020) | On request | Historical validation only |
| GDOT AADT traffic volumes | Road segment traffic | Free, download/export | Ready |
| DeKalb SPLOST project list | Planned improvements | Free, PDF | Ready |
| DeKalb Sidewalk Map | Existing sidewalks | Free, web tool | Ready |
| Notebook 4a outputs | PAS scores, crash data | Local | Already have |

### Technical Requirements

```
osmnx>=2.1.0
networkx
geopandas
folium
shapely
matplotlib
pandas
numpy
requests
```

### Notebook Structure (Draft)

1. Introduction & setup
2. Load notebook 4a outputs (stop scores, crash data, Census join)
3. Download & prepare walking network (OSMnx)
4. Compute walk-shed isochrones (5-min, 10-min) for all stops
5. Calculate detour factors and connectivity metrics
6. Population-within-walk-shed analysis (Census block overlay)
7. GDOT AADT data acquisition and join
8. Crash rate modeling with traffic volume control
9. Planned infrastructure cross-reference
10. MARTA Army data validation (if obtained)
11. Interactive maps: walk-sheds, detour factors, gap analysis
12. Findings & advocacy implications

---

### Expected Key Outputs

- **Detour factor map:** Interactive map showing where network distance >> Euclidean 
  distance, highlighting the worst-connected stops
- **Walk-shed gap map:** Residential areas within 400m crow-flies of a stop but >800m 
  by foot — the "transit desert pockets" created by street layout
- **Connectivity scorecard:** Per-stop metrics (intersection density, dead-end ratio, 
  circuity) that quantify the walkability problem
- **Prioritized investment list:** Stops ranked by (low PAS × high detour factor × high 
  catchment population × not in CIP), identifying where sidewalk/path investments would 
  have the most impact

---

*Builds on [Notebook 4a: Pedestrian Infrastructure Gap Analysis](../notebooks/04_dekalb_pedestrian_infrastructure.ipynb)*
