USE airline_crm;
GO

CREATE OR ALTER VIEW dw.v_master AS
SELECT customer_id, first_name, last_name, birth_date,
       LOWER(first_name + ' ' + last_name) AS full_name,
       LOWER(TRIM(email)) AS email_lc,
       LEFT(LOWER(TRIM(email)), CHARINDEX('@', email) - 1) AS email_local,
       SUBSTRING(LOWER(TRIM(email)), CHARINDEX('@', email) + 1, 100) AS email_domain
FROM src.customers;
GO

CREATE OR ALTER VIEW dw.v_unlinked_contact AS
SELECT source_system, source_id, full_name, email_lc,
       LEFT(email_lc, CHARINDEX('@', email_lc) - 1) AS email_local,
       SUBSTRING(email_lc, CHARINDEX('@', email_lc) + 1, 100) AS email_domain
FROM (
    SELECT 'booking' AS source_system, booking_id AS source_id,
           LOWER(contact_first_name + ' ' + contact_last_name) AS full_name, LOWER(TRIM(contact_email)) AS email_lc
    FROM src.bookings WHERE customer_id IS NULL AND contact_email LIKE '%@%'
    UNION ALL
    SELECT 'service', contact_id, LOWER(contact_name), LOWER(TRIM(contact_email))
    FROM src.service_contacts WHERE customer_id IS NULL AND contact_email LIKE '%@%'
) u;
GO

DROP TABLE IF EXISTS dw.tally;
SELECT TOP (60) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS n INTO dw.tally FROM sys.all_objects;

DROP TABLE IF EXISTS dw.customer_link;
CREATE TABLE dw.customer_link (
    source_system varchar(20) NOT NULL,   -- loyalty / booking / service / web
    source_id     varchar(20) NOT NULL,   -- member_id, booking_id, contact_id, session_id
    customer_id   varchar(20) NOT NULL,
    match_rule    varchar(60) NOT NULL,   -- which rule made the link
    CONSTRAINT pk_customer_link PRIMARY KEY (source_system, source_id));
GO

---Records that already have a customer ID

INSERT INTO dw.customer_link
SELECT 'booking', booking_id, customer_id, 'given' FROM src.bookings WHERE customer_id IS NOT NULL;

INSERT INTO dw.customer_link
SELECT 'service', contact_id, customer_id, 'given' FROM src.service_contacts WHERE customer_id IS NOT NULL;

---Loyalty members
-- L1: same email
INSERT INTO dw.customer_link
SELECT 'loyalty', l.member_id, m.customer_id, 'L1 same email'
FROM src.loyalty l
JOIN dw.v_master m ON m.email_lc = LOWER(TRIM(l.email));

-- L2: same name and birth date, exactly one candidate
INSERT INTO dw.customer_link
SELECT 'loyalty', member_id, customer_id, 'L2 name + birth date'
FROM (
    SELECT l.member_id, m.customer_id,
           COUNT(*) OVER (PARTITION BY l.member_id) AS n_candidates
    FROM src.loyalty l
    JOIN dw.v_master m ON m.full_name = LOWER(l.first_name + ' ' + l.last_name)
                      AND m.birth_date = l.birth_date
    WHERE NOT EXISTS (SELECT 1 FROM dw.customer_link k
                      WHERE k.source_system = 'loyalty' AND k.source_id = l.member_id)
) x
WHERE n_candidates = 1;

---Bookings and service contacts that don't have a customer ID

-- U1: same email, ignoring capitals
INSERT INTO dw.customer_link
SELECT u.source_system, u.source_id, m.customer_id, 'U1 same email'
FROM dw.v_unlinked_contact u
JOIN dw.v_master m ON m.email_lc = u.email_lc;

