USE airline_crm;
GO

WITH checks AS (
  -- COMPLETENESS
  SELECT 'loyalty'  AS source, 'phone missing' AS [check], SUM(CASE WHEN phone IS NULL THEN 1 ELSE 0 END) AS bad_rows, COUNT(*) AS total_rows FROM src.loyalty
  UNION ALL SELECT 'loyalty', 'address missing', SUM(CASE WHEN street_address IS NULL THEN 1 ELSE 0 END), COUNT(*) FROM src.loyalty
  UNION ALL SELECT 'bookings', 'no customer_id (guest booking)', SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END), COUNT(*) FROM src.bookings
  UNION ALL SELECT 'web_sessions', 'anonymous (no customer_id)', SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END), COUNT(*) FROM src.web_sessions
  UNION ALL SELECT 'service_contacts', 'no customer_id', SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END), COUNT(*) FROM src.service_contacts
  UNION ALL SELECT 'service_contacts', 'no survey score', SUM(CASE WHEN satisfaction_1_5 IS NULL THEN 1 ELSE 0 END), COUNT(*) FROM src.service_contacts
  -- UNIQUENESS: rows that sit in a group of 2+ people with the same name and birth date
  UNION ALL SELECT 'loyalty', 'suspected duplicate profiles (rows in groups)', ISNULL(SUM(n), 0), (SELECT COUNT(*) FROM src.loyalty)
    FROM (SELECT COUNT(*) AS n FROM src.loyalty GROUP BY first_name, last_name, birth_date HAVING COUNT(*) > 1) d
  UNION ALL SELECT 'customers', 'duplicate email', ISNULL(SUM(n), 0), (SELECT COUNT(*) FROM src.customers)
    FROM (SELECT COUNT(*) AS n FROM src.customers GROUP BY LOWER(email) HAVING COUNT(*) > 1) d
  -- VALIDITY
  UNION ALL SELECT 'customers', 'email not valid-looking', SUM(CASE WHEN email NOT LIKE '%_@_%._%' THEN 1 ELSE 0 END), COUNT(*) FROM src.customers
  UNION ALL SELECT 'customers', 'under 18 when account created', SUM(CASE WHEN DATEDIFF(year, birth_date, created_date) < 18 THEN 1 ELSE 0 END), COUNT(*) FROM src.customers
  UNION ALL SELECT 'bookings', 'email contains capitals', SUM(CASE WHEN contact_email COLLATE Latin1_General_100_BIN2 <> LOWER(contact_email) THEN 1 ELSE 0 END), COUNT(*) FROM src.bookings
  UNION ALL SELECT 'bookings', 'booked after the flight date', SUM(CASE WHEN booking_date > flight_date THEN 1 ELSE 0 END), COUNT(*) FROM src.bookings
  -- CONSISTENCY (references that point to nothing)
  UNION ALL SELECT 'bookings', 'flight_id not in flights', SUM(CASE WHEN f.flight_id IS NULL THEN 1 ELSE 0 END), COUNT(*)
    FROM src.bookings b LEFT JOIN src.flights f ON f.flight_id = b.flight_id
  UNION ALL SELECT 'web_sessions', 'booking_id not in bookings', SUM(CASE WHEN w.booking_id IS NOT NULL AND b.booking_id IS NULL THEN 1 ELSE 0 END), COUNT(*)
    FROM src.web_sessions w LEFT JOIN src.bookings b ON b.booking_id = w.booking_id
  UNION ALL SELECT 'bookings', 'customer_id not in customer master', SUM(CASE WHEN b.customer_id IS NOT NULL AND c.customer_id IS NULL THEN 1 ELSE 0 END), COUNT(*)
    FROM src.bookings b LEFT JOIN src.customers c ON c.customer_id = b.customer_id
  -- FRESHNESS
  UNION ALL SELECT 'customers', 'record never updated since creation', SUM(CASE WHEN last_updated_date = created_date THEN 1 ELSE 0 END), COUNT(*) FROM src.customers
)
SELECT source, [check], bad_rows, total_rows,
       CAST(100.0 * bad_rows / total_rows AS decimal(5,1)) AS pct_bad
FROM checks
ORDER BY pct_bad DESC;