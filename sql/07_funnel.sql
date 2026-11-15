USE airline_crm;
GO

-- clear earlier web links so this file can be re-run safely
DELETE FROM dw.customer_link WHERE source_system = 'web';

-- W1: the visitor was logged in
INSERT INTO dw.customer_link
SELECT 'web', session_id, customer_id, 'given'
FROM src.web_sessions WHERE customer_id IS NOT NULL;

-- W2: the session ended in a booking, and that booking belongs to a known customer
INSERT INTO dw.customer_link
SELECT 'web', w.session_id, fb.customer_id, 'W2 via booking'
FROM src.web_sessions w
JOIN dw.fact_booking fb ON fb.booking_id = w.booking_id
WHERE w.customer_id IS NULL AND fb.customer_id IS NOT NULL;

-- W3: the same device (browser cookie) was seen with exactly ONE known customer
INSERT INTO dw.customer_link
SELECT 'web', w.session_id, d.customer_id, 'W3 device seen with one customer'
FROM src.web_sessions w
JOIN (SELECT s.device_id, MIN(k.customer_id) AS customer_id
      FROM src.web_sessions s
      JOIN dw.customer_link k ON k.source_system = 'web' AND k.source_id = s.session_id
      GROUP BY s.device_id
      HAVING COUNT(DISTINCT k.customer_id) = 1) d ON d.device_id = w.device_id
WHERE NOT EXISTS (SELECT 1 FROM dw.customer_link k2
                  WHERE k2.source_system = 'web' AND k2.source_id = w.session_id);
GO

-- how many sessions can now be tied to a customer?
SELECT COUNT(*) AS sessions,
       SUM(CASE WHEN w.customer_id IS NOT NULL THEN 1 ELSE 0 END) AS known_before,
       SUM(CASE WHEN k.source_id IS NOT NULL THEN 1 ELSE 0 END) AS known_after,
       CAST(100.0 * SUM(CASE WHEN w.customer_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS decimal(4,1)) AS pct_before,
       CAST(100.0 * SUM(CASE WHEN k.source_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS decimal(4,1)) AS pct_after
FROM src.web_sessions w
LEFT JOIN dw.customer_link k ON k.source_system = 'web' AND k.source_id = w.session_id;

-- accuracy per rule, using the answer key
SELECT k.match_rule, COUNT(*) AS links,
       SUM(CASE WHEN k.customer_id = t.truth_customer_id THEN 1 ELSE 0 END) AS correct,
       CAST(100.0 * SUM(CASE WHEN k.customer_id = t.truth_customer_id THEN 1 ELSE 0 END) / COUNT(*) AS decimal(6,2)) AS accuracy_pct
FROM dw.customer_link k
JOIN ans.web_truth t ON t.session_id = k.source_id
WHERE k.source_system = 'web'
GROUP BY k.match_rule;

WITH s AS (
    SELECT TRY_CAST(LEFT(furthest_stage, 1) AS int) AS stage FROM src.web_sessions
),
steps AS (
    SELECT v.step, v.label, SUM(CASE WHEN s.stage >= v.step THEN 1 ELSE 0 END) AS sessions
    FROM s
    CROSS JOIN (VALUES (1, 'Search'), (2, 'Saw results'), (3, 'Selected flight'),
                       (4, 'Passenger details'), (5, 'Payment page'), (6, 'Booking confirmed')) v(step, label)
    GROUP BY v.step, v.label
)
SELECT step, label, sessions,
       CAST(100.0 * sessions / FIRST_VALUE(sessions) OVER (ORDER BY step) AS decimal(5,1)) AS pct_of_start,
       CAST(100.0 * sessions / LAG(sessions) OVER (ORDER BY step) AS decimal(5,1)) AS pct_of_previous_step
FROM steps
ORDER BY step;

GO
CREATE OR ALTER VIEW dw.v_route_region AS
SELECT DISTINCT route_id, region FROM src.flights;
GO

WITH s AS (
    SELECT w.device_type, w.traffic_source, r.region,
           TRY_CAST(LEFT(w.furthest_stage, 1) AS int) AS stage
    FROM src.web_sessions w
    LEFT JOIN dw.v_route_region r ON r.route_id = w.searched_route_id
)
SELECT 'device' AS dimension, device_type AS value, COUNT(*) AS sessions,
       CAST(100.0 * SUM(CASE WHEN stage >= 2 THEN 1 ELSE 0 END) / COUNT(*) AS decimal(4,1)) AS pct_saw_results,
       CAST(100.0 * SUM(CASE WHEN stage = 6 THEN 1 ELSE 0 END) / COUNT(*) AS decimal(4,1)) AS pct_converted
FROM s GROUP BY device_type
UNION ALL
SELECT 'source', traffic_source, COUNT(*),
       CAST(100.0 * SUM(CASE WHEN stage >= 2 THEN 1 ELSE 0 END) / COUNT(*) AS decimal(4,1)),
       CAST(100.0 * SUM(CASE WHEN stage = 6 THEN 1 ELSE 0 END) / COUNT(*) AS decimal(4,1))
FROM s GROUP BY traffic_source
UNION ALL
SELECT 'route region', region, COUNT(*),
       CAST(100.0 * SUM(CASE WHEN stage >= 2 THEN 1 ELSE 0 END) / COUNT(*) AS decimal(4,1)),
       CAST(100.0 * SUM(CASE WHEN stage = 6 THEN 1 ELSE 0 END) / COUNT(*) AS decimal(4,1))
FROM s GROUP BY region
ORDER BY dimension, pct_converted DESC;

SELECT COUNT(*) AS abandoned_at_payment,
       SUM(CASE WHEN w.customer_id IS NOT NULL THEN 1 ELSE 0 END) AS identified_before_stitching,
       SUM(CASE WHEN k.source_id IS NOT NULL THEN 1 ELSE 0 END) AS identified_after_stitching,
       SUM(CASE WHEN c.marketing_consent = 1 THEN 1 ELSE 0 END) AS can_be_contacted
FROM src.web_sessions w
LEFT JOIN dw.customer_link k ON k.source_system = 'web' AND k.source_id = w.session_id
LEFT JOIN dw.dim_customer c ON c.customer_id = k.customer_id
WHERE TRY_CAST(LEFT(w.furthest_stage, 1) AS int) = 5;