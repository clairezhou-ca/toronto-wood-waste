"""ArcGIS Pro (arcpy) helper: add layers, apply the ward choropleth, export the layout.
UNTESTED: written without ArcGIS Pro access. Run in the Pro Python window; adjust GPKG and LAYOUT_NAME first."""
import arcpy
GPKG = r"C:\path\to\arcgis_package.gpkg"        # <- edit
LAYOUT_NAME = "WoodWasteMap"                    # <- name of an existing layout in the project
OUT_PNG = r"C:\path\to\toronto_wood_waste_map.png"

aprx = arcpy.mp.ArcGISProject("CURRENT")
m = aprx.listMaps()[0]
for name in ["wards_supply", "green_spaces_city", "roads_arterial", "routes_to_ingram", "transfer_stations"]:
    m.addDataFromPath(f"{GPKG}\\main.{name}")   # GeoPackage tables are addressed as <file>.gpkg\main.<table>

wards = m.listLayers("wards_supply")[0]
sym = wards.symbology
sym.updateRenderer("GraduatedColorsRenderer")
r = sym.renderer
r.classificationField = "supply_pct"
r.breakCount = 5
r.classificationMethod = "Quantile"
ramps = aprx.listColorRamps("Greens*")
if ramps: r.colorRamp = ramps[0]
wards.symbology = sym

layout = aprx.listLayouts(LAYOUT_NAME)[0]
layout.exportToPNG(OUT_PNG, resolution=200)
print("exported", OUT_PNG)
