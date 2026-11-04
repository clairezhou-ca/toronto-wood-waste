# Phase 2 findings: techno-economics and biochar siting

Confirmed inputs: Dlong distances are **one-way**; STN treated as metric tonnes (affects only the weigh-scale validation shares).
All economics are illustrative ranges in `src/config.py` (triangular distributions); replace with facility quotes before any decision use.

## Model (per wet tonne of feedstock)
incremental cost = capex x CRF(6 %, 20 yr) + opex + haul-to-plant - biochar revenue - avoided haul to the 120 km mulch processor
net CO2e = dry fraction x (sequestration 0.60 - processing 0.10) + transport difference
break-even carbon price = incremental cost / net CO2e. Credit is applied per **dry** tonne (v1 left the basis unstated).

## Results
| Site (single plant) | Mean haul km | Break-even $/tCO2e |
|---|---|---|
| Ingram | 13.0 | 58 |
| Bermondsey | 16.4 | 61 |
| Dufferin | 16.7 | 61 |
| Commissioners | 17.0 | 61 |
| Victoria Park | 19.3 | 63 |
| Disco | 21.3 | 65 |
| Scarborough | 23.9 | 66 |

- Monte Carlo (20,000 draws, Ingram): break-even P5 / median / P95 = **0 / 59 / 188 $/tCO2e**; P(<= $65) = 53 %, P(<= $100) = 70 %, P(cheaper with no carbon value) = 23 %.
- If the whole City haul contract fee (about $16.7/m3) is counted as avoided cost, biochar is cheaper at zero carbon value in 99 % of draws (upper bound; assumes the fee is genuinely avoidable).
- Tornado (swing in break-even): capex 166, opex 159, biochar price 155, haul cost 96, yield 58, moisture 51, sequestration 33, processing 11.
- p-median siting (capacitated MILP): 1 plant at Ingram 13.0 km; 2 plants (Bermondsey + Ingram) 9.4 km; 3 plants 9.0 km. Scale economies are not modelled, so extra plants are not shown to pay.

## Interpretation
Siting moves the break-even by only about $8/tCO2e. The decision is driven by plant cost and biochar price, not by where the plant sits. The headline "biochar beats mulch" holds on climate; whether it is cheaper depends on assumptions that need real quotes.
Mulch decomposition emissions are set to zero (conservative for biochar). Congestion is not modelled (no city-wide speed data).
