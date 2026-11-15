USE airline_crm;
GO

SELECT COUNT(*) AS contacts,
       SUM(CASE WHEN k.source_id IS NOT NULL THEN 1 ELSE 0 END) AS linked_to_a_customer
FROM src.service_contacts s
LEFT JOIN dw.customer_link k ON k.source_system = 'service' AND k.source_id = s.contact_id;

SELECT topic, COUNT(*) AS contacts,
       CAST(AVG(1.0 * satisfaction_1_5) AS decimal(3,2)) AS avg_satisfaction,
       CAST(AVG(resolution_hours) AS decimal(5,1)) AS avg_resolution_hours
FROM src.service_contacts
GROUP BY topic
ORDER BY contacts DESC;

WITH fx AS (
    SELECT booking_id,
           CASE WHEN flight_cancelled = 1 THEN '1 Cancelled'
                WHEN arr_delay_min >= 60  THEN '2 Delayed 60+ min'
                WHEN arr_delay_min >= 15  THEN '3 Delayed 15-59 min'
                ELSE '4 On time' END AS flight_experience
    FROM dw.fact_booking
    WHERE booking_status IN ('Flown', 'Flight cancelled')
),
b AS (SELECT flight_experience, COUNT(*) AS bookings FROM fx GROUP BY flight_experience),
s AS (
    SELECT e.flight_experience,
           COUNT(*) AS contacts,
           AVG(1.0 * sc.satisfaction_1_5) AS avg_satisfaction,
           AVG(sc.resolution_hours) AS avg_resolution_hours
    FROM src.service_contacts sc
    JOIN fx e ON e.booking_id = sc.booking_id
    GROUP BY e.flight_experience
)
SELECT b.flight_experience, b.bookings, s.contacts,
       CAST(1000.0 * s.contacts / b.bookings AS decimal(6,1)) AS contacts_per_1000_bookings,
       CAST(s.avg_satisfaction AS decimal(3,2)) AS avg_satisfaction,
       CAST(s.avg_resolution_hours AS decimal(5,1)) AS avg_resolution_hours
FROM b JOIN s ON s.flight_experience = b.flight_experience
ORDER BY b.flight_experience;

USE airline_crm;
GO

CREATE OR ALTER VIEW dw.v_customer_360 AS
SELECT c.customer_id, c.first_name, c.last_name, c.country, c.age, c.marketing_consent,
       c.loyalty_tier, c.n_loyalty_profiles, c.points_total,
       c.n_flown, c.first_flight_date, c.last_flight_date, c.revenue_eur,
       r.segment AS rfm_segment,
       ISNULL(w.web_sessions, 0) AS web_sessions,
       ISNULL(w.abandoned_at_payment, 0) AS abandoned_at_payment,
       ISNULL(s.service_contacts, 0) AS service_contacts,
       s.avg_satisfaction
FROM dw.dim_customer c
LEFT JOIN dw.rfm r ON r.customer_id = c.customer_id
LEFT JOIN (SELECT k.customer_id, COUNT(*) AS web_sessions,
                  SUM(CASE WHEN TRY_CAST(LEFT(ws.furthest_stage, 1) AS int) = 5 THEN 1 ELSE 0 END) AS abandoned_at_payment
           FROM dw.customer_link k
           JOIN src.web_sessions ws ON ws.session_id = k.source_id
           WHERE k.source_system = 'web'
           GROUP BY k.customer_id) w ON w.customer_id = c.customer_id
LEFT JOIN (SELECT k.customer_id, COUNT(*) AS service_contacts,
                  CAST(AVG(1.0 * sc.satisfaction_1_5) AS decimal(3,2)) AS avg_satisfaction
           FROM dw.customer_link k
           JOIN src.service_contacts sc ON sc.contact_id = k.source_id
           WHERE k.source_system = 'service'
           GROUP BY k.customer_id) s ON s.customer_id = c.customer_id;
GO

SELECT TOP 10 * FROM dw.v_customer_360 ORDER BY revenue_eur DESC;
SELECT COUNT(*) AS customers FROM dw.v_customer_360; 

SELECT rfm_segment,
       COUNT(*) AS customers,
       SUM(CASE WHEN service_contacts > 0 THEN 1 ELSE 0 END) AS contacted_service,
       SUM(CASE WHEN avg_satisfaction <= 2.5 THEN 1 ELSE 0 END) AS unhappy,
       SUM(CASE WHEN avg_satisfaction <= 2.5 AND marketing_consent = 1 THEN 1 ELSE 0 END) AS unhappy_and_contactable
FROM dw.v_customer_360
WHERE rfm_segment IN ('Champions', 'Loyal', 'At risk')
GROUP BY rfm_segment;