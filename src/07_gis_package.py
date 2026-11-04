"""GIS package for ArcGIS Pro: one GeoPackage (EPSG:26917) + a matplotlib preview of the target map."""
import geopandas as gpd, pandas as pd, numpy as np, networkx as nx, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, warnings
from matplotlib.patches import Patch
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge
from scipy.spatial import cKDTree
from config import *
warnings.filterwarnings("ignore")
CRS = "EPSG:26917"; UTM = "EPSG:32617"; GPK = OUT / "arcgis_package.gpkg"
if GPK.exists(): GPK.unlink()

wards = gpd.read_file(OUT / "ward_supply.geojson").to_crs(CRS)
wards["supply_pct"] = (wards.supply_share_ba * 100).round(2)
wards["class5"] = pd.qcut(wards.supply_share_ba, 5, labels=False) + 1
brks = pd.qcut(wards.supply_share_ba, 5, retbins=True)[1] * 100
cols = ["ward", "ward_name", "trees", "ba_m2", "green_ha", "req311_2yr", "supply_pct", "class5", "area_km2"]
wards[cols + ["geometry"]].to_file(GPK, layer="wards_supply", driver="GPKG")

st = pd.read_csv(OUT / "stations.csv"); single = pd.read_csv(OUT / "siting_single_site.csv").set_index("site")
obs = pd.read_csv(OUT / "validation_station_shares.csv").set_index("station").observed_share
sg = gpd.GeoDataFrame(st[["station"]], geometry=gpd.points_from_xy(st.lon, st.lat), crs=4326).to_crs(CRS)
sg["mean_haul_km"] = sg.station.map(single.mean_haul_km); sg["breakeven_usd_per_tco2e"] = sg.station.map(single.breakeven_carbon_price)
sg["obs_share_2023"] = sg.station.map(obs).round(3); sg["rank_by_haul"] = sg.mean_haul_km.rank().astype(int)
sg.to_file(GPK, layer="transfer_stations", driver="GPKG")

# context layers
g = gpd.read_file(WORK / "green_spaces.gpkg"); g["geometry"] = g.geometry.buffer(0)
g = g[g.AREA_CLASS.isin(CITY_GREEN_CLASSES)].to_crs(CRS); g["geometry"] = g.geometry.simplify(5)
g[["AREA_CLASS", "AREA_NAME", "geometry"]].to_file(GPK, layer="green_spaces_city", driver="GPKG")
c = gpd.read_file(RAW / "Centreline_-_Version_2_-_4326.geojson", engine="pyogrio",
                  columns=["FROM_INTERSECTION_ID", "TO_INTERSECTION_ID", "FEATURE_CODE_DESC", "ONEWAY_DIR_CODE_DESC"]).to_crs(CRS)
c[c.FEATURE_CODE_DESC.isin(["Expressway", "Major Arterial", "Minor Arterial"])][["FEATURE_CODE_DESC", "geometry"]].to_file(GPK, layer="roads_arterial", driver="GPKG")

# --- real road routes ward-supply-centroid -> best site, with network geometry ---------------------------------------------------
c = c[c.FEATURE_CODE_DESC.isin(SPEED_KPH)].dropna(subset=["FROM_INTERSECTION_ID", "TO_INTERSECTION_ID"])
def ends(g_): 
    return (g_.geoms[0].coords[0], g_.geoms[-1].coords[-1]) if isinstance(g_, MultiLineString) else (g_.coords[0], g_.coords[-1])
def rev(g_):
    m = linemerge(g_) if isinstance(g_, MultiLineString) else g_
    return LineString(list(m.coords)[::-1]) if m.geom_type == "LineString" else g_
G = nx.DiGraph(); xy = {}
for r in c.itertuples():
    a, b = int(r.FROM_INTERSECTION_ID), int(r.TO_INTERSECTION_ID)
    if a == b: continue
    p0, p1 = ends(r.geometry); xy.setdefault(a, p0); xy.setdefault(b, p1)
    L = r.geometry.length; t = L / 1000 / SPEED_KPH[r.FEATURE_CODE_DESC] * 60; ow = r.ONEWAY_DIR_CODE_DESC
    if ow != "Against-Digitization" and (not G.has_edge(a, b) or G[a][b]["time"] > t): G.add_edge(a, b, time=t, geom=r.geometry)
    if ow != "Follow-Digitization" and (not G.has_edge(b, a) or G[b][a]["time"] > t): G.add_edge(b, a, time=t, geom=rev(r.geometry))
