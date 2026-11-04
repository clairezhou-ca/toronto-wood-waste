"""Central configuration. Every modelling assumption lives here so it can be audited and changed."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = Path("/mnt/user-data/uploads")            # raw City downloads (never committed to the repo)
WORK = Path("/home/claude/data")                # parsed intermediates
OUT = ROOT / "outputs"
DB = ROOT / "data" / "warehouse.duckdb"

# --- Weigh-scale SiteCode -> transfer station (confirmed by the analyst) ---------------------
SITE_TO_STATION = {
    "DU": "Dufferin", "BT": "Bermondsey", "ID": "Ingram",
    "VP": "Victoria Park", "SB": "Scarborough", "CM": "Commissioners",
}
STATION_KEYS = {
    "Dufferin": "Dufferin", "Bermondsey": "Bermondsey", "Disco": "Disco", "Ingram": "Ingram",
    "Victoria Park": "Victoria Park", "Scarborough": "Scarborough", "Commissioners": "Commissioners",
}

# --- Physical assumptions ------------------------------------------------------------------
CHIP_DENSITY_T_PER_M3 = 0.16      # used in the v1 Dlong sheet; the sheet's own note says 0.20 -> sensitivity
CHIP_DENSITY_ALT = 0.20
TRAILER_M3 = (60, 75, 95)          # triangular (min, mode, max) chip-trailer capacity -- ASSUMPTION, verify w/ hauler invoices
ROUND_TRIP_FACTOR = (1.0, 2.0)     # is Dlong one-way or round trip? unknown -> scenario
EF_DIESEL_KG_PER_L = 2.68          # NIR 2025 diesel factor used in v1
FE_LONG_L100 = (29, 47)            # 95% CI, lognormal (v1)
FE_SHORT_L100 = (22, 32)

# --- Road network speeds (km/h) for heavy trucks by Centreline class -- ASSUMPTION, no city-wide speed data
SPEED_KPH = {
    "Expressway": 80, "Expressway Ramp": 50, "Major Arterial": 45, "Major Arterial Ramp": 40,
    "Minor Arterial": 40, "Collector": 35, "Collector Ramp": 35, "Local": 30,
}
SPEED_SENS = 0.20                  # +/-20 % sensitivity on all speeds

# --- Green Spaces classes treated as City-managed tree land -------------------------------------
CITY_GREEN_CLASSES = ["Park", "OTHER_CITY", "Open Green Space", "Building Grounds", "Boulevard",
                      "Civic Centre Square", "Cul de Sac", "Traffic Island", "Cemetery"]

# --- 311 request types that generate wood waste (Forestry Operations) ---------------------------
WOOD_311_TYPES = ["Residential or Park Tree Removal", "Tree Emergency Clean-Up", "Storm Clean Up",
                  "General Pruning", "General Tree Maintenance", "Stump Removal", "Stemming",
                  "Tree Brush Pick-up"]
FULL_YEARS = [2024, 2025]

# ======================= PHASE 2: techno-economic assumptions (ILLUSTRATIVE -- replace with facility quotes) ==========
D_BAU_KM = 120.0                    # one-way yard -> mulch processor (Dlong, confirmed one-way by analyst)
RETURN_FACTOR = 1.75                # Dlong is ONE-WAY (confirmed): truck km = one-way x (1 + empty-return fuel ratio ~0.75) -- ASSUMPTION
EF_TKM = 9.8 * RETURN_FACTOR / 120.0   # kg CO2 per loaded tonne-km incl. empty return
Q_TOTAL_T = 14_400                  # t/yr: staff estimate 90,000 m3/yr x 0.16 t/m3 (lower observed haul stream ~3,250 t in 2023)
MOISTURE = (0.35, 0.45, 0.50); YIELD = (0.20, 0.25, 0.30)          # triangular (min, mode, max)
SEQ_PER_DRY_T = (0.45, 0.60, 0.70); PROC_PER_DRY_T = (0.05, 0.10, 0.15)   # tCO2e per DRY tonne (v1 used 0.6/0.1 with no moisture basis)
CAPEX_PER_TYR = (250, 450, 800); LIFE_YR = 20; DISC = 0.06            # $ per t/yr of capacity
OPEX_PER_T = (25, 40, 70); BIOCHAR_PRICE = (100, 300, 600)           # $/t feedstock ; $/t biochar
C_TKM = (0.10, 0.20, 0.40)                                           # $ per tonne-km hauling
CONTRACT_PER_M3 = (14.0, 16.7, 20.0)                                 # City haul contract $/m3 (upper-bound sensitivity only)
