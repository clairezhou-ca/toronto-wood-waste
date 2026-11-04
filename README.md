# Toronto Urban Wood Waste: Mulch vs Biochar (spatial LCA + techno-economic model)

Status: **Phases 1-2 complete**: data audit, supply layer, road network, v1->v2 transport LCA, techno-economics (break-even carbon price, Monte Carlo, tornado),
biochar siting (p-median MILP), and an interactive page (`docs/index.html`, deployable on GitHub Pages: Settings -> Pages -> /docs).

Stack: Python (pandas, GeoPandas, NetworkX, SciPy, SALib), SQL (DuckDB), ArcGIS Pro (cartography, Phase 3), Leaflet (web).

## Run
```
pip install -r requirements.txt
cd src && python 01_build_warehouse.py && python 02_supply.py && python 03_network.py && python 04_validate_and_v2.py && python 05_economics_siting.py && python 06_build_page.py
```
Raw inputs (City of Toronto Open Data + lab-provided weigh-scale/haul workbook) are not distributed. See `src/config.py` for every assumption.

## Layout
`sql/` cleaning layer | `src/` pipeline | `outputs/` aggregated results and figures | `docs/PHASE1_FINDINGS.md`, `docs/PHASE2_FINDINGS.md` findings and limitations | `docs/index.html` interactive map
