-- Weigh-scale transactions (2023): de-duplicate, flag zero-weight, map site code to transfer station.
CREATE OR REPLACE TABLE weigh_clean AS
WITH dedup AS (
    SELECT DISTINCT * FROM weigh_raw                       -- exact duplicate rows exist in the source extract
), mapped AS (
    SELECT
        CAST(DateOut AS DATE)                      AS date_out,
        date_trunc('month', CAST(DateOut AS DATE)) AS month,
        SiteCode                                   AS site_code,
        st.station,
        TranNum                                    AS tran_num,
        BillCompany                                AS bill_company,
        VTEntryLabel                               AS vehicle_type,
        NetSTN                                     AS net_stn,
        TransTotalFee                              AS fee_cad
    FROM dedup d
    LEFT JOIN station_map st ON st.site_code = d.SiteCode
)
SELECT *, net_stn > 0 AS has_weight FROM mapped;

CREATE OR REPLACE VIEW v_station_summary AS
SELECT station,
       count(*)                                  AS loads,
       round(sum(net_stn), 1)                    AS net_stn_total,
       round(avg(net_stn), 2)                    AS mean_load,
       round(quantile_cont(net_stn, 0.5), 2)     AS median_load,
       round(quantile_cont(net_stn, 0.95), 2)    AS p95_load,
       round(sum(fee_cad), 0)                    AS fees_cad,
       round(sum(CASE WHEN fee_cad > 0 THEN net_stn END), 1) AS paying_stn
FROM weigh_clean WHERE has_weight GROUP BY 1 ORDER BY net_stn_total DESC;

CREATE OR REPLACE VIEW v_monthly AS
SELECT month, count(*) AS loads, round(sum(net_stn),1) AS net_stn FROM weigh_clean WHERE has_weight GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE VIEW v_payer_mix AS
SELECT bill_company, count(*) AS loads, round(sum(net_stn),1) AS net_stn, round(sum(fee_cad),0) AS fees_cad,
       round(sum(fee_cad)/nullif(sum(CASE WHEN fee_cad>0 THEN net_stn END),0),2) AS fee_per_stn
FROM weigh_clean WHERE has_weight GROUP BY 1 ORDER BY net_stn DESC;
