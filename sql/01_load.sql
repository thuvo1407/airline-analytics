USE airline_crm;
GO

DROP TABLE IF EXISTS stg.customers, stg.bookings, stg.loyalty, stg.web, stg.service, stg.flights,
                     stg.loyalty_truth, stg.bookings_truth, stg.web_truth, stg.service_truth;

CREATE TABLE stg.customers (customer_id varchar(20), first_name varchar(100), last_name varchar(100),
    email varchar(200), phone varchar(60), birth_date varchar(20), gender varchar(5), country varchar(60),
    city varchar(100), street_address varchar(300), postal_code varchar(30), preferred_language varchar(5),
    marketing_consent varchar(5), created_date varchar(20), last_updated_date varchar(20));

CREATE TABLE stg.bookings (booking_id varchar(20), customer_id varchar(20), contact_first_name varchar(100),
    contact_last_name varchar(100), contact_email varchar(200), flight_id varchar(30), flight_date varchar(20),
    booking_date varchar(20), fare_class varchar(20), channel varchar(30), fare_eur varchar(20),
    ancillary_eur varchar(20), booking_status varchar(30));

CREATE TABLE stg.loyalty (member_id varchar(20), first_name varchar(100), last_name varchar(100),
    email varchar(200), phone varchar(60), country varchar(60), city varchar(100), street_address varchar(300),
    postal_code varchar(30), birth_date varchar(20), tier varchar(20), points_balance varchar(20),
    enrolled_date varchar(30));

CREATE TABLE stg.web (session_id varchar(20), session_start varchar(30), customer_id varchar(20),
    device_id varchar(30), device_type varchar(20), traffic_source varchar(30), searched_route_id varchar(20),
    furthest_stage varchar(30), booking_id varchar(20));

CREATE TABLE stg.service (contact_id varchar(20), contact_date varchar(20), customer_id varchar(20),
    contact_name varchar(200), contact_email varchar(200), channel varchar(30), topic varchar(50),
    booking_id varchar(20), flight_id varchar(30), resolution_hours varchar(20), satisfaction_1_5 varchar(10));

CREATE TABLE stg.flights (flight_id varchar(30), flight_date varchar(20), flight_number varchar(10),
    route_id varchar(20), origin varchar(5), destination varchar(5), region varchar(30), direction varchar(5),
    aircraft_type varchar(20), seats varchar(10), sched_dep_hour varchar(5), cancelled varchar(5),
    cancel_reason varchar(50), arr_delay_min varchar(20), delay_cause varchar(60), pax_boarded varchar(10),
    partner_codeshare_pax varchar(10), gc_km varchar(10), flown_km varchar(10), pass_revenue_eur varchar(20),
    ancillary_revenue_eur varchar(20), cargo_tonnes varchar(20), cargo_revenue_eur varchar(20),
    fuel_burn_t varchar(20), co2_t varchar(20));

CREATE TABLE stg.loyalty_truth  (member_id varchar(20), truth_customer_id varchar(20), is_duplicate_profile varchar(5));
CREATE TABLE stg.bookings_truth (booking_id varchar(20), truth_customer_id varchar(20));
CREATE TABLE stg.web_truth      (session_id varchar(20), truth_customer_id varchar(20));
CREATE TABLE stg.service_truth  (contact_id varchar(20), truth_customer_id varchar(20));
GO

-- load: FIRSTROW=2 skips the header, KEEPNULLS keeps empty cells as NULL, FIELDQUOTE handles "a, b" addresses
BULK INSERT stg.customers FROM '/data/raw/customers_master.csv'
  WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', FIELDTERMINATOR=',', ROWTERMINATOR='0x0a', KEEPNULLS, TABLOCK);
BULK INSERT stg.bookings FROM '/data/raw/bookings.csv'
  WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', FIELDTERMINATOR=',', ROWTERMINATOR='0x0a', KEEPNULLS, TABLOCK);
BULK INSERT stg.loyalty FROM '/data/raw/loyalty_members.csv'
  WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', FIELDTERMINATOR=',', ROWTERMINATOR='0x0a', KEEPNULLS, TABLOCK);
BULK INSERT stg.web FROM '/data/raw/web_sessions.csv'
  WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', FIELDTERMINATOR=',', ROWTERMINATOR='0x0a', KEEPNULLS, TABLOCK);
BULK INSERT stg.service FROM '/data/raw/service_contacts.csv'
  WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', FIELDTERMINATOR=',', ROWTERMINATOR='0x0a', KEEPNULLS, TABLOCK);
BULK INSERT stg.flights FROM '/data/raw/flights_reference.csv'
  WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', FIELDTERMINATOR=',', ROWTERMINATOR='0x0a', KEEPNULLS, TABLOCK);

BULK INSERT stg.loyalty_truth FROM '/data/answer_key/loyalty_truth.csv'
  WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', FIELDTERMINATOR=',', ROWTERMINATOR='0x0a', KEEPNULLS, TABLOCK);
BULK INSERT stg.bookings_truth FROM '/data/answer_key/bookings_truth.csv'
  WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', FIELDTERMINATOR=',', ROWTERMINATOR='0x0a', KEEPNULLS, TABLOCK);
