"""Build docs/index.html: self-contained interactive map + techno-economic calculator (aggregated data only, no tiles, no libraries)."""
import geopandas as gpd, pandas as pd, json, math
from config import *
W, H, LON0, LAT0, LAT1 = 900, 670, -79.64, 43.57, 43.865
K = W / ((-79.10 - LON0) * math.cos(math.radians(43.7)))
px = lambda lon, lat: (round((lon - LON0) * math.cos(math.radians(43.7)) * K, 1), round((LAT1 - lat) * K, 1))
g = gpd.read_file(OUT / "ward_supply.geojson"); g["geometry"] = g.geometry.simplify(0.0012)
def path(geom):
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    return "".join("M" + "L".join("%s,%s" % px(x, y) for x, y in p.exterior.coords) + "Z" for p in polys)
M = pd.read_csv(OUT / "ward_station_matrix.csv", dtype={"ward": str}); st = pd.read_csv(OUT / "stations.csv")
obs = pd.read_csv(OUT / "validation_station_shares.csv").set_index("station").observed_share
sites = list(st.station)
km = M.pivot(index="ward", columns="station", values="km")
data = dict(
  wards=[dict(id=r.ward, name=r.ward_name, share=round(r.supply_share_ba, 4), d=path(r.geometry), km=[round(km.loc[r.ward, s], 1) for s in sites]) for r in g.itertuples()],
  sites=[dict(name=s, x=px(r.lon, r.lat)[0], y=px(r.lon, r.lat)[1], obs=(None if pd.isna(obs.get(s)) else round(float(obs[s]), 3))) for s, r in zip(sites, st.itertuples())],
  W=W, H=H, DBAU=D_BAU_KM, EF=EF_TKM, CRF=DISC * (1 + DISC) ** LIFE_YR / ((1 + DISC) ** LIFE_YR - 1))
html = open("page_template.html").read().replace("__DATA__", json.dumps(data, separators=(",", ":")))
(ROOT / "docs").mkdir(exist_ok=True); (ROOT / "docs" / "index.html").write_text(html); print("docs/index.html", len(html) // 1024, "KB")
