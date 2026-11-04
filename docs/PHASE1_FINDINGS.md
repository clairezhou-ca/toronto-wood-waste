# Phase 1 findings: Toronto urban wood waste, data audit, supply layer, network, v1 -> v2

All numbers are reproducible with `src/01..04`. Raw City data and the DuckDB warehouse (plates, transaction IDs, hauler names)
are **not** in the repo; only aggregated outputs are.

## 1. Data audit (what changed vs. the v1 report)
| Item | v1 report | Finding |
|---|---|---|
| 8,122 t "functional unit" | treated as one cohort | Sum of 30 hauling records spanning **2022-2025** (2022: 1,748 t; 2023: 3,250 t; 2024: 1,172 t; 2025: 1,952 t). Not an annual quantity |
| Payload per trip | Dlong rows sampled as per-trip payloads (mean 270 t) | Each row is a **site x period x vendor aggregate** (m3), not a truck load |
| Trips | 8,122 / 25 t = 325 | Bottom-up from m3 and trailer size: **~677** (534-846 for 95-60 m3 trailers) |
| Bulk density | 0.16 t/m3 | The sheet's own note says 0.20 t/m3 -> 10,153 t instead of 8,122 t (+25 %) |
| Weigh-scale extract | n/a | 427 rows -> 403 after removing 24 exact duplicates; 2 zero-weight loads; mean load ~2.1 STN (unit to confirm: short ton vs tonne) |
| Weigh-scale coverage | n/a | 859 STN total in 2023 vs 3,250 t hauled in 2023 -> the extract is a **partial stream** |

## 2. Supply layer (25 wards)
- 688,335 street trees; ward label matches spatial join 100 %; 3,307 missing DBH (ward-median imputed); 77 values > 200 cm capped.
- 53,758 wood-generating 311 requests (Forestry Operations, 2024-2025).
- Proxy test vs 311 requests, leave-one-out R2 (n = 25): tree count 0.33 | **street-tree basal area 0.65** | green-space area -0.11 | BA + green 0.53.
- Decision: basal area is the supply index. Green Spaces (City-managed classes only) did **not** improve prediction, so it is used only as a
  sensitivity scenario. It may still matter for park-generated wood that never goes through 311, but that cannot be validated with the data held.

## 3. Road network (Toronto Centreline)
- 43,094 truck-usable segments; 31,762 nodes; 99.7 % in the largest strongly-connected component; one-way restrictions respected.
- Speeds are **assumed by road class** (expressway 80 ... local 30 km/h). No city-wide speed/congestion data was available (Midblock counts cover individual streets only).
- Sanity check: network/straight-line distance median 1.35 (typical urban range 1.3-1.4). Ward-supply-centroid -> station: median 16.9 km / 17.1 min.

## 4. Validation: negative result
Nearest-station assignment of the basal-area supply vs observed 2023 weigh-scale shares (6 stations): **Spearman -0.43 (p = 0.40, n = 6)**.
Dufferin and Scarborough receive ~65 % of observed tonnage but ~20 % of modelled tonnage.
Interpretation: with n = 6 this is inconclusive statistically, but it gives **no support** to "vehicles go to the nearest station". Likely reasons: contractor
choice, a partial extract dominated by few accounts, and Disco absent from the data. The extract has no origin field, so an origin-destination matrix cannot be built.
Consequence: Phase 2 must not claim savings from "re-routing existing flows". It frames the problem as **biochar facility siting**, which only needs supply shares and network times.

## 5. v1 -> v2 transport emissions (long-haul legs only)
| | v1 report | v2 one-way km | v2 round-trip km |
|---|---|---|---|
| Mean tCO2 | 44.8 (report 44.9; reproduced) | 79.8 | 159.6 |
| P5 - P95 | 32.7 - 60.4 | 60.9 - 101.9 | 121.9 - 203.7 |
| kg CO2 per tonne chip | 5.5 | 9.8 | 19.7 |
| Share of biochar-vs-mulch benefit (4,061 tCO2e) | 1.1 % | 2.0 % | 3.9 % |

Sobol first-order indices: one-way vs round-trip km **0.60**, fuel economy 0.25, trailer capacity 0.14.
**The biochar-beats-mulch conclusion survives** (transport stays below ~4 % of the benefit), but the transport number is 1.8x-3.6x higher than reported,
and the single most valuable fact to verify is whether the 101-155 km distances in Dlong are one-way or round trip.

## 6. Open questions / assumptions to verify
1. Dlong distances: one-way or round trip? (60 % of v2 variance)
2. Trailer capacity (60-95 m3 assumed; check hauler invoices)
3. Bulk density 0.16 vs 0.20 t/m3; wet vs dry basis for the biochar sequestration credit (Phase 2)
4. STN unit; whether the weigh-scale extract is filtered
5. Time mismatch: weigh scale 2023, hauls 2022-2025, 311 2024-2025, tree inventory snapshot
6. Transfer-station file is from 2012; confirm current status
7. Publishing: get supervisor approval; publish aggregates only
