1. Customer: one real person with one customer_id in the customer master.
2. Customer master: the reference list of 10000 customers, the source for name, birth dates, gender, address, language, and marketing consent.
3. Golden record: the single trusted row per customer in dw.dim_customer, built from the master plus linked loyalty, booking, web and service data.
4. Record linkage: deciding that records from different systems describe the same customer when they do not share a reliable ID.
5. Match rule: one test used to link records (i.e "same email"), every link stores its rule.
6. Duplicate profile: two loyalty members that can be linked to the same customer.
7. Anonymous session: a web visit with no logged-in customer.
8. Answer key: a hidden table of the true customer behind every record (ans.* tables). Only used to grade linking accuracy, never for analysis.
9. Unlinked record: a booking, service contact or web session without a customer_id in the source system.
10. 'given': the source system already supplied the customer_id.
11. 'L1 same email': a loyalty member's email, ignoring capitals, equals a master email.
12. 'L2 name + birth date': a loyalty member has the same name and birthday as exactly one master customer. This catches a duplicate profile whose email changes.
13. 'U1 same email': an unlinked booking's or service contact's email, ignoring capitals, equals a master email.
14. 'U2 name + domain + one letter missing': same full name and email domain, and the typed email equals a master email with exactly one letter deleted, with a single candidate.
15. 'W2 via booking': an anonymous web session that ended in a booking inherits the booking's customer.
16. 'W3 device seen with one customer': an anonymous session on a device that has been seen with exactly one known customer is assigned to that customer.
17. Conversion rate: sessions that reached a step divided by sessions that started the funnel.
18. Payment abandonment: a session whose furthest stage is 5, the payment page, with no confirmed booking.
19. Traffic source: how the visitor arrived: Direct, Organic search, Paid search, Email campaign, Metasearch or Social.
20. Booking status: Flown, No-show, or Flight cancelled.
21. Revenue: fare plus ancillary spend on a booking with status Flown. Cancelled and no-show bookings are excluded.
22. Region: the flight's route group: Asia, North Atlantic, Europe, Middle East or Domestic.
23. Long-haul: flights to Asia or North Atlantic in this project.
24. Active customer: a customer who flew at least once in the 12 months up to 31 October 2026.
25. Recency (R): days since the customer's last flown booking. A lower number scores higher.
26. Frequency (F): number of flown bookings. The data is a sample of tickets, so this understates real flying.
27. Monetary (M): total revenue from flown bookings.
28. RFM score: recency and monetary are scored 1 to 5 by quintile. Frequency uses fixed bands: 1 flight = 1, 2 to 3 = 2, 4 to 6 = 3, 7 to 12 = 4, 13 or more = 5.
29. Cohort: customers grouped by the quarter of their first flight. Only customers created on or after 1 January 2023 are included, so the first flight in the data is close to their first flight.
30. Retention: the share of a cohort that flies again in a later quarter.

