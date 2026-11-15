Airline Customer Data Foundation & Analytics

Customer data audit, record linkage, RFM segmentation, cohort retention and booking funnel analysis for a fictional airline, built in Python and SQL Server.

About the data:
All data in this project is synthetic. The airline "Nordic Horizon Airways" is fictional. Its headline figures were calibrated against figures several Finnish public reports to achieve a realistic shape. I used AI to assist with writing the Python generator scripts and developing the matching rules. I design the data problems and the analysis myself.

Business question:
1. Can we trust the customer data held in five different systems?
2. Which customers are valuable, and which valuable customers are slipping away?
3. Where do we lose bookings online, and can we reach those customers?
4. Does a bad flight experience drive customer service contacts?

What is in the data
Generated with the scripts in python/, seeded so the result is identical every run.

- Customer master: 10,000 customers, the reference list.
- Flights: 112,590 flights on 28 routes, January 2023 to October 2026, with dates, regions, delays and cancellations.
- Bookings: 50,000 tickets, each linked to a real flight. About 8% have no customer ID.
- Loyalty members: 6,695 rows. 195 people are enrolled twice, and some details are missing or outdated.
- Web sessions: 60,000 visits. 55% are anonymous, and each follows a six-step booking funnel.
- Service contacts: 6,000 cases, often about delayed or cancelled flights. About 10% have no customer ID.

I also kept a hidden answer key (the true customer behind every record) so I could measure how accurate my linking was. It is only used to grade results, never to do the analysis.

What I did
- Load (sql/01_load.sql): got five CSV exports into SQL Server safely, using staging tables first and typed tables second.
- Audit (sql/02_audit.sql): measured how bad the data is. 
- Linking (sql/03_matching.sql): linked 100% of unlinked bookings and service contacts to a customer, with 100% accuracy against the answer key.
- Golden record (sql/04_golden.sql): built dim_customer and fact_booking, one trusted row per customer and per booking, plus a glossary.
- RFM (sql/05_rfm.sql): scored customers on recency, frequency and monetary value. 
- Cohorts (sql/06_cohorts.sql): measured whether first-time flyers come back. 
- Funnel (sql/07_funnel.sql): found where bookings drop out. About 37% of sessions that reach the payment page do not finish. 
- Service (sql/08_service.sql): linked service contacts to flight disruption.

Record linkage rules

Each rule only links a record when it finds exactly one candidate. Every link stores which rule created it.
- Loyalty: same email; same name and birth date (this catches the duplicate profiles).
- Bookings and service contacts without a customer ID: same email ignoring capitals; same name and email domain with one letter missing.
- Web sessions: logged in; the session ended in a known customer's booking; the same device was seen with exactly one known customer.

Key findings:
- Identity resolution recovered 8.1% of revenue. Before linking, 3874 bookings (7.7%) had no customer_id. Linkage (U1/U2) resolved 100% of them at 100% accuracy against the answer key, attributing €912880 in flown revenue and uncovering all 195 duplicate loyalty profiles.
- Champions (18.6% of flyers) account for 50.8% of total flown revenue (€5.76M), while Hibernating flyers make up 37.1% of the base but only 14.3% of revenue. Meanwhile 232 At-risk flyers (€477K revenue) represent high-value win-back targets (60.3% have marketing consent).
- Payment abandonment is the biggest late-funnel loss. 37.4% of sessions reaching the payment page (4300 of 11500) failed to confirm a booking. Device and booking stitching (W2/W3) raised identified web sessions from 44.9% to 84%, nearly doubling reachable payment-abandoners from 1,888 to 3,495 (2,120 contactable with consent).
- 76.6% of loyalty members flew again within 4 quarters compared to 38.8% of non-members; However, the generator picks loyalty members in proportion to how often they fly, so this does not show that the programme causes retention. Across all repeat flyers (6387 customers), the median time to a second flight is 138 days.
- Cancelled flights triggered 624.8 service contacts per 1000 bookings with a 2.73 average satisfaction score, compared to 91.3 contacts per 1000 and 3.85 satisfaction for on-time flights—making proactive disruption outreach critical for VIP retention.

How to reproduce

Requires Python 3, Docker and VS Code with the SQL Server (mssql) extension.


python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python python/generate_network.py
python python/generate_customers.py
python python/generate_bookings.py
python python/generate_customer_sources.py
python python/generate_flight_extract.py
python python/calibration_check.py

Copy two files under their working names, then start SQL Server and run the SQL files in order (sql/00_setup.sql to sql/08_service.sql):

cp data/answer_key/customers_truth.csv data/raw/customers_master.csv
cp data/answer_key/flights_truth.csv data/raw/flights_reference.csv

docker run --platform linux/amd64 \
  -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=<choose-a-strong-password>" \
  -p 1433:1433 --name sqlserver \
  -v "$(pwd)/data:/data:ro" -v sqlserver_data:/var/opt/mssql \
  -d mcr.microsoft.com/mssql/server:2022-latest

Documentation

- documentation/glossary.md: definitions used in this project
- documentation/data_quality_finds: the audit findings
- documentation/results/: screenshots of key results

Limitations
- The data is synthetic and the errors are simple, so 100% matching accuracy is not realistic. 
- The booking data is a sample of tickets, so customer "frequency" is understated.
- Retention is roughly flat because the generator does not model customers drifting away.
- Customer segments do not differ much in behaviour, because the generator did not make them differ.


