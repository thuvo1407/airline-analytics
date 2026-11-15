This md summarizes the data quality audit results conducted on the simulated airline warehouse ('airline_crm) to assess data accuract and cross-system consistency before analysis.

##1 Dataset overview 
Total records loaded:
*'customers': 10000 records
*'bookings': 50000 records
*'loyalty': 6695 records
*'service_contacts': 60000 records
*'flights': 112590 records
A scan across mandatory fields such as 'booking_date', 'flight_date', 'fare_eur', 'birth_date', 'session_start', 'seats' recorded zero (0) invalid/null values ('bad_bookings' = 0, 'bad_customer' = 0, 'bad_flights' = 0). This implies the raw data complies well with initial formatting constraints.

##2 Customer linkage: A major challenge is linking fragmented transactions ('bookings', 'service_contacts') to standard customer profiles in the data warehouse 'dw.customer_link'.

*Loyalty members:

**Rule L1 - Same email: matches ignoring case differences against a master customer's email.
**Rule L2 - Name+birthday: matches identical first/last names and birth dates with a single candidate, successfully identifying duplicate profiles where emails were modified.

*Bookings & service contacts:

**Rule U1 - Same email: matches emails ignoring case differences to master emails;
**Rule U2 - Name + domain + one letter issing: natches full names and email domains where the typed email equals a master email with exactly one letter deleted (catching potential typos)

*Web sessions:

**Rule W1 - given: sessions where visitors were logged in and already possessed a customer ID.
**Rule W2 - via booking: sessions that concluded in a booking tied to a known customer.
**Rule W3 - device seen with one customer: the same device ID was seen with exactly one know customer, so its anonymous sessions are assigned to that same person.

##3 Linkage success result: 
Previously unlinked records from source systems were successfully resolved and linked at 100%:
*'bookings without customer_id': 4030/4030 successfully linked
*'service contacts without customer_id': 619/619 successfully linked
By Booking channels:
*Total bookings across channels: web 25066, app 12518, travel agency 9899, call center 2517.
*Unlink customer rates pct_unlinked remained stable between 7.9% and 8.4% across channels.
By Web sessions & Device types:
*Device distribution: Mobile 34873, Desktop 20980, Tablet 4147
*Anonymous session rates pct_anonymous accounted for ~55% across all devices.

##4 Duplicate profile detection: 195/195 planted duplicates detected.

##5 Cross-source data consistency:
By comparing address information between 'src.loyalty' and 'src.customers' via 'dw.customer_link', it was discovered that out of 5902 linked members with addresses, 879 (14.9%) showed differences in registered cities or street addresses.