-- U2: same name and email domain, and the typed email equals a master email with ONE letter deleted
INSERT INTO dw.customer_link
SELECT source_system, source_id, customer_id, 'U2 name + domain + one letter missing'
FROM (
    SELECT u.source_system, u.source_id, m.customer_id,
           COUNT(*) OVER (PARTITION BY u.source_system, u.source_id) AS n_candidates
    FROM dw.v_unlinked_contact u
    JOIN dw.v_master m ON m.full_name = u.full_name
                      AND m.email_domain = u.email_domain
                      AND LEN(m.email_local) = LEN(u.email_local) + 1
    WHERE NOT EXISTS (SELECT 1 FROM dw.customer_link k
                      WHERE k.source_system = u.source_system AND k.source_id = u.source_id)
      AND EXISTS (SELECT 1 FROM dw.tally t
                  WHERE t.n <= LEN(m.email_local)
                    AND STUFF(m.email_local, t.n, 1, '') = u.email_local)
) x
WHERE n_candidates = 1;
GO

---Linkage success rate
SELECT 'bookings without customer_id' AS what,
       COUNT(*) AS records,
       SUM(CASE WHEN k.source_id IS NOT NULL THEN 1 ELSE 0 END) AS linked,
       CAST(100.0 * SUM(CASE WHEN k.source_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1)) AS pct_linked
FROM src.bookings b
LEFT JOIN dw.customer_link k ON k.source_system = 'booking' AND k.source_id = b.booking_id
WHERE b.customer_id IS NULL
UNION ALL
SELECT 'service contacts without customer_id', COUNT(*),
       SUM(CASE WHEN k.source_id IS NOT NULL THEN 1 ELSE 0 END),
       CAST(100.0 * SUM(CASE WHEN k.source_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1))
FROM src.service_contacts s
LEFT JOIN dw.customer_link k ON k.source_system = 'service' AND k.source_id = s.contact_id
WHERE s.customer_id IS NULL
UNION ALL
SELECT 'loyalty members', COUNT(*),
       SUM(CASE WHEN k.source_id IS NOT NULL THEN 1 ELSE 0 END),
       CAST(100.0 * SUM(CASE WHEN k.source_id IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1))
FROM src.loyalty l
LEFT JOIN dw.customer_link k ON k.source_system = 'loyalty' AND k.source_id = l.member_id;

SELECT k.source_system, k.match_rule,
       COUNT(*) AS links,
       SUM(CASE WHEN k.customer_id = t.truth_customer_id THEN 1 ELSE 0 END) AS correct,
       CAST(100.0 * SUM(CASE WHEN k.customer_id = t.truth_customer_id THEN 1 ELSE 0 END) / COUNT(*) AS decimal(6,2)) AS accuracy_pct
FROM dw.customer_link k
JOIN (SELECT 'loyalty' AS s, member_id AS id, truth_customer_id FROM ans.loyalty_truth
      UNION ALL SELECT 'booking', booking_id, truth_customer_id FROM ans.bookings_truth
      UNION ALL SELECT 'service', contact_id, truth_customer_id FROM ans.service_truth) t
  ON t.s = k.source_system AND t.id = k.source_id
GROUP BY k.source_system, k.match_rule
ORDER BY k.source_system, k.match_rule;

---Duplicate loyalty profiles detection:
SELECT customer_id, COUNT(*) AS profiles, STRING_AGG(source_id, ', ') AS member_ids
FROM dw.customer_link
WHERE source_system = 'loyalty'
GROUP BY customer_id
HAVING COUNT(*) > 1;

-- found versus planted
SELECT (SELECT COUNT(*) FROM (SELECT customer_id FROM dw.customer_link WHERE source_system = 'loyalty'
                              GROUP BY customer_id HAVING COUNT(*) > 1) d) AS duplicates_found,
       (SELECT SUM(CAST(is_duplicate_profile AS int)) FROM ans.loyalty_truth) AS duplicates_planted;


---Loyalty addresses vs master addresses:
SELECT COUNT(*) AS linked_members_with_address,
       SUM(CASE WHEN l.city <> m.city OR l.street_address <> m.street_address THEN 1 ELSE 0 END) AS address_differs,
       CAST(100.0 * SUM(CASE WHEN l.city <> m.city OR l.street_address <> m.street_address THEN 1 ELSE 0 END) / COUNT(*) AS decimal(5,1)) AS pct_differs
FROM src.loyalty l
JOIN dw.customer_link k ON k.source_system = 'loyalty' AND k.source_id = l.member_id
JOIN src.customers m ON m.customer_id = k.customer_id
WHERE l.street_address IS NOT NULL;