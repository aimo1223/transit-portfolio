# Notebook 4b Handoff: Network Walk-Shed & Transit Access Gap Analysis

> **Findings update (2026-05-29, post-run).** Notebook 4b is now built and executed across all 875 stops. The detour-factor hypothesis described below did **not** hold for this stop set: network detour-to-stop is modest (median ≈ 1.2, almost none above 1.5), because MARTA stops sit on connected through-roads. The real access barrier here is **coverage** — crow-flies buffers overstate who can actually walk to a stop — not cul-de-sac circuity. The 2–4× "cul-de-sac hell" detours this plan anticipated would require outer-DeKalb stops (Lithonia, Stonecrest, Panola) beyond this study area. Read the detour-centric sections below as the original hypothesis; the notebook's Sections 5 and 12 carry the corrected, coverage-gap framing.

## What this is
This handoff document provides everything needed to build notebook 4b from scratch. It covers the project context, what notebook 4a established, what 4b needs to accomplish, technical decisions already made, data sources with access details, and pitfalls to avoid.

## Project context
This is a transit data analytics portfolio (github.com/aimo1223/transit-portfolio). The author is a data analyst with 4 years of experience who is job hunting and also genuinely passionate about making Atlanta/Decatur more walkable. The portfolio serves dual purpose: demonstrating analytical skills to employers and building an advocacy case for pedestrian infrastructure investment.

The author hates how car-dependent Atlanta is, particularly the dendritic cul-de-sac street layouts that isolate neighborhoods from transit. This notebook should reflect that — frame findings around actionable policy implications, not academic abstractions.

## What notebook 4a established
**File:** `notebooks/04_dekalb_pedestrian_infrastructure.ipynb` (34 cells, complete)

**Study area bounding box (DeKalb County subset):**
```python
BBOX_NORTH, BBOX_SOUTH = 33.82, 33.74
BBOX_EAST, BBOX_WEST = -84.28, -84.38
```

**Key results from 4a:**
- 875 MARTA bus stops scored with two versions of a Pedestrian Access Score (PAS)
  - PAS v1: binary flags (sidewalk yes/no within 50m) — creates bimodal distribution with spike at ~85. Good for infrastructure maps because categorical color transitions reveal where sidewalk coverage drops suddenly along a corridor.
  - PAS v2: continuous components (distance decay, coverage ratios) — better discrimination for ranking stops. Weights: proximity 30%, network coverage 35%, crossings 20%, road-SW coverage 15%.
- 266 stops (30%) scored Poor or No Infrastructure
- Equity finding: Black population share correlates with worse PAS at r = -0.49
- Crash proximity: raw PAS-crash correlation is POSITIVE (better infra = more crashes). After normalizing by population density, the relationship disappears (active-commuter normalized r ≈ -0.01). This is likely because both crashes and infrastructure concentrate on high-traffic corridors, and people don't walk where there's no sidewalk (suppressed demand).
- Two Folium interactive maps saved: `maps/dekalb_pedestrian_access.html` (infrastructure overlay, v1 colors) and `maps/dekalb_stops_v2_scores.html` (stops only, v2 gradient)

**Key outputs you can load in 4b:**
- `data/processed/dekalb_stop_ped_access_scores.csv` — all 875 stops with PAS v1, PAS v2, component scores, crash counts
- `data/processed/dekalb_ped_bike_crashes.csv` — all ped/bike crashes in study area
- `config.env` — contains `CENSUS_API_KEY=08037e8e73eaa2a4962a0af6a2c5318d4ba2836c`
- MARTA GTFS feed at `data/raw/google_transit.zip`

## What notebook 4b needs to do

### Core analysis: Network walk-sheds (this is the centerpiece)
Use OSMnx to download the walkable street network for the study area and compute actual walking isochrones (5-min and 10-min at 5 km/h) for every bus stop. The key metric is the **detour factor**: `network_walking_distance / euclidean_distance`. A detour factor of 1.0 means the street grid is perfectly direct; 3-4x means cul-de-sac hell.

