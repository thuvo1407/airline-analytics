"""
STEP 4: Create ~50,000 bookings. Every booking is for a REAL flight from Step 2
and a REAL customer from Step 3.

Outputs
  data/raw/bookings.csv                  what the booking system exports (some customer_ids are blank)
  data/answer_key/bookings_truth.csv     booking_id -> the real customer (for grading the matching)
"""
from pathlib import Path

import numpy as np
import pandas as pd

from config import RANDOM_SEED, N_BOOKINGS, UNLINKED_BOOKING_RATE

rng = np.random.default_rng(RANDOM_SEED + 30)

ROOT = Path(__file__).resolve().parent.parent
KEY_DIR = ROOT / "data" / "answer_key"
RAW_DIR = ROOT / "data" / "raw"

FARE_MULT = {"Light": 0.85, "Classic": 1.00, "Flex": 1.45, "Business": 3.20}
CHANNELS = ["Web", "App", "Travel agency", "Call center"]
CHANNEL_P = [0.50, 0.25, 0.20, 0.05]


def mangle_email(email):
    """Guest bookings re-type the email: sometimes in capitals, sometimes with a typo."""
    r = rng.random()
    if r < 0.70:
        return email
    if r < 0.90:
        return email.upper()
    local, domain = email.split("@")
    i = int(rng.integers(1, max(len(local) - 1, 2)))
    return local[:i] + local[i + 1:] + "@" + domain          # one letter dropped


def main():
    flights = pd.read_csv(KEY_DIR / "flights_truth.csv", parse_dates=["flight_date"])
    cust = pd.read_csv(KEY_DIR / "customers_truth.csv", parse_dates=["created_date"])

    # busier flights get more bookings; cancelled flights still had bookings
    weight = np.where(flights["cancelled"] == 1, flights["seats"] * 0.75, flights["pax_boarded"]).astype(float)
    fl_idx = rng.choice(len(flights), N_BOOKINGS, p=weight / weight.sum())
    f = flights.iloc[fl_idx].reset_index(drop=True)

    # some customers fly a lot, most rarely
    cust_w = rng.lognormal(0, 1.0, len(cust))
    cust_w /= cust_w.sum()
    created = cust["created_date"].to_numpy()
    flight_dates = f["flight_date"].to_numpy()
    cust_idx = rng.choice(len(cust), N_BOOKINGS, p=cust_w)
    for _ in range(30):      # a customer cannot book before their account exists
        bad = created[cust_idx] > flight_dates - np.timedelta64(1, "D")
        if not bad.any():
            break
        cust_idx[bad] = rng.choice(len(cust), bad.sum(), p=cust_w)
    bad = created[cust_idx] > flight_dates - np.timedelta64(1, "D")
    cust_idx[bad] = int(np.argmin(created))                          # fallback: oldest customer
    c = cust.iloc[cust_idx].reset_index(drop=True)

    # when was it booked? long-haul books earlier
    long_haul = f["region"].isin(["Asia", "North Atlantic", "Middle East"]).to_numpy()
    lead = np.where(long_haul, rng.gamma(2.2, 40, N_BOOKINGS), rng.gamma(1.8, 18, N_BOOKINGS)).astype(int) + 1
    booking_date = f["flight_date"] - pd.to_timedelta(lead, unit="D")
    booking_date = booking_date.where(booking_date >= c["created_date"], c["created_date"])
    booking_date = booking_date.where(booking_date <= f["flight_date"] - pd.Timedelta(days=1), f["flight_date"] - pd.Timedelta(days=1))

    # fare class and price
    fare_class = np.where(long_haul,
                          rng.choice(["Light", "Classic", "Flex", "Business"], N_BOOKINGS, p=[0.30, 0.40, 0.18, 0.12]),
                          rng.choice(["Light", "Classic", "Flex"], N_BOOKINGS, p=[0.45, 0.40, 0.15]))
    avg_fare = (f["pass_revenue_eur"] / f["pax_boarded"].replace(0, np.nan)).fillna(f["gc_km"] * 0.08).to_numpy()
    fare = np.round(avg_fare * np.array([FARE_MULT[x] for x in fare_class]) * rng.lognormal(0, 0.15, N_BOOKINGS), 2)
    avg_anc = (f["ancillary_revenue_eur"] / f["pax_boarded"].replace(0, np.nan)).fillna(15).to_numpy()
    ancillary = np.round(avg_anc * rng.lognormal(0, 0.6, N_BOOKINGS) * (rng.random(N_BOOKINGS) < 0.55), 2)

    status = np.where(f["cancelled"] == 1, "Flight cancelled",
                      np.where(rng.random(N_BOOKINGS) < 0.02, "No-show", "Flown"))
    channel = rng.choice(CHANNELS, N_BOOKINGS, p=CHANNEL_P)

    # the data problem: some bookings come through without a customer id (guest checkout)
    unlinked = rng.random(N_BOOKINGS) < UNLINKED_BOOKING_RATE
    contact_email = [mangle_email(e) if u else e for e, u in zip(c["email"], unlinked)]

    raw = pd.DataFrame({
        "booking_id": [f"B{i + 1:07d}" for i in range(N_BOOKINGS)],
        "customer_id": np.where(unlinked, None, c["customer_id"]),
        "contact_first_name": c["first_name"], "contact_last_name": c["last_name"],
        "contact_email": contact_email,
        "flight_id": f["flight_id"], "flight_date": f["flight_date"].dt.date,
        "booking_date": booking_date.dt.date, "fare_class": fare_class, "channel": channel,
        "fare_eur": fare, "ancillary_eur": ancillary, "booking_status": status,
    })
    truth = pd.DataFrame({"booking_id": raw["booking_id"], "truth_customer_id": c["customer_id"]})

    # checks
    assert raw["booking_id"].is_unique
    assert raw["flight_id"].isin(flights["flight_id"]).all(), "booking points to a flight that does not exist"
    assert (booking_date <= f["flight_date"]).all(), "booked after the flight"
    assert (booking_date >= c["created_date"]).all(), "booked before the account existed"
    print("\nAll validation checks passed.")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw.to_csv(RAW_DIR / "bookings.csv", index=False)
    truth.to_csv(KEY_DIR / "bookings_truth.csv", index=False)

    print(f"\nBookings: {len(raw):,}   Without customer_id: {raw['customer_id'].isna().mean():.1%}")
    print(f"Customers with at least one booking: {c['customer_id'].nunique():,} of {len(cust):,}")
    print("\nBookings by fare class:")
    print(raw["fare_class"].value_counts().to_string())
    print("\nBookings by status:")
    print(raw["booking_status"].value_counts().to_string())
    print("\nFirst 3 bookings:")
    print(raw.head(3).to_string())
    print("\nSaved bookings.csv to data/raw, bookings_truth.csv to data/answer_key")


if __name__ == "__main__":
    main()