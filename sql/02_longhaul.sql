-- Long-haul sheet: each row is an aggregate (site x period x vendor), NOT a truck trip.
CREATE OR REPLACE TABLE longhaul_clean AS
SELECT row_number() OVER ()          AS rec_id,
       year, site, vendor, m3, dist_km,
       m3 * 0.16                     AS tonnes_160,      -- v1 assumption (160 kg/m3)
       m3 * 0.20                     AS tonnes_200       -- the sheet's own bulk-density note (0.2 t/m3)
FROM longhaul_raw WHERE m3 IS NOT NULL;

CREATE OR REPLACE VIEW v_longhaul_by_year AS
SELECT year, count(*) AS records, sum(m3) AS m3, round(sum(tonnes_160),1) AS t_at_160, round(sum(tonnes_200),1) AS t_at_200
FROM longhaul_clean GROUP BY 1 ORDER BY 1;
