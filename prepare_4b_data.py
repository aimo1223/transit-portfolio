"""
prepare_4b_data.py — fetch the external datasets that notebook 04b needs.

Notebook 04b's analysis sandbox cannot reach OpenStreetMap or the Census API,
so the two data sources that must come from the network are fetched here, once,
on a machine with internet access. Everything else (detour factors, isochrones,
connectivity metrics, overlays) the notebook computes itself from these files
plus the notebook 4a outputs already in data/processed/.

Usage (from the repo root):
    pip install "osmnx>=2.0" pygris requests geopandas pandas
    python prepare_4b_data.py

Produces, into data/raw/:
    dekalb_walk_network.graphml      OSM walkable street network for the study bbox
    dekalb_blockgroups_pop.geojson   ACS 2022 5-yr block-group total population
    dekalb_tracts_commute.geojson    ACS 2022 5-yr tract commute-to-work mode

The Census key is read from config.env so it is never hard-coded here.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# Study-area bounding box (DeKalb County subset) — must match the notebook.
BBOX_NORTH, BBOX_SOUTH = 33.83, 33.71
BBOX_EAST,  BBOX_WEST  = -84.23, -84.36
STATE = "13"                 # Georgia
COUNTIES = ["089", "121"]    # DeKalb + Fulton (the bbox straddles the county line)
ACS_YEAR = 2022              # ACS 5-year, 2018-2022


def read_census_key(path=ROOT / "config.env"):
    for line in Path(path).read_text().splitlines():
        if line.strip().startswith("CENSUS_API_KEY"):
            return line.split("=", 1)[1].strip()
    raise SystemExit("CENSUS_API_KEY not found in config.env")


def build_network():
    """Download the walkable street network for the study bbox and save as GraphML."""
    import osmnx as ox
    out = RAW / "dekalb_walk_network.graphml"
    # OSMnx 2.x expects bbox as (left, bottom, right, top) = (west, south, east, north)
    bbox = (BBOX_WEST, BBOX_SOUTH, BBOX_EAST, BBOX_NORTH)
    print(f"[1/3] Downloading OSM walk network for bbox {bbox} (this can take 1-3 min)...")
    G = ox.graph_from_bbox(bbox, network_type="walk")
    ox.save_graphml(G, out)
    print(f"      saved {out.name}: {len(G.nodes):,} nodes, {len(G.edges):,} edges")


def fetch_census():
    """Pull ACS block-group population and tract commute mode, save as GeoJSON."""
    import requests
    import geopandas as gpd
    import pygris
    key = read_census_key()

    def acs(geo, county, variables):
        params = {
            "get": "NAME," + ",".join(variables),
            "for": f"{geo}:*",
            "in": f"state:{STATE} county:{county}",
            "key": key,
        }
        r = requests.get(f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5",
                         params=params, timeout=60)
        r.raise_for_status()
        rows = r.json()
        return pd.DataFrame(rows[1:], columns=rows[0])

    # ---- block-group total population: B01001_001E ----
    print("[2/3] Fetching block-group geometry + population...")
    bg_pieces = [pygris.block_groups(state=STATE, county=c, year=ACS_YEAR, cb=True)
                 for c in COUNTIES]
    bg_geom = gpd.GeoDataFrame(pd.concat(bg_pieces, ignore_index=True),
                               geometry="geometry", crs=bg_pieces[0].crs)
    bg_pop = pd.concat([acs("block group", c, ["B01001_001E"]) for c in COUNTIES],
                       ignore_index=True)
    bg_pop["GEOID"] = (bg_pop["state"] + bg_pop["county"]
                       + bg_pop["tract"] + bg_pop["block group"])
    bg_pop["pop_total"] = pd.to_numeric(bg_pop["B01001_001E"], errors="coerce")
    bg = bg_geom.merge(bg_pop[["GEOID", "pop_total"]], on="GEOID", how="left")
    bg.to_file(RAW / "dekalb_blockgroups_pop.geojson", driver="GeoJSON")
    print(f"      saved dekalb_blockgroups_pop.geojson: {len(bg):,} block groups")

    # ---- tract commute-to-work mode: B08301_001E (total), B08301_010E (transit) ----
    print("[3/3] Fetching tract geometry + commute mode...")
    tr_pieces = [pygris.tracts(state=STATE, county=c, year=ACS_YEAR, cb=True)
                 for c in COUNTIES]
    tr_geom = gpd.GeoDataFrame(pd.concat(tr_pieces, ignore_index=True),
                               geometry="geometry", crs=tr_pieces[0].crs)
    tr_com = pd.concat([acs("tract", c, ["B08301_001E", "B08301_010E"]) for c in COUNTIES],
                       ignore_index=True)
    tr_com["GEOID"] = tr_com["state"] + tr_com["county"] + tr_com["tract"]
    tr_com["commute_total"] = pd.to_numeric(tr_com["B08301_001E"], errors="coerce")
    tr_com["commute_transit"] = pd.to_numeric(tr_com["B08301_010E"], errors="coerce")
    tr = tr_geom.merge(tr_com[["GEOID", "commute_total", "commute_transit"]],
                       on="GEOID", how="left")
    tr.to_file(RAW / "dekalb_tracts_commute.geojson", driver="GeoJSON")
    print(f"      saved dekalb_tracts_commute.geojson: {len(tr):,} tracts")


if __name__ == "__main__":
    build_network()
    fetch_census()
    print("\nDone. All three files are in data/raw/ — notebook 04b will pick them up.")
