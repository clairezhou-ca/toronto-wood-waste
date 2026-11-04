"""(A) Validate the ward->station assignment against 2023 weigh-scale tonnage.
   (B) Re-run the long-haul transport LCA (v2) and compare with the v1 report."""
import duckdb, numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats
from SALib.sample import sobol as sob_s
from SALib.analyze import sobol as sob_a
import warnings; warnings.filterwarnings("ignore")
from config import *

# ================================ (A) validation ===========================================================
M = pd.read_csv(OUT / "ward_station_matrix.csv", dtype={"ward": str})
S = pd.read_csv(OUT / "ward_supply.csv", dtype={"ward": str}).set_index("ward")
near = M.loc[M.groupby("ward").minutes.idxmin()].set_index("ward")                 # baseline: closest station by drive time
pred = S.join(near[["station", "km", "minutes"]]).groupby("station").supply_share_ba.sum()
con = duckdb.connect(str(DB), read_only=True)
obs = con.execute("select station, net_stn_total from v_station_summary").df().set_index("station").net_stn_total
cmp_ = pd.DataFrame({"predicted_share": pred, "observed_stn": obs}); cmp_["observed_share"] = cmp_.observed_stn / cmp_.observed_stn.sum()
six = cmp_.dropna().copy(); six["predicted_share_6"] = six.predicted_share / six.predicted_share.sum()
r_s = stats.spearmanr(six.predicted_share_6, six.observed_share); r_p = stats.pearsonr(six.predicted_share_6, six.observed_share)
print("== (A) nearest-station model vs 2023 weigh-scale (6 stations with data; Disco has no weigh code) ==")
print(cmp_.round(3).to_string()); print(f"Spearman rho = {r_s.statistic:.2f} (p={r_s.pvalue:.2f}) | Pearson r = {r_p.statistic:.2f} (n=6)")
print("wards per station (nearest by drive time):", near.station.value_counts().to_dict())
cmp_.to_csv(OUT / "validation_station_shares.csv")
fig, ax = plt.subplots(figsize=(5.2, 4.4)); ax.scatter(six.predicted_share_6, six.observed_share, s=60, color="#2c7a4b")
for s_, r_ in six.iterrows(): ax.annotate(s_, (r_.predicted_share_6, r_.observed_share), xytext=(5, 4), textcoords="offset points", fontsize=8)
ax.plot([0, .5], [0, .5], "--", color="grey", lw=1); ax.set_xlabel("Modelled share (nearest-station, basal-area supply)"); ax.set_ylabel("Observed share (2023 weigh scale)")
ax.set_title(f"Station throughput: model vs observed (Spearman {r_s.statistic:.2f}, n=6)", fontsize=9); fig.tight_layout(); fig.savefig(OUT / "fig_validation.png", dpi=160)

# ================================ (B) v1 vs v2 =============================================================
rng = np.random.default_rng(42); N = 10_000
LH = con.execute("select year, site, vendor, m3, dist_km from longhaul_clean").df()
SH = con.execute("select \"Total Distance(km)\" as d from shorthaul_raw").df().d.dropna().values
def lognorm_from_ci(lo, hi, size):
    s = (np.log(hi) - np.log(lo)) / (2 * 1.96); mu = 0.5 * (np.log(lo) + np.log(hi)); return rng.lognormal(mu, s, size)

# --- v1 reproduction (per-trip model x 324.88 trips, as in the report) ---
d_long = rng.choice(LH.dist_km.values, N); d_short = rng.choice(SH, N)
fe_l = lognorm_from_ci(*FE_LONG_L100, N); fe_s = lognorm_from_ci(*FE_SHORT_L100, N); p = rng.triangular(1.0, 1.3, 1.5, N)
v1_trip = ((fe_l / 100) * d_long + (fe_s / 100) * (p * d_short)) * EF_DIESEL_KG_PER_L
v1_total_t = v1_trip * (8122.08 / 25) / 1000
print("\n== (B) v1 reproduction: per-trip mean %.1f kg (report: 138.1) -> system %.1f t CO2 (report: 44.9)" % (v1_trip.mean(), v1_total_t.mean()))

