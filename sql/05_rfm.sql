USE airline_crm;
GO

DROP TABLE IF EXISTS dw.rfm;

WITH base AS (
    SELECT customer_id,
           DATEDIFF(day, last_flight_date, '2026-10-31') AS recency_days,
           n_flown AS frequency,
           revenue_eur AS monetary
    FROM dw.dim_customer
    WHERE n_flown > 0
),
scored AS (
    SELECT *,
           NTILE(5) OVER (ORDER BY recency_days DESC, customer_id) AS r_score,   -- fewest days since flight = 5
           CASE WHEN frequency >= 13 THEN 5 WHEN frequency >= 7 THEN 4
                WHEN frequency >= 4  THEN 3 WHEN frequency >= 2 THEN 2 ELSE 1 END AS f_score,
           NTILE(5) OVER (ORDER BY monetary, customer_id) AS m_score
    FROM base
)
SELECT *,
       CASE WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 4                  THEN 'Loyal'
            WHEN r_score >= 4 AND f_score >= 2                  THEN 'Potential loyalists'
            WHEN r_score >= 4                                   THEN 'New customers'
            WHEN r_score = 3                                    THEN 'Need attention'
            WHEN f_score >= 4                                   THEN 'At risk'
            ELSE 'Hibernating' END AS segment
INTO dw.rfm
FROM scored;
GO

SELECT COUNT(*) AS customers_scored FROM dw.rfm;

SELECT r.segment,
       COUNT(*) AS customers,
       CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS decimal(4,1)) AS pct_customers,
       AVG(r.recency_days) AS avg_days_since_flight,
       CAST(AVG(1.0 * r.frequency) AS decimal(4,1)) AS avg_flights,
       CAST(AVG(r.monetary) AS decimal(8,0)) AS avg_revenue_eur,
       CAST(SUM(r.monetary) AS decimal(12,0)) AS revenue_eur,
       CAST(100.0 * SUM(r.monetary) / SUM(SUM(r.monetary)) OVER () AS decimal(4,1)) AS pct_revenue,
       CAST(100.0 * AVG(1.0 * c.marketing_consent) AS decimal(4,1)) AS pct_can_contact,
       CAST(100.0 * AVG(1.0 * c.is_loyalty_member) AS decimal(4,1)) AS pct_loyalty_members
FROM dw.rfm r
JOIN dw.dim_customer c ON c.customer_id = r.customer_id
GROUP BY r.segment
ORDER BY revenue_eur DESC;

SELECT r.segment,
       COUNT(*) AS flown_bookings,
       CAST(100.0 * SUM(CASE WHEN fb.region IN ('Asia', 'North Atlantic') THEN 1 ELSE 0 END) / COUNT(*) AS decimal(4,1)) AS pct_long_haul,
       CAST(AVG(1.0 * fb.days_booked_ahead) AS decimal(5,1)) AS avg_days_booked_ahead,
       CAST(100.0 * SUM(CASE WHEN fb.fare_class IN ('Flex', 'Business') THEN 1 ELSE 0 END) / COUNT(*) AS decimal(4,1)) AS pct_flex_or_business
FROM dw.fact_booking fb
JOIN dw.rfm r ON r.customer_id = fb.customer_id
WHERE fb.booking_status = 'Flown'
GROUP BY r.segment
ORDER BY pct_long_haul DESC;

SELECT TOP 25 c.customer_id, c.first_name, c.country, c.loyalty_tier,
       r.recency_days, r.frequency, CAST(r.monetary AS decimal(8,0)) AS revenue_eur
FROM dw.rfm r
JOIN dw.dim_customer c ON c.customer_id = r.customer_id
WHERE r.segment = 'At risk' AND c.marketing_consent = 1
ORDER BY r.monetary DESC;