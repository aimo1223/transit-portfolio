# Project: Pedestrian Infrastructure Gap Analysis at MARTA Bus Stops

## Overview

This project analyzes the disconnect between transit stop placement and pedestrian infrastructure in DeKalb County, Georgia — specifically the Decatur, Avondale Estates, and surrounding corridors. The central question: **How many MARTA bus stops lack safe pedestrian access, and who is most affected?**

The project combines transit stop data, sidewalk/cycleway network data, crash records, and demographic data to identify and visualize where infrastructure gaps create unsafe conditions for transit riders.

## Motivation

Many MARTA bus stops — particularly along corridors like Clairmont Rd and N Decatur Rd — sit on roads with no sidewalks, forcing riders to walk in traffic or cross multiple lanes without crosswalks. This is a measurable equity and safety issue: the infrastructure creates dangerous conditions, and crash reports then attribute fault to "jaywalking" pedestrians who had no safe alternative.

## Research Questions

1. **Where are the gaps?** Which MARTA bus stops have no connecting sidewalk infrastructure within a walkable radius?
2. **How dangerous are the gaps?** Do pedestrian/cyclist crashes cluster near stops with poor infrastructure?
3. **Who is affected?** What are the demographic characteristics (income, vehicle ownership, race/ethnicity) of communities served by the most infrastructure-deficient stops?
4. **What's the network story?** How do sidewalk discontinuities (short segments that dead-end) create the illusion of infrastructure without the function?
5. **What does improvement look like?** Using the N Decatur Rd road diet project as a case study, what would the pedestrian level of service look like before vs. after?

## Data Sources

### 1. MARTA GTFS — Bus Stop Locations
- **Source**: MARTA developer resources (itsmarta.com/app-developer-resources.aspx)
- **File**: google_transit.zip → stops.txt
- **Status**: Already downloaded (effective 4/18/2026)
- **Key fields**: stop_id, stop_name, stop_lat, stop_lon, wheelchair_boarding
- **Coverage**: 7,052 stops system-wide; 285 in study area bounding box; 20 along N Decatur Rd
- **Notes**: wheelchair_boarding field has values 0 (no info: 2,846 stops) and 1 (accessible: 4,201 stops). The 40% with no info is itself a data quality finding.
- **Access method**: Direct download, already in project folder

### 2. OpenStreetMap — Sidewalk & Cycleway Network
- **Source**: Overpass API (overpass-api.de)
- **Query types**:
  - Separate sidewalk geometries: `way["highway"="footway"]["footway"="sidewalk"]`
  - Roads with sidewalk tags: `way["highway"]["sidewalk"~"both|left|right|yes"]`
  - Cycleways: `way["highway"="cycleway"]`
  - Crossings: `way["highway"="footway"]["footway"="crossing"]`
- **Status**: Tested successfully — 1,728 ways returned for study area bbox (33.755,-84.32 to 33.795,-84.25)
- **Limitations**: OSM sidewalk coverage is known to be incomplete (footpath.ai research confirms this globally). This is actually an advantage — mapping the gaps between what OSM shows and what exists is part of the story. Can supplement with Mapillary street-level imagery for ground-truthing.
- **Access method**: Overpass API (POST requests); will need to run from local Python, not sandbox

### 3. GDOT Crash Data — Pedestrian & Cyclist Crashes
- **Source**: GDOT Crash Data Dashboard (gdot.aashtowaresafety.net/crash-data-dashboard)
- **Coverage**: Last 5 years of crashes on Georgia public roads
- **Key filters**: Pedestrian involved, bicycle involved, county (DeKalb), crash severity
- **Download**: CSV export available from dashboard's Raw Table tab
- **Status**: Dashboard confirmed accessible; data download requires manual interaction with Numetric UI
- **Backup source**: NHTSA FARS API for fatal crashes (crashviewer.nhtsa.dot.gov/CrashAPI) — supports Georgia (state=13), DeKalb County (county=89), JSON/CSV output. API was down during testing but is documented.
- **DeKalb context**: 43 pedestrian fatalities in 2022 alone — one of Georgia's highest
- **Access method**: Manual CSV download from GDOT dashboard, or FARS API for fatalities only

### 4. Census ACS — Demographics & Equity Overlay
- **Source**: Census Bureau API (api.census.gov)
- **Dataset**: ACS 5-year estimates (most recent available)
- **Geography**: Census tract level, DeKalb County (state=13, county=089)
- **Key tables**:
  - B08201: Household Size by Vehicles Available (zero-car households)
  - B08301: Means of Transportation to Work (transit riders, walkers)
  - B19013: Median Household Income
  - B03002: Hispanic/Latino Origin by Race
  - B01003: Total Population