**Implementation notes:**
- OSMnx 2.1+ API: use `ox.graph_from_bbox()` with `network_type='walk'`
- Add travel time to edges: `length / walk_speed` (walk_speed ≈ 83.3 m/min = 5 km/h)
- For isochrones: snap each stop to nearest network node, use `nx.ego_graph()` with `radius=` travel time threshold, extract convex hull or alpha shape of reachable nodes
- Reference: https://github.com/gboeing/osmnx-examples/blob/main/notebooks/13-isolines-isochrones.ipynb
- 875 stops × isochrone computation may be slow — consider computing for a representative subset first, then full run

### Street connectivity metrics
For the 400m buffer around each stop, compute: intersection density, dead-end ratio, average block length, circuity. These quantify dendritic vs. grid layout. OSMnx has `stats.basic_stats()` but you may need to subgraph per stop.

### Population within walk-shed
Overlay walk-shed polygons with Census block-group or block-level population (ACS B01001_001E). This gives "how many people can actually walk to this stop in 5 minutes" — much more meaningful than the crow-flies buffer population from 4a.

### GDOT AADT traffic volumes (if user has collected the data)
The user said they'd collect data for 4b. Check if `data/raw/` has any AADT files. If present, join traffic volumes to road segments near stops for proper crash rate modeling. If not present, note it as a gap and skip gracefully.

### DeKalb SPLOST cross-reference
The user may have collected the SPLOST/CIP project list. If present in `data/raw/`, overlay against identified gaps. If not, build the framework and note where to plug it in.

### Suppressed demand analysis
Compare: population within 5-min walk-shed × transit commuter share (from Census) vs. PAS score. Stops where many people live nearby and commute by transit but have terrible PAS scores are the strongest candidates for suppressed demand.

## Data the user is collecting
The user said "let me collect the data for 4b" before this handoff. Check `data/raw/` for any new files (GDOT AADT, DeKalb project lists, etc.) and incorporate what's available. The OSMnx and Census data can be downloaded programmatically — don't wait for those.

## Technical requirements
```
pip install osmnx>=2.1.0 networkx geopandas folium shapely matplotlib pandas numpy requests
```

## Design preferences (from working with the user)
1. **v1 PAS for infrastructure maps, v2 for analysis** — the user specifically prefers v1 categorical colors on maps that show infrastructure lines, because the sharp transitions match their walking experience. Use v2 for ranking, scoring, and the stops-only map.
2. **No useless charts** — if a visualization has all data points at the same value, replace it with something informative (map, table with context, different metric).
3. **Honest framing** — don't overclaim causal relationships. Frame limitations as advocacy opportunities ("we'd need X data to prove Y") rather than academic hedging.
4. **Advocacy-oriented** — this isn't a school project. Name specific corridors, reference specific funding sources (SPLOST, SS4A grants), and produce outputs that could go into a public comment or city council presentation.
5. **Clean, portfolio-quality code** — employers will review this. Good docstrings, clear variable names, markdown narrative between code cells.

## Notebook structure (draft, 12 sections)
1. Introduction & setup (imports, config, load 4a outputs)
2. Load notebook 4a outputs (stop scores, crash data, Census join)
3. Download & prepare walking network (OSMnx)
4. Compute walk-shed isochrones (5-min, 10-min) for all stops
5. Calculate detour factors and connectivity metrics
6. Population-within-walk-shed analysis (Census block overlay)
7. GDOT AADT data acquisition and join (if data available)
8. Crash rate modeling with traffic volume control (if AADT available)
9. Planned infrastructure cross-reference (if data available)
10. Suppressed demand proxy analysis
11. Interactive maps: walk-sheds, detour factors, gap analysis
12. Findings & advocacy implications

## Expected deliverables
- `notebooks/04b_dekalb_walkshed_analysis.ipynb` — the notebook
- `maps/dekalb_walkshed_detour.html` — interactive Folium map with walk-shed polygons and detour factors
- `data/processed/dekalb_stop_walkshed_metrics.csv` — per-stop walk-shed population, detour factor, connectivity metrics
- `assets/walkshed_*.png` — static chart exports
- Updated `docs/index.html` — change the "Planned" card for 4b to "In Progress" with notebook link

## What NOT to do
- Don't rebuild anything from notebook 4a — load its CSV outputs
- Don't use crow-flies buffers — the whole point of 4b is network distance
- Don't frame findings passively — name the corridors, name the problem, propose the fix
- Don't ignore data the user may have added to data/raw/ — check first