# --- v2: long-haul recomputed bottom-up from the 30 hauling records -----------------------------------------
m3km = float((LH.m3 * LH.dist_km).sum())                      # m3-km of chip hauled (data, not assumption)
tot_m3 = float(LH.m3.sum()); mean_km = m3km / tot_m3
K = m3km * 0.01 * EF_DIESEL_KG_PER_L / 1000                    # t CO2 per (L/100km * return_factor / m3_per_trailer)
cap = rng.triangular(*TRAILER_M3, N); fe = lognorm_from_ci(*FE_LONG_L100, N)
def v2(rt): return K * rt * fe / cap
v2_oneway, v2_round = v2(1.0), v2(2.0)
trips_mid = tot_m3 / TRAILER_M3[1]
print(f"long-haul records: {len(LH)} | total {tot_m3:,.0f} m3 = {tot_m3*0.16:,.0f} t @0.16 / {tot_m3*0.20:,.0f} t @0.20 t/m3 | m3-weighted mean haul {mean_km:.0f} km")
print(f"trips: v1 assumed 325 (25 t/truck) | v2 central {trips_mid:,.0f} ({TRAILER_M3[1]} m3/trailer); range {tot_m3/TRAILER_M3[2]:,.0f}-{tot_m3/TRAILER_M3[0]:,.0f}")
tab = pd.DataFrame({"v1 (report)": [v1_total_t.mean(), *np.percentile(v1_total_t, [5, 95])],
                    "v2 one-way distances": [v2_oneway.mean(), *np.percentile(v2_oneway, [5, 95])],
                    "v2 round-trip distances": [v2_round.mean(), *np.percentile(v2_round, [5, 95])]}, index=["mean tCO2", "P5", "P95"]).round(1)
print(tab.to_string()); tab.to_csv(OUT / "v1_vs_v2_transport.csv")
print("kg CO2 per tonne chip (0.16 t/m3): v1 %.1f | v2 one-way %.1f | v2 round-trip %.1f" % (v1_total_t.mean()*1000/8122.08, v2_oneway.mean()*1000/(tot_m3*0.16), v2_round.mean()*1000/(tot_m3*0.16)))
print("share of the biochar-vs-mulch benefit (4,061 tCO2e): v1 %.1f%% | v2 round-trip upper %.1f%%" % (v1_total_t.mean()/4061*100, v2_round.mean()/4061*100))

# --- tornado (one-at-a-time) around the central case ----------------------------------------------------------
fe_mid = np.exp(0.5 * (np.log(FE_LONG_L100[0]) + np.log(FE_LONG_L100[1]))); cap_mid = TRAILER_M3[1]; rt_mid = 1.5
base = K * rt_mid * fe_mid / cap_mid
tor = {"Trailer capacity (60-95 m3)": (K*rt_mid*fe_mid/TRAILER_M3[2], K*rt_mid*fe_mid/TRAILER_M3[0]),
       "One-way vs round-trip km (1.0-2.0)": (K*1.0*fe_mid/cap_mid, K*2.0*fe_mid/cap_mid),
       "Fuel economy (29-47 L/100km)": (K*rt_mid*FE_LONG_L100[0]/cap_mid, K*rt_mid*FE_LONG_L100[1]/cap_mid)}
fig, ax = plt.subplots(figsize=(7, 3)); 
for i, (k, (lo, hi)) in enumerate(sorted(tor.items(), key=lambda kv: kv[1][1]-kv[1][0])):
    ax.barh(i, hi-base, left=base, color="#c0504d"); ax.barh(i, lo-base, left=base, color="#4f81bd"); ax.text(hi+1, i, f"{lo:.0f}-{hi:.0f}", va="center", fontsize=8)
ax.set_yticks(range(len(tor))); ax.set_yticklabels([k for k, _ in sorted(tor.items(), key=lambda kv: kv[1][1]-kv[1][0])], fontsize=8)
ax.axvline(base, color="k", lw=1); ax.set_xlabel("Long-haul transport emissions (tCO2)"); ax.set_title("v2 tornado: which assumption matters most", fontsize=9); fig.tight_layout(); fig.savefig(OUT / "fig_tornado_v2.png", dpi=160)

# --- Sobol indices on the closed-form model -----------------------------------------------------------------------
prob = {"num_vars": 3, "names": ["trailer_m3", "fuel_L100", "km_factor"], "bounds": [[0, 1]] * 3}
X = sob_s.sample(prob, 4096, calc_second_order=False)
cap_s = stats.triang.ppf(X[:, 0], c=(TRAILER_M3[1]-TRAILER_M3[0])/(TRAILER_M3[2]-TRAILER_M3[0]), loc=TRAILER_M3[0], scale=TRAILER_M3[2]-TRAILER_M3[0])
sg = (np.log(FE_LONG_L100[1]) - np.log(FE_LONG_L100[0])) / (2*1.96); fe_s2 = stats.lognorm.ppf(X[:, 1], s=sg, scale=fe_mid)
km_s = 1.0 + X[:, 2]
Y = K * km_s * fe_s2 / cap_s; Si = sob_a.analyze(prob, Y, calc_second_order=False, print_to_console=False)
sob = pd.DataFrame({"S1": Si["S1"], "ST": Si["ST"]}, index=prob["names"]).round(2); print("\nSobol indices (v2 long-haul emissions):"); print(sob.to_string()); sob.to_csv(OUT / "sobol_v2.csv")