BULK INSERT stg.web_truth FROM '/data/answer_key/web_sessions_truth.csv'
  WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', FIELDTERMINATOR=',', ROWTERMINATOR='0x0a', KEEPNULLS, TABLOCK);
BULK INSERT stg.service_truth FROM '/data/answer_key/service_contacts_truth.csv'
  WITH (FORMAT='CSV', FIRSTROW=2, FIELDQUOTE='"', FIELDTERMINATOR=',', ROWTERMINATOR='0x0a', KEEPNULLS, TABLOCK);
GO

DROP TABLE IF EXISTS src.customers, src.bookings, src.loyalty, src.web_sessions, src.service_contacts, src.flights,
                     ans.loyalty_truth, ans.bookings_truth, ans.web_truth, ans.service_truth;

SELECT customer_id, first_name, last_name, email, phone,
       TRY_CAST(birth_date AS date) AS birth_date, gender, country, city, street_address, postal_code,
       preferred_language, TRY_CAST(marketing_consent AS bit) AS marketing_consent,
       TRY_CAST(created_date AS date) AS created_date, TRY_CAST(last_updated_date AS date) AS last_updated_date
INTO src.customers FROM stg.customers;

SELECT booking_id, customer_id, contact_first_name, contact_last_name, contact_email, flight_id,
       TRY_CAST(flight_date AS date) AS flight_date, TRY_CAST(booking_date AS date) AS booking_date,
       fare_class, channel, TRY_CAST(fare_eur AS decimal(10,2)) AS fare_eur,
       TRY_CAST(ancillary_eur AS decimal(10,2)) AS ancillary_eur, booking_status
INTO src.bookings FROM stg.bookings;

SELECT member_id, first_name, last_name, email, phone, country, city, street_address, postal_code,
       TRY_CAST(birth_date AS date) AS birth_date, tier, TRY_CAST(points_balance AS int) AS points_balance,
       TRY_CAST(enrolled_date AS date) AS enrolled_date
INTO src.loyalty FROM stg.loyalty;

SELECT session_id, TRY_CAST(session_start AS datetime2(0)) AS session_start, customer_id, device_id,
       device_type, traffic_source, searched_route_id, furthest_stage, booking_id
INTO src.web_sessions FROM stg.web;

SELECT contact_id, TRY_CAST(contact_date AS date) AS contact_date, customer_id, contact_name, contact_email,
       channel, topic, booking_id, flight_id, TRY_CAST(resolution_hours AS decimal(6,1)) AS resolution_hours,
       TRY_CAST(TRY_CAST(satisfaction_1_5 AS decimal(3,1)) AS tinyint) AS satisfaction_1_5
INTO src.service_contacts FROM stg.service;

SELECT flight_id, TRY_CAST(flight_date AS date) AS flight_date, flight_number, route_id, origin, destination,
       region, direction, TRY_CAST(seats AS int) AS seats, TRY_CAST(cancelled AS bit) AS cancelled,
       TRY_CAST(arr_delay_min AS decimal(8,1)) AS arr_delay_min, delay_cause,
       TRY_CAST(pax_boarded AS int) AS pax_boarded
INTO src.flights FROM stg.flights;

SELECT member_id, truth_customer_id, TRY_CAST(is_duplicate_profile AS bit) AS is_duplicate_profile
INTO ans.loyalty_truth FROM stg.loyalty_truth;
SELECT * INTO ans.bookings_truth FROM stg.bookings_truth;
SELECT * INTO ans.web_truth      FROM stg.web_truth;
SELECT * INTO ans.service_truth  FROM stg.service_truth;
GO

-- primary keys: they also make later joins fast
ALTER TABLE src.customers        ALTER COLUMN customer_id varchar(20) NOT NULL;
ALTER TABLE src.bookings         ALTER COLUMN booking_id  varchar(20) NOT NULL;
ALTER TABLE src.loyalty          ALTER COLUMN member_id   varchar(20) NOT NULL;
ALTER TABLE src.web_sessions     ALTER COLUMN session_id  varchar(20) NOT NULL;
ALTER TABLE src.service_contacts ALTER COLUMN contact_id  varchar(20) NOT NULL;
ALTER TABLE src.flights          ALTER COLUMN flight_id   varchar(30) NOT NULL;
GO
ALTER TABLE src.customers        ADD CONSTRAINT pk_customers PRIMARY KEY (customer_id);
ALTER TABLE src.bookings         ADD CONSTRAINT pk_bookings  PRIMARY KEY (booking_id);
ALTER TABLE src.loyalty          ADD CONSTRAINT pk_loyalty   PRIMARY KEY (member_id);
ALTER TABLE src.web_sessions     ADD CONSTRAINT pk_web       PRIMARY KEY (session_id);
ALTER TABLE src.service_contacts ADD CONSTRAINT pk_service   PRIMARY KEY (contact_id);
ALTER TABLE src.flights          ADD CONSTRAINT pk_flights   PRIMARY KEY (flight_id);
GO