- **Status**: API requires free API key (api.census.gov/data/key_signup.html) — need to register
- **Access method**: REST API with key; tract-level data for all of DeKalb County

### 5. Supplementary Sources (Lower Priority)

| Source | Data | Access | Notes |
|--------|------|--------|-------|
| DeKalb County Open Data (dekalbinsights-dekalbgis.opendata.arcgis.com) | Parcels, zoning, land use | ArcGIS REST API | Useful for identifying residential vs. commercial context around stops |
| ARC Open Data Hub (opendata.atlantaregional.com) | Regional transit, bike/ped plans | Download | Regional context and planning documents |
| Georgia GIO Data Hub (data-hub.gio.georgia.gov) | Statewide GIS layers | Download (CSV, KML, GeoJSON) | ACS vehicle availability already mapped |
| MARTA GTFS-Realtime | Live bus positions | Protobuf API | Could add ridership proxy (frequency of service) |
| AECOM N Decatur Rd Concept Plans | Road diet design specs | Via Medlock Park Neighborhood Assoc or City of Decatur | Before/after case study framework |

## Study Area

**Primary bounding box**: 33.755°N to 33.795°N, 84.32°W to 84.25°W

This captures the corridor from the Emory University area east through Decatur, Avondale Estates, and toward Kensington — including N Decatur Rd, Clairmont Rd, E Ponce de Leon Ave, and connecting residential streets.

**Key corridors of interest**:
- N Decatur Rd (planned road diet corridor — excellent before/after case study)
- Clairmont Rd (bus stops in front yards, no sidewalks)
- E Ponce de Leon Ave (connects Decatur to Avondale, mixed infrastructure)
- Scott Blvd / Church St intersection (multi-arterial convergence, fragmented bike lanes)

## Methodology

### Phase 1: Data Acquisition & Cleaning
- Download/query all data sources
- Standardize coordinate systems (WGS84)
- Build unified GeoDataFrame of stops with attributes

### Phase 2: Sidewalk Connectivity Analysis
- For each MARTA stop, query OSM for sidewalk/footway segments within 400m (5-min walk)
- Calculate a **Pedestrian Access Score** based on:
  - Presence of any sidewalk connecting to the stop
  - Length of continuous sidewalk network reachable
  - Presence of marked crossings at nearby intersections
  - Whether the road the stop is on has a sidewalk tag
- Identify **infrastructure discontinuities**: short sidewalk segments (<200m) that don't connect to the broader network

### Phase 3: Safety Overlay
- Geocode pedestrian/cyclist crash locations
- Calculate crash density within buffer zones around stops
- Correlate crash frequency with Pedestrian Access Score
- Identify highest-risk stops (low access score + high crash density)

### Phase 4: Equity Analysis
- Join stop locations to Census tracts
- Compare Pedestrian Access Scores across demographic groups
- Test whether low-income / zero-car / majority-minority tracts have worse pedestrian infrastructure at their transit stops
- Visualize disparities

### Phase 5: Case Study — N Decatur Rd
- Map current pedestrian infrastructure along the corridor
- Overlay planned road diet improvements (from AECOM concept)
- Model how the Pedestrian Access Score would change for each stop post-improvement

## Expected Outputs

- Interactive Folium map showing all MARTA stops in study area, colored by Pedestrian Access Score, with crash data overlay
- Statistical analysis of equity disparities in pedestrian infrastructure
- Corridor-level visualization of N Decatur Rd before/after
- Charts: Pedestrian Access Score distribution, crash proximity analysis, demographic correlations
- Exported datasets (CSV) for reproducibility

## Technical Stack

- Python (Jupyter Notebook)
- pandas, geopandas, shapely (spatial analysis)
- osmnx or direct Overpass API (street network)
- folium (interactive maps)
- matplotlib/seaborn (static charts)
- Census API (demographics)
- requests (API calls)

## Action Items Before Starting

1. Register for Census API key at api.census.gov/data/key_signup.html
2. Download GDOT crash data CSV from Numetric dashboard (filter: DeKalb County, pedestrian/bicycle, last 5 years)
3. Decide on study area scope — current bbox or expand to all of DeKalb County?
4. Ground-truth a few stops on Clairmont Rd with Google Street View to calibrate OSM completeness expectations
