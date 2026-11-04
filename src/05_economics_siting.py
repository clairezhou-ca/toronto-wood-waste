"""Phase 2: per-tonne techno-economics (break-even carbon price, Monte Carlo + tornado) and biochar siting (p-median MILP)."""
import numpy as np, pandas as pd, json, warnings; warnings.filterwarnings("ignore")
from config import *
rng = np.random.default_rng(42)
M = pd.read_csv(OUT / "ward_station_matrix.csv", dtype={"ward": str}); S = pd.read_csv(OUT / "ward_supply.csv", dtype={"ward": str}).set_index("ward")
share = S.supply_share_ba; km = M.pivot(index="ward", columns="station", values="km").loc[share.index]; mins = M.pivot(index="ward", columns="station", values="minutes").loc[share.index]
crf = DISC * (1 + DISC) ** LIFE_YR / ((1 + DISC) ** LIFE_YR - 1)

def econ(d_site, p):
    """All inputs scalar or arrays. Returns incremental cost ($/wet t), net CO2e (t/wet t), break-even ($/tCO2e)."""
    dry = 1 - p["moist"]
    inc = (p["capex"] * crf + p["opex"] + p["ctkm"] * d_site) - dry * p["yield"] * p["price"] - p["ctkm"] * D_BAU_KM
    co2 = dry * (p["seq"] - p["proc"]) + EF_TKM * (D_BAU_KM - d_site) / 1000
    return inc, co2, np.maximum(inc, 0) / co2
mid = dict(moist=.45, **{"yield": .25}, seq=.60, proc=.10, capex=450, opex=40, price=300, ctkm=.20)

# ---------- siting: p-median with plant capacity (wards -> sites) ---------------------------------------------------------
sites = list(km.columns); q = share * Q_TOTAL_T; rows = []
def pmedian(p_open, cap):
    """Capacitated p-median as a MILP (scipy.optimize.milp / HiGHS). Vars: y_j (open) then x_wj (share of ward w sent to j)."""
    from scipy.optimize import milp, LinearConstraint, Bounds
    W, J = len(km.index), len(sites); nv = J + W * J; qv = q.values; D = km.values
    c = np.concatenate([np.zeros(J), (qv[:, None] * D).ravel()])
    A, lo, hi = [], [], []
    for w in range(W):                                   # each ward fully served
        r = np.zeros(nv); r[J + w * J: J + (w + 1) * J] = 1; A.append(r); lo.append(1); hi.append(1)
    for j in range(J):                                   # plant capacity
        r = np.zeros(nv); r[J + j::J] = qv; r[j] = -cap; A.append(r); lo.append(-np.inf); hi.append(0)
    for w in range(W):
        for j in range(J):                               # only ship to open plants
            r = np.zeros(nv); r[J + w * J + j] = 1; r[j] = -1; A.append(r); lo.append(-np.inf); hi.append(0)
    r = np.zeros(nv); r[:J] = 1; A.append(r); lo.append(p_open); hi.append(p_open)
    res = milp(c, constraints=LinearConstraint(np.array(A), lo, hi), integrality=np.concatenate([np.ones(J), np.zeros(W * J)]), bounds=Bounds(0, 1))
    assert res.success, res.message
    opened = [sites[j] for j in range(J) if res.x[j] > .5]
    return opened, res.fun / q.sum()
for p_open, cap in [(1, Q_TOTAL_T * 1.01), (2, Q_TOTAL_T * .6), (3, Q_TOTAL_T * .4)]:
    op, dbar = pmedian(p_open, cap); inc, co2, be = econ(dbar, mid)
    rows.append(dict(plants=p_open, sites="+".join(op), capacity_t_yr_each=round(cap), mean_haul_km=round(dbar, 1), incr_cost_per_t=round(float(inc), 1), net_tco2e_per_t=round(float(co2), 3), breakeven_carbon_price=round(float(be), 1)))
P = pd.DataFrame(rows); print("== siting (p-median, illustrative economics) =="); print(P.to_string(index=False)); P.to_csv(OUT / "siting_pmedian.csv", index=False)
single = pd.DataFrame({"site": sites, "mean_haul_km": [(q * km[j]).sum() / q.sum() for j in sites], "mean_minutes": [(q * mins[j]).sum() / q.sum() for j in sites]}).sort_values("mean_haul_km")
single["breakeven_carbon_price"] = [round(float(econ(d, mid)[2]), 1) for d in single.mean_haul_km]; print("\n== single-site ranking =="); print(single.round(1).to_string(index=False)); single.round(2).to_csv(OUT / "siting_single_site.csv", index=False)
d_best = float(single.mean_haul_km.iloc[0])

# ---------- Monte Carlo of break-even carbon price (best single site) ------------------------------------------------------
N = 20_000; T = lambda r: rng.triangular(*r, N)
pm = dict(moist=T(MOISTURE), **{"yield": T(YIELD)}, seq=T(SEQ_PER_DRY_T), proc=T(PROC_PER_DRY_T), capex=T(CAPEX_PER_TYR), opex=T(OPEX_PER_T), price=T(BIOCHAR_PRICE), ctkm=T(C_TKM))
inc, co2, be = econ(d_best, pm)
q_ = np.percentile(be, [5, 50, 95]); print(f"\n== Monte Carlo break-even carbon price at {single.site.iloc[0]} ({d_best:.1f} km mean haul): P5 {q_[0]:.0f} | median {q_[1]:.0f} | P95 {q_[2]:.0f} $/tCO2e")
print("P(break-even <= $65) = %.0f%% | P(<= $100) = %.0f%% | P(<= $0, i.e. cheaper without carbon value) = %.0f%%" % tuple((be <= v).mean() * 100 for v in (65, 100, 0.001)))
# upper bound: whole City contract fee counts as avoided cost
dens = rng.triangular(.16, .17, .20, N); contract = T(CONTRACT_PER_M3) / dens
inc_up = inc - (contract - pm["ctkm"] * D_BAU_KM); print("upper bound (full contract fee avoided): P(biochar cheaper without carbon value) = %.0f%%" % ((inc_up <= 0).mean() * 100))
# ---------- tornado (one-at-a-time low/high), break-even ---------------------------------------------------------------------
rngs = dict(moist=MOISTURE, **{"yield": YIELD}, seq=SEQ_PER_DRY_T, proc=PROC_PER_DRY_T, capex=CAPEX_PER_TYR, opex=OPEX_PER_T, price=BIOCHAR_PRICE, ctkm=C_TKM)
tor = []
for k, (lo, m_, hi) in rngs.items():
    a = float(econ(d_best, {**mid, k: lo})[2]); b = float(econ(d_best, {**mid, k: hi})[2]); tor.append((k, a, b))
tor = pd.DataFrame(tor, columns=["parameter", "breakeven_at_low", "breakeven_at_high"]); tor["swing"] = (tor.breakeven_at_high - tor.breakeven_at_low).abs()
tor = tor.sort_values("swing", ascending=False); print("\n== tornado: break-even carbon price ($/tCO2e), central =", round(float(econ(d_best, mid)[2]), 1)); print(tor.round(1).to_string(index=False)); tor.round(2).to_csv(OUT / "tornado_breakeven.csv", index=False)
json.dump({"mc_p5_p50_p95": [round(float(v), 1) for v in q_], "d_best_km": round(d_best, 2), "central_breakeven": round(float(econ(d_best, mid)[2]), 1)}, open(OUT / "econ_summary.json", "w"))
