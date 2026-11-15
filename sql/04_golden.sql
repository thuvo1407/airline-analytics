USE airline_crm;
GO

DROP TABLE IF EXISTS dw.fact_booking;

SELECT b.booking_id,
       k.customer_id,                 -- NULL only for the few bookings the rules could not link
       k.match_rule AS link_rule,
       b.flight_id, b.flight_date, b.booking_date,
       f.route_id, f.region, f.origin, f.destination,
       b.fare_class, b.channel, b.fare_eur, b.ancillary_eur,
       b.fare_eur + b.ancillary_eur AS revenue_eur,
       b.booking_status,
       f.cancelled AS flight_cancelled, f.arr_delay_min,
       DATEDIFF(day, b.booking_date, b.flight_date) AS days_booked_ahead
INTO dw.fact_booking
FROM src.bookings b
JOIN src.flights f ON f.flight_id = b.flight_id
LEFT JOIN dw.customer_link k ON k.source_system = 'booking' AND k.source_id = b.booking_id;

ALTER TABLE dw.fact_booking ALTER COLUMN booking_id varchar(20) NOT NULL;
ALTER TABLE dw.fact_booking ADD CONSTRAINT pk_fact_booking PRIMARY KEY (booking_id);
GO

DROP TABLE IF EXISTS dw.dim_customer;

WITH loy AS (
    SELECT k.customer_id,
           COUNT(*) AS n_loyalty_profiles,
           MAX(CASE y.tier WHEN 'Platinum' THEN 4 WHEN 'Gold' THEN 3 WHEN 'Silver' THEN 2 ELSE 1 END) AS tier_rank,
           SUM(y.points_balance) AS points_total
    FROM dw.customer_link k
    JOIN src.loyalty y ON y.member_id = k.source_id
    WHERE k.source_system = 'loyalty'
    GROUP BY k.customer_id
),
bk AS (
    SELECT customer_id,
           COUNT(*) AS n_bookings,
           SUM(CASE WHEN booking_status = 'Flown' THEN 1 ELSE 0 END) AS n_flown,
           MIN(CASE WHEN booking_status = 'Flown' THEN flight_date END) AS first_flight_date,
           MAX(CASE WHEN booking_status = 'Flown' THEN flight_date END) AS last_flight_date,
           SUM(CASE WHEN booking_status = 'Flown' THEN revenue_eur ELSE 0 END) AS revenue_eur
    FROM dw.fact_booking
    WHERE customer_id IS NOT NULL
    GROUP BY customer_id
)
SELECT c.customer_id, c.first_name, c.last_name, c.birth_date,
       DATEDIFF(year, c.birth_date, '2026-10-31') AS age,
       c.gender, c.country, c.city, c.postal_code, c.preferred_language,
       c.marketing_consent, c.created_date,
       CASE l.tier_rank WHEN 4 THEN 'Platinum' WHEN 3 THEN 'Gold' WHEN 2 THEN 'Silver' WHEN 1 THEN 'Basic' ELSE 'Not a member' END AS loyalty_tier,
       CASE WHEN l.customer_id IS NULL THEN 0 ELSE 1 END AS is_loyalty_member,
       ISNULL(l.n_loyalty_profiles, 0) AS n_loyalty_profiles,
       ISNULL(l.points_total, 0) AS points_total,
       ISNULL(b.n_bookings, 0) AS n_bookings,
       ISNULL(b.n_flown, 0) AS n_flown,
       b.first_flight_date, b.last_flight_date,
       ISNULL(b.revenue_eur, 0) AS revenue_eur
INTO dw.dim_customer
FROM src.customers c
LEFT JOIN loy l ON l.customer_id = c.customer_id
LEFT JOIN bk  b ON b.customer_id = c.customer_id;

ALTER TABLE dw.dim_customer ALTER COLUMN customer_id varchar(20) NOT NULL;
ALTER TABLE dw.dim_customer ADD CONSTRAINT pk_dim_customer PRIMARY KEY (customer_id);
GO

SELECT (SELECT COUNT(*) FROM dw.dim_customer) AS customers,
       (SELECT COUNT(*) FROM dw.fact_booking) AS bookings,
       (SELECT COUNT(*) FROM dw.fact_booking WHERE customer_id IS NULL) AS bookings_still_unlinked,
       (SELECT COUNT(*) FROM dw.dim_customer WHERE n_flown > 0) AS customers_who_flew,
       (SELECT COUNT(*) FROM dw.dim_customer WHERE n_loyalty_profiles > 1) AS customers_with_2_profiles;

-- what did the linking recover?
SELECT SUM(CASE WHEN link_rule <> 'given' THEN 1 ELSE 0 END) AS bookings_recovered,
       CAST(SUM(CASE WHEN link_rule <> 'given' THEN revenue_eur ELSE 0 END) AS decimal(12,0)) AS revenue_recovered_eur,
       CAST(100.0 * SUM(CASE WHEN link_rule <> 'given' THEN revenue_eur ELSE 0 END) / SUM(revenue_eur) AS decimal(4,1)) AS pct_of_revenue
FROM dw.fact_booking
WHERE booking_status = 'Flown' AND customer_id IS NOT NULL;