G = G.subgraph(max(nx.strongly_connected_components(G), key=len)).copy()
nodes = np.array(list(G.nodes)); tree = cKDTree(np.array([xy[n] for n in nodes]))
best = single.mean_haul_km.idxmin()
s_xy = sg[sg.station == best].geometry.iloc[0]; s_node = nodes[tree.query([s_xy.x, s_xy.y])[1]]
cen = pd.read_csv(OUT / "ward_supply_centroids_utm17n.csv", dtype={"ward": str}).dropna(subset=["ward"])
cen_g = gpd.GeoDataFrame(cen, geometry=gpd.points_from_xy(cen.cx, cen.cy), crs=UTM).to_crs(CRS)
Gr = G.reverse(copy=False); dist, path = nx.single_source_dijkstra(Gr, s_node, weight="time"); rows = []
for r in cen_g.itertuples():
    n = nodes[tree.query([r.geometry.x, r.geometry.y])[1]]; p = path[n][::-1]; parts = []
    for a, b in zip(p[:-1], p[1:]):
        gm = G[a][b]["geom"]; gm = linemerge(gm) if isinstance(gm, MultiLineString) else gm
        parts += list(gm.coords) if gm.geom_type == "LineString" else [xy[a], xy[b]]
    rows.append(dict(ward=r.ward, to_station=best, minutes=round(dist[n], 1), supply_pct=float(wards.set_index("ward").loc[r.ward, "supply_pct"]), geometry=LineString(parts)))
routes = gpd.GeoDataFrame(rows, crs=CRS); routes["km"] = (routes.length / 1000).round(1)
routes.to_file(GPK, layer=f"routes_to_{best.lower().replace(' ', '_')}", driver="GPKG")
cen_g[["ward", "geometry"]].to_file(GPK, layer="ward_supply_centroids", driver="GPKG")
print("layers:", gpd.list_layers(GPK).name.tolist()); print("class breaks (% of citywide supply):", np.round(brks, 2).tolist()); print("best site:", best, "| routes km median %.1f max %.1f" % (routes.km.median(), routes.km.max()))

# --- preview map (target look for ArcGIS Pro layout) --------------------------------------------------------------------------------
ramp = ["#edf8e9", "#bae4b3", "#74c476", "#31a354", "#006d2c"]
fig, ax = plt.subplots(figsize=(11, 7.6)); ax.set_facecolor("#e9f1f6")
wards.plot(ax=ax, color=[ramp[i - 1] for i in wards.class5], edgecolor="white", linewidth=.8)
g.plot(ax=ax, color="#9ccc9c", alpha=.35, linewidth=0)
gpd.read_file(GPK, layer="roads_arterial").plot(ax=ax, color="#8a8f8c", linewidth=.35, alpha=.7)
routes.plot(ax=ax, color="#d9822b", linewidth=0.8 + routes.supply_pct * 0.5, alpha=.85)
sg.plot(ax=ax, markersize=95, color="#ffffff", edgecolor="#1d2420", linewidth=1.6, zorder=5)
for r in sg.itertuples(): ax.annotate(r.station, (r.geometry.x, r.geometry.y), xytext=(7, 6), textcoords="offset points", fontsize=8, weight="bold", zorder=6)
bx = sg[sg.station == best]; bx.plot(ax=ax, markersize=210, color="#d9822b", edgecolor="#1d2420", linewidth=2, zorder=7)
ax.set_axis_off(); ax.set_title("Toronto urban wood waste: supply and best biochar site (%s)" % best, fontsize=13, weight="bold", loc="left")
leg = [Patch(color=ramp[i], label=f"{brks[i]:.1f} - {brks[i+1]:.1f} %") for i in range(5)]
ax.legend(handles=leg, title="Ward share of supply\n(street-tree basal area)", loc="lower left", fontsize=8, title_fontsize=8, frameon=True)
ax.text(.995, .012, "Routes: shortest drive time to %s, width = ward supply share\nSources: City of Toronto Open Data; analysis Y. Zhou. Speeds assumed by road class.\nNAD83 / UTM zone 17N" % best, transform=ax.transAxes, ha="right", va="bottom", fontsize=7, color="#444")
fig.tight_layout(); fig.savefig(OUT / "fig_map_preview.png", dpi=170)
