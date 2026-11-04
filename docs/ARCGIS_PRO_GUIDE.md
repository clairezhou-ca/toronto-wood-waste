# ArcGIS Pro: publication map + network cross-check

Package: `outputs/arcgis_package.gpkg` (all layers NAD83 / UTM 17N, EPSG:26917). Target look: `outputs/fig_map_preview.png`.

| Layer | Geometry | Key fields | Use |
|---|---|---|---|
| wards_supply | polygon (25) | supply_pct, class5, trees, ba_m2, req311_2yr | choropleth |
| green_spaces_city | polygon | AREA_CLASS | context, 35 % transparency |
| roads_arterial | line | FEATURE_CODE_DESC | context, thin grey |
| routes_to_ingram | line (25) | minutes, km, supply_pct | routes, width by supply_pct |
| transfer_stations | point (7) | mean_haul_km, breakeven_usd_per_tco2e, obs_share_2023, rank_by_haul | sites |
| ward_supply_centroids | point (25) | ward | network origins |

## A. Build the map (about 30 minutes)
1. New Map project. Catalog -> Databases -> Add Database -> select the .gpkg. Drag the six layers in, drawing order: wards_supply, green_spaces_city, roads_arterial, routes_to_ingram, transfer_stations.
2. Map properties -> Coordinate system: NAD 1983 UTM Zone 17N.
3. wards_supply -> Symbology -> Graduated Colors, field `supply_pct`, Method Quantile, 5 classes, ramp Greens (light to dark). Outline white 0.8 pt. Class breaks should match the preview: 0.98 / 2.39 / 3.43 / 3.92 / 5.44 / 8.82 %.
4. green_spaces_city: fill #9CCC9C, transparency 65 %, no outline. roads_arterial: #8A8F8C, 0.35 pt.
5. routes_to_ingram -> Graduated Symbols, field `supply_pct`, line widths 0.8 to 4 pt, colour #D9822B.
6. transfer_stations -> white circle 10 pt, dark outline 1.6 pt; label with `station` (bold, 8 pt, halo). Add a second symbol layer or a definition query for Ingram: orange fill #D9822B, 14 pt.
7. Layout: Letter landscape. Title (left aligned): "Toronto urban wood waste: supply and best biochar site". Legend (ward classes titled "Ward share of supply (street-tree basal area)"), scale bar, north arrow, source note: "City of Toronto Open Data; analysis Y. Zhou. Speeds assumed by road class."
8. Export: PNG 200 dpi (about 2200 px wide) for the website, PDF 300 dpi for the portfolio. Save as `docs/img/toronto_wood_waste_map.png` and link it under the interactive map.

Optional automation: `src/arcgis_build_layout.py` (arcpy). **Untested** (written without ArcGIS Pro access); check paths and layout name before running.

## B. Network Analyst cross-check (adds a real ArcGIS skill, and validates the NetworkX model)
1. Create a feature dataset in a file geodatabase; copy the Toronto Centreline in (original download, not the arterial subset).
2. Create Network Dataset from it. Add a cost attribute `Minutes` = Length / speed using the same class speeds as `src/config.py` (Expressway 80, ramps 50/40, Major Arterial 45, Minor Arterial 40, Collector 35, Local 30 km/h). Apply one-way restrictions from ONEWAY_DIR_CODE_DESC.
3. Network Analyst -> OD Cost Matrix: Origins = ward_supply_centroids, Destinations = transfer_stations, cutoff none, accumulate Length.
4. Export the OD lines table and compare with `outputs/ward_station_matrix.csv` (correlation, mean absolute difference in km and minutes). Report the result either way.
Only after step 4 is done can the resume say Network Analyst was used. Until then the project used NetworkX.
