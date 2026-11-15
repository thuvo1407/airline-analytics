"""
Everything generated is SYNTHETIC (fictional airline, fictional customers).
"""

#Reproducibility
RANDOM_SEED = 42    # same seed = same data every run

#Time window shared by ALL tables
START_DATE = "2023-01-01"
END_DATE = "2026-10-31"

#Customers
N_CUSTOMERS = 10_000
CUSTOMER_SINCE = "2010-01-01"         # earliest possible account creation date
COUNTRY_WEIGHTS = {                   # must sum to 1.0; Finland is the home market
    "Finland": 0.40, "Sweden": 0.10, "Germany": 0.12, "United Kingdom": 0.12,
    "France": 0.09, "Netherlands": 0.06, "Spain": 0.06, "Italy": 0.05,
}
NEVER_UPDATED_RATE = 0.35
MARKETING_CONSENT_RATE = 0.60

#Source system volumes (Project 1)
N_BOOKINGS = 50_000                   # a sample of tickets, each linked to a real flight
N_LOYALTY_MEMBERS = 6_500
N_WEB_SESSIONS = 60_000
N_SERVICE_CONTACTS = 6_000

#Data quality problems: customer systems (Project 1) 
MISSING_PHONE_RATE = 0.20
MISSING_ADDRESS_RATE = 0.12
DUPLICATE_PROFILE_RATE = 0.03
STALE_ADDRESS_RATE = 0.15
UNLINKED_BOOKING_RATE = 0.08
ANONYMOUS_SESSION_RATE = 0.55
UNLINKED_SERVICE_RATE = 0.10

#Data quality problems: flight extract (Project 2) 
FLIGHT_DELAY_CAUSE_VARIANT_RATE = 0.12   # delay cause typed in a different way
FLIGHT_DELAY_CAUSE_MISSING_RATE = 0.06   # delay cause left blank
FLIGHT_AIRCRAFT_LABEL_VARIANT_RATE = 0.08
FLIGHT_DUPLICATE_ROW_RATE = 0.0025
FLIGHT_PAX_OVER_SEATS_RATE = 0.0015
FLIGHT_MISSING_DELAY_RATE = 0.005