"""Load raw files into DuckDB and run the SQL cleaning layer."""
import duckdb, pandas as pd, warnings
from config import *
warnings.filterwarnings("ignore")

XLSX = RAW / "Toronto_Urban_Forest_Biomass_Data.xlsx"
con = duckdb.connect(str(DB))

weigh = pd.read_excel(XLSX, sheet_name="ALL Woodchips Transactions")
long = pd.read_excel(XLSX, sheet_name="Dlong", header=1)
long.columns = [str(c).strip() for c in long.columns]
long = long.rename(columns={"Year": "year", "Service Site": "site", "Total Quantity (m3)": "m3",
                            "Distance Long (dlong)": "dist_km", "Vendor Name": "vendor"})
long = long[["year", "site", "m3", "dist_km", "vendor"]].dropna(subset=["m3"])
long["site"] = long["site"].str.strip()
short = pd.read_excel(XLSX, sheet_name="Dshort"); short.columns = [str(c).strip() for c in short.columns]

con.register("weigh_df", weigh); con.execute("CREATE OR REPLACE TABLE weigh_raw AS SELECT * FROM weigh_df")
con.register("long_df", long);   con.execute("CREATE OR REPLACE TABLE longhaul_raw AS SELECT * FROM long_df")
con.register("short_df", short); con.execute("CREATE OR REPLACE TABLE shorthaul_raw AS SELECT * FROM short_df")
con.execute("CREATE OR REPLACE TABLE station_map AS SELECT * FROM (VALUES " +
            ",".join(f"('{k}','{v}')" for k, v in SITE_TO_STATION.items()) + ") t(site_code, station)")
for f in ["01_clean_weighscale.sql", "02_longhaul.sql"]:
    con.execute((ROOT / "sql" / f).read_text())

print("raw weigh rows:", len(weigh), "| after de-dup:", con.execute("select count(*) from weigh_clean").fetchone()[0],
      "| zero-weight:", con.execute("select count(*) from weigh_clean where not has_weight").fetchone()[0])
print("\n== station summary (2023 weigh scale) =="); print(con.execute("select * from v_station_summary").df().to_string(index=False))
print("\n== payer mix =="); print(con.execute("select * from v_payer_mix").df().to_string(index=False))
print("\n== long-haul records by year =="); print(con.execute("select * from v_longhaul_by_year").df().to_string(index=False))
print("\nlong-haul total m3:", con.execute("select sum(m3) from longhaul_clean").fetchone()[0],
      "| tonnes@160:", round(con.execute("select sum(tonnes_160) from longhaul_clean").fetchone()[0],2),
      "| tonnes@200:", round(con.execute("select sum(tonnes_200) from longhaul_clean").fetchone()[0],2))
con.execute("select * from v_station_summary").df().to_csv(OUT / "weigh_station_summary.csv", index=False)
con.execute("select * from v_monthly").df().to_csv(OUT / "weigh_monthly.csv", index=False)
