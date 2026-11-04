"""Build docs/index.html (executive case-study page + interactive simulator). Aggregated data only; no tiles, no libraries."""
import geopandas as gpd, pandas as pd, json, math
from config import *
W, H, LON0, LAT1 = 900, 670, -79.64, 43.865
K = W / ((-79.10 - LON0) * math.cos(math.radians(43.7)))
px = lambda lon, lat: (round((lon - LON0) * math.cos(math.radians(43.7)) * K, 1), round((LAT1 - lat) * K, 1))
g = gpd.read_file(OUT / "ward_supply.geojson"); g["geometry"] = g.geometry.simplify(0.0012)
def path(geom):
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    return "".join("M" + "L".join("%s,%s" % px(x, y) for x, y in p.exterior.coords) + "Z" for p in polys)
M = pd.read_csv(OUT / "ward_station_matrix.csv", dtype={"ward": str}).dropna(subset=["ward"]); st = pd.read_csv(OUT / "stations.csv")
cen = pd.read_csv(OUT / "ward_supply_centroids_utm17n.csv", dtype={"ward": str}, keep_default_na=False).set_index("ward")
cg = gpd.GeoSeries(gpd.points_from_xy(cen.cx, cen.cy), crs="EPSG:32617", index=cen.index).to_crs(4326)
obs = pd.read_csv(OUT / "validation_station_shares.csv").set_index("station").observed_share
sites = list(st.station); km = M.pivot(index="ward", columns="station", values="km")
data = dict(wards=[dict(id=r.ward, name=r.ward_name, share=round(r.supply_share_ba, 4), d=path(r.geometry), c=px(cg[r.ward].x, cg[r.ward].y), km=[round(km.loc[r.ward, s], 1) for s in sites]) for r in g.itertuples()],
  sites=[dict(name=s, x=px(r.lon, r.lat)[0], y=px(r.lon, r.lat)[1], obs=(None if pd.isna(obs.get(s)) else round(float(obs[s]), 3))) for s, r in zip(sites, st.itertuples())],
  DBAU=D_BAU_KM, EF=EF_TKM, CRF=DISC * (1 + DISC) ** LIFE_YR / ((1 + DISC) ** LIFE_YR - 1))
tor = pd.read_csv(OUT / "tornado_breakeven.csv").set_index("parameter").swing; one = json.load(open(OUT / "econ_summary.json")); ss = pd.read_csv(OUT / "siting_single_site.csv")
v = pd.read_csv(OUT / "v1_vs_v2_transport.csv", index_col=0); rf = RETURN_FACTOR
S = {"lo": f"{ss.breakeven_carbon_price.min():.0f}", "hi": f"{ss.breakeven_carbon_price.max():.0f}", "mc5": f"{one['mc_p5_p50_p95'][0]:.0f}", "mc50": f"{one['mc_p5_p50_p95'][1]:.0f}", "mc95": f"{one['mc_p5_p50_p95'][2]:.0f}",
     "swcap": f"{tor['capex']:.0f}", "swpr": f"{tor['price']:.0f}", "swhaul": f"{tor['ctkm']:.0f}", "v2": f"{v.loc['mean tCO2','v2 one-way distances']*rf:.0f}",
     "v2lo": f"{v.loc['P5','v2 one-way distances']*rf:.0f}", "v2hi": f"{v.loc['P95','v2 one-way distances']*rf:.0f}", "v2sh": f"{v.loc['mean tCO2','v2 one-way distances']*rf/4061*100:.1f}", "rf": f"{rf}"}
html = open("page_template.html").read().replace("@@DATA@@", json.dumps(data, separators=(",", ":")))
for k, val in S.items(): html = html.replace(f"@@{k}@@", val)
(ROOT / "docs").mkdir(exist_ok=True); (ROOT / "docs" / "index.html").write_text(html); print("docs/index.html", len(html) // 1024, "KB", S)
