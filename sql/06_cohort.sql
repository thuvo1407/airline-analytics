USE airline_crm;
GO

DROP TABLE IF EXISTS dw.cohort_activity;

WITH flown AS (
    SELECT fb.customer_id,
           DATEFROMPARTS(YEAR(fb.flight_date), (MONTH(fb.flight_date) - 1) / 3 * 3 + 1, 1) AS flight_q
    FROM dw.fact_booking fb
    JOIN dw.dim_customer c ON c.customer_id = fb.customer_id
    WHERE fb.booking_status = 'Flown'
      AND c.created_date >= '2023-01-01'
      AND fb.flight_date <= '2026-09-30'
),
first_q AS (
    SELECT customer_id, MIN(flight_q) AS cohort_q FROM flown GROUP BY customer_id
)
SELECT DISTINCT f.customer_id, q.cohort_q, f.flight_q,
       DATEDIFF(quarter, q.cohort_q, f.flight_q) AS quarters_since_first
INTO dw.cohort_activity
FROM flown f
JOIN first_q q ON q.customer_id = f.customer_id;
GO

SELECT COUNT(DISTINCT customer_id) AS customers_in_cohorts FROM dw.cohort_activity;

DROP TABLE IF EXISTS dw.cohort_retention;

WITH ret AS (
    SELECT cohort_q, quarters_since_first AS k, COUNT(DISTINCT customer_id) AS active
    FROM dw.cohort_activity
    GROUP BY cohort_q, quarters_since_first
),
cohort_size AS (
    SELECT cohort_q, active AS cohort_size FROM ret WHERE k = 0
)
SELECT r.cohort_q, s.cohort_size, r.k, r.active,
       CAST(100.0 * r.active / s.cohort_size AS decimal(5,1)) AS retention_pct
INTO dw.cohort_retention
FROM ret r
JOIN cohort_size s ON s.cohort_q = r.cohort_q;
GO

--one row per cohort, one column per quarter since first flight
SELECT cohort_q, cohort_size,
       [1] AS q1, [2] AS q2, [3] AS q3, [4] AS q4, [6] AS q6, [8] AS q8
FROM (SELECT cohort_q, cohort_size, k, retention_pct FROM dw.cohort_retention) s
PIVOT (MAX(retention_pct) FOR k IN ([1], [2], [3], [4], [6], [8])) p
ORDER BY cohort_q;

SELECT c.is_loyalty_member,
       COUNT(*) AS first_time_flyers,
       SUM(r.returned) AS came_back_within_4_quarters,
       CAST(100.0 * SUM(r.returned) / COUNT(*) AS decimal(5,1)) AS pct_came_back
FROM (SELECT customer_id, MIN(cohort_q) AS cohort_q,
             MAX(CASE WHEN quarters_since_first BETWEEN 1 AND 4 THEN 1 ELSE 0 END) AS returned
      FROM dw.cohort_activity
      GROUP BY customer_id) r
JOIN dw.dim_customer c ON c.customer_id = r.customer_id
WHERE r.cohort_q <= '2025-07-01'
GROUP BY c.is_loyalty_member;

WITH t AS (
    SELECT customer_id, flight_date,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY flight_date, booking_id) AS trip_no
    FROM dw.fact_booking
    WHERE booking_status = 'Flown' AND customer_id IS NOT NULL
)
SELECT DISTINCT
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY DATEDIFF(day, a.flight_date, b.flight_date)) OVER () AS median_days_to_second_flight,
       COUNT(*) OVER () AS customers_with_2_plus_flights
FROM t a
JOIN t b ON b.customer_id = a.customer_id AND a.trip_no = 1 AND b.trip_no = 2;