"""Ward-level wood-waste supply index from street trees (basal area), City green space, and 311 requests."""
import geopandas as gpd, pandas as pd, numpy as np, warnings
from config import *
warnings.filterwarnings("ignore")
UTM = "EPSG:32617"

w = gpd.read_file(RAW / "City_Wards_Data_-_4326.geojson")[["AREA_SHORT_CODE", "AREA_NAME", "geometry"]]
w["ward"] = w["AREA_SHORT_CODE"].str.zfill(2); w = w.rename(columns={"AREA_NAME": "ward_name"}).drop(columns="AREA_SHORT_CODE")
w_utm = w.to_crs(UTM); w["area_km2"] = (w_utm.area / 1e6).values

# --- street trees: basal area (m2) per ward ------------------------------------------------------
tr = gpd.read_file(RAW / "Street_Tree_Data_-_4326.geojson", engine="pyogrio", columns=["WARD", "DBH_TRUNK"])
tr["geometry"] = tr.geometry.centroid
n0 = len(tr)
tr["dbh"] = tr["DBH_TRUNK"].clip(upper=200)                       # 9,380 cm is a data-entry error -> cap at 200 cm
tr["dbh"] = tr.groupby("WARD")["dbh"].transform(lambda s: s.fillna(s.median()))
tr["ba_m2"] = np.pi * (tr["dbh"] / 200) ** 2
tree = tr.groupby("WARD").agg(trees=("ba_m2", "size"), ba_m2=("ba_m2", "sum"), dbh_median=("dbh", "median")).rename_axis("ward")
print(f"street trees: {n0:,} | DBH missing: {tr['DBH_TRUNK'].isna().sum():,} | DBH>200cm capped: {(tr['DBH_TRUNK']>200).sum():,}")

# --- supply-weighted centroid per ward (where the wood actually is) -------------------------------
tr_utm = tr.to_crs(UTM); tr_utm["x"] = tr_utm.geometry.x; tr_utm["y"] = tr_utm.geometry.y
cent = tr_utm.groupby("WARD").apply(lambda d: pd.Series({"cx": np.average(d.x, weights=d.ba_m2), "cy": np.average(d.y, weights=d.ba_m2)}))
cent.index.name = "ward"; cent.to_csv(OUT / "ward_supply_centroids_utm17n.csv")

# --- City-managed green space area per ward --------------------------------------------------------
g = gpd.read_file(WORK / "green_spaces.gpkg").to_crs(UTM)
g["geometry"] = g.geometry.buffer(0)                              # repairs the single invalid polygon
g = g[g["AREA_CLASS"].isin(CITY_GREEN_CLASSES)]
ov = gpd.overlay(g[["AREA_CLASS", "geometry"]], w_utm[["ward", "geometry"]], how="intersection", keep_geom_type=True)
ov["ha"] = ov.area / 1e4
green = ov.groupby("ward")["ha"].sum().rename("green_ha")
park = ov[ov.AREA_CLASS == "Park"].groupby("ward")["ha"].sum().rename("park_ha")

# --- 311 wood-generating requests (full years only) --------------------------------------------------
sr = pd.read_pickle(WORK / "sr_all.pkl")
sr["ward"] = sr["Ward"].str.extract(r"\((\d+)\)")[0]
m = (sr.Division.str.contains("Forestry", na=False) & sr["Section"].eq("Forestry Operations")
     & sr["Service Request Type"].isin(WOOD_311_TYPES) & sr["Creation Date"].dt.year.isin(FULL_YEARS))
req = sr[m].groupby("ward").size().rename("req311_2yr")
print(f"311 wood-generating requests used: {m.sum():,}")

d = w.set_index("ward").join(tree).join(green).join(park).join(req)
d["trees_per_km2"] = d.trees / d.area_km2
# --- which proxy best explains observed 311 demand? leave-one-out R2 ---------------------------------
def loo_r2(X, y):
    X = np.column_stack([np.ones(len(y)), X]); pred = np.zeros(len(y))
    for i in range(len(y)):
        k = np.arange(len(y)) != i; b = np.linalg.lstsq(X[k], y[k], rcond=None)[0]; pred[i] = X[i] @ b
    return 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
y = d.req311_2yr.values.astype(float)
cands = {"tree count": d[["trees"]].values, "street-tree basal area": d[["ba_m2"]].values,
         "green space ha": d[["green_ha"]].values, "BA + green ha": d[["ba_m2", "green_ha"]].values,
         "BA + park ha": d[["ba_m2", "park_ha"]].fillna(0).values}
print("\nProxy comparison vs 311 wood requests (n=25 wards):")
res = {k: loo_r2(v, y) for k, v in cands.items()}
for k, v in res.items(): print(f"  {k:26s} leave-one-out R2 = {v:5.2f}   Pearson r = {np.corrcoef(v_ := (cands[k].sum(axis=1) if cands[k].shape[1]==1 else cands[k][:,0]), y)[0,1]:.2f}")
best = max(res, key=res.get); print("best proxy:", best)

# supply index = share of citywide basal-area-weighted wood generation (robust, unit-free)
d["supply_share_ba"] = d.ba_m2 / d.ba_m2.sum()
d["supply_share_blend"] = (d.ba_m2 / d.ba_m2.sum() + d.green_ha / d.green_ha.sum()) / 2
d["req311_share"] = d.req311_2yr / d.req311_2yr.sum()
d.drop(columns="geometry").round(4).to_csv(OUT / "ward_supply.csv")
d.reset_index().to_file(OUT / "ward_supply.geojson", driver="GeoJSON")
print("\n", d.drop(columns="geometry")[["ward_name", "trees", "ba_m2", "green_ha", "req311_2yr", "supply_share_ba", "supply_share_blend"]].round(3).to_string())
