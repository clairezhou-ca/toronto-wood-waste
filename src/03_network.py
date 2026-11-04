"""Road network from Toronto Centreline -> ward-supply-centroid to transfer-station travel distance/time."""
import geopandas as gpd, pandas as pd, numpy as np, networkx as nx, warnings
from scipy.spatial import cKDTree
from shapely.geometry import MultiLineString
from config import *
warnings.filterwarnings("ignore")
UTM = "EPSG:32617"

c = gpd.read_file(RAW / "Centreline_-_Version_2_-_4326.geojson", engine="pyogrio",
                  columns=["FROM_INTERSECTION_ID", "TO_INTERSECTION_ID", "FEATURE_CODE_DESC", "ONEWAY_DIR_CODE_DESC", "LINEAR_NAME_FULL"]).to_crs(UTM)
c = c[c.FEATURE_CODE_DESC.isin(SPEED_KPH)].copy()
c = c.dropna(subset=["FROM_INTERSECTION_ID", "TO_INTERSECTION_ID"])
print("road segments used:", len(c), "of which expressway/ramp:", c.FEATURE_CODE_DESC.str.contains("Expressway").sum())

def endpoints(g):
    if isinstance(g, MultiLineString):
        return g.geoms[0].coords[0], g.geoms[-1].coords[-1]
    return g.coords[0], g.coords[-1]

G = nx.DiGraph(); xy = {}
for r in c.itertuples():
    a, b = int(r.FROM_INTERSECTION_ID), int(r.TO_INTERSECTION_ID)
    if a == b: continue
    p0, p1 = endpoints(r.geometry); xy.setdefault(a, p0); xy.setdefault(b, p1)
    L = r.geometry.length; t = L / 1000 / SPEED_KPH[r.FEATURE_CODE_DESC] * 60      # minutes
    kw = dict(length=L, time=t, cls=r.FEATURE_CODE_DESC)
    ow = r.ONEWAY_DIR_CODE_DESC
    if ow != "Against-Digitization":
        if not G.has_edge(a, b) or G[a][b]["time"] > t: G.add_edge(a, b, **kw)
    if ow != "Follow-Digitization":
        if not G.has_edge(b, a) or G[b][a]["time"] > t: G.add_edge(b, a, **kw)
scc = max(nx.strongly_connected_components(G), key=len)
print(f"graph: {G.number_of_nodes():,} nodes / {G.number_of_edges():,} edges | largest strongly-connected comp: {len(scc):,} nodes ({len(scc)/G.number_of_nodes()*100:.1f}%)")
G = G.subgraph(scc).copy()
nodes = np.array(list(G.nodes)); coords = np.array([xy[n] for n in nodes]); tree = cKDTree(coords)

# --- stations ---------------------------------------------------------------------------------------
st = gpd.read_file(WORK / "transfer-stations-wgs84-jan-2012" / "SW_transfer_station_wgs84.shp").to_crs(UTM)
st["station"] = st["Name"].map(lambda n: next(v for k, v in STATION_KEYS.items() if k in n))
d, i = tree.query(np.column_stack([st.geometry.x, st.geometry.y])); st["node"] = nodes[i]; st["snap_m"] = d
print("station snap distances (m):", dict(zip(st.station, d.round(0))))

# --- ward supply centroids ----------------------------------------------------------------------------
cen = pd.read_csv(OUT / "ward_supply_centroids_utm17n.csv", dtype={"ward": str})
d, i = tree.query(cen[["cx", "cy"]].values); cen["node"] = nodes[i]; cen["snap_m"] = d
print("ward centroid snap distances (m): median %.0f, max %.0f" % (np.median(d), d.max()))

# --- shortest-time routes ward -> station (reverse graph, one Dijkstra per station) ------------------------
Gr = G.reverse(copy=False); rows = []
for s in st.itertuples():
    dist, path = nx.single_source_dijkstra(Gr, s.node, weight="time")
    for w in cen.itertuples():
        p = path[w.node][::-1]                                      # ward -> station order
        km = sum(G[a][b]["length"] for a, b in zip(p[:-1], p[1:])) / 1000
        rows.append(dict(ward=w.ward, station=s.station, km=km, minutes=dist[w.node],
                         exp_share=sum(G[a][b]["length"] for a, b in zip(p[:-1], p[1:]) if G[a][b]["cls"].startswith("Expressway")) / 1000 / max(km, 1e-9)))
M = pd.DataFrame(rows); M.to_csv(OUT / "ward_station_matrix.csv", index=False)
st.drop(columns="geometry").assign(lon=st.to_crs(4326).geometry.x, lat=st.to_crs(4326).geometry.y).to_csv(OUT / "stations.csv", index=False)
print("\nward->station km: median %.1f, min %.1f, max %.1f | minutes median %.1f" % (M.km.median(), M.km.min(), M.km.max(), M.minutes.median()))
print("circuity check (network km / straight-line km), median:",
      round(float(np.median([r.km * 1000 / max(np.hypot(*(cen.set_index('ward').loc[r.ward, ['cx','cy']].values - st.set_index('station').loc[r.station].geometry.coords[0])), 1) for r in M.itertuples()])), 2))
