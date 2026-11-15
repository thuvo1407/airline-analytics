"""
Step 5: Create the three remaining customer systems, all built from the same
customers (Step 3), bookings (Step 4) and flights (Step 2):

  1. loyalty_members.csv    the loyalty programme (duplicates, missing and outdated details)
  2. web_sessions.csv       website/app visits with a booking funnel (many anonymous)
  3. service_contacts.csv   customer service cases (often about delayed/cancelled flights)

Raw exports go to data/raw. The real answers go to data/answer_key.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

from config import (RANDOM_SEED, START_DATE, END_DATE, N_LOYALTY_MEMBERS, N_WEB_SESSIONS,
                    N_SERVICE_CONTACTS, MISSING_PHONE_RATE, MISSING_ADDRESS_RATE,
                    DUPLICATE_PROFILE_RATE, STALE_ADDRESS_RATE, ANONYMOUS_SESSION_RATE,
                    UNLINKED_SERVICE_RATE)

rng = np.random.default_rng(RANDOM_SEED + 40)
Faker.seed(RANDOM_SEED + 40)
LOCALE = {"Finland": "fi_FI", "Sweden": "sv_SE", "Germany": "de_DE", "United Kingdom": "en_GB",
          "France": "fr_FR", "Netherlands": "nl_NL", "Spain": "es_ES", "Italy": "it_IT"}
fakers = {c: Faker(l) for c, l in LOCALE.items()}

ROOT = Path(__file__).resolve().parent.parent
KEY_DIR = ROOT / "data" / "answer_key"
PROC_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"
END = pd.Timestamp(END_DATE)
START = pd.Timestamp(START_DATE)


def load():
    cust = pd.read_csv(KEY_DIR / "customers_truth.csv", parse_dates=["created_date"],
                       dtype={"postal_code": str, "phone": str})
    bookings = pd.read_csv(RAW_DIR / "bookings.csv", parse_dates=["flight_date", "booking_date"])
    btruth = pd.read_csv(KEY_DIR / "bookings_truth.csv")
    bookings = bookings.merge(btruth, on="booking_id")
    flights = pd.read_csv(KEY_DIR / "flights_truth.csv", parse_dates=["flight_date"])
    routes = pd.read_csv(PROC_DIR / "routes.csv")
    return cust, bookings, flights, routes


def mangle_email(email):
    r = rng.random()
    if r < 0.70:
        return email
    if r < 0.90:
        return email.upper()
    local, domain = email.split("@")
    i = int(rng.integers(1, max(len(local) - 1, 2)))
    return local[:i] + local[i + 1:] + "@" + domain


def random_dates(start, end, n):
    """Random dates between two arrays/scalars of timestamps."""
    start = np.broadcast_to(np.asarray(start, dtype="datetime64[D]"), n)
    end = np.broadcast_to(np.asarray(end, dtype="datetime64[D]"), n)
    span = (end - start).astype(int)
    return start + (rng.random(n) * (span + 1)).astype(int).astype("timedelta64[D]")


# ---------------------------------------------------------------------------
def build_loyalty(cust, bookings):
    flown = bookings[bookings["booking_status"] == "Flown"]
    n_flown = flown.groupby("truth_customer_id").size().reindex(cust["customer_id"]).fillna(0).to_numpy()
    spend = flown.groupby("truth_customer_id")["fare_eur"].sum().reindex(cust["customer_id"]).fillna(0).to_numpy()
    p = 0.3 + n_flown                                           # frequent flyers join more often
    pick = rng.choice(len(cust), N_LOYALTY_MEMBERS, replace=False, p=p / p.sum())
    c = cust.iloc[pick].reset_index(drop=True)
    n_f, sp = n_flown[pick], spend[pick]

    tier = np.select([n_f >= 25, n_f >= 12, n_f >= 5], ["Platinum", "Gold", "Silver"], "Basic")
    enrol = random_dates(c["created_date"].to_numpy(), np.datetime64(END_DATE), len(c))
    points = np.round(sp * 2 * rng.uniform(0.3, 1.0, len(c))).astype(int)

    rows = pd.DataFrame({
        "first_name": c["first_name"], "last_name": c["last_name"], "email": c["email"],
        "phone": c["phone"], "country": c["country"], "city": c["city"],
        "street_address": c["street_address"], "postal_code": c["postal_code"],
        "birth_date": c["birth_date"], "tier": tier, "points_balance": points, "enrolled_date": enrol,
        "truth_customer_id": c["customer_id"], "is_duplicate_profile": 0,
    })

    # problem 1: outdated address (the customer moved, the loyalty system never heard)
    stale = np.where(rng.random(len(rows)) < STALE_ADDRESS_RATE)[0]
    for i in stale:
        fk = fakers[rows.at[i, "country"]]
        rows.at[i, "city"], rows.at[i, "street_address"], rows.at[i, "postal_code"] = (
            fk.city(), fk.street_address().replace("\n", ", "), fk.postcode())

    # problem 2: the same person signed up twice (different email, newer enrolment)
    dup = rows.sample(frac=DUPLICATE_PROFILE_RATE, random_state=RANDOM_SEED).copy()
    dup["email"] = [e.split("@")[0].rstrip("0123456789") + "@" + rng.choice(["gmail.com", "outlook.com", "icloud.com"])
                    for e in dup["email"]]
    dup["enrolled_date"] = rows.loc[dup.index, "enrolled_date"] + pd.to_timedelta(rng.integers(30, 800, len(dup)), unit="D")
    dup["enrolled_date"] = dup["enrolled_date"].clip(upper=END)
    dup["tier"], dup["points_balance"], dup["is_duplicate_profile"] = "Basic", 0, 1
    rows = pd.concat([rows, dup], ignore_index=True)

    # problem 3: missing phone and address
    rows.loc[rng.random(len(rows)) < MISSING_PHONE_RATE, "phone"] = None
    miss = rng.random(len(rows)) < MISSING_ADDRESS_RATE
    rows.loc[miss, ["street_address", "postal_code", "city"]] = None

    rows = rows.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)
    rows.insert(0, "member_id", [f"M{i + 1:06d}" for i in range(len(rows))])
    truth = rows[["member_id", "truth_customer_id", "is_duplicate_profile"]]
    return rows.drop(columns=["truth_customer_id", "is_duplicate_profile"]), truth


# ---------------------------------------------------------------------------
def build_web(cust, bookings, routes):
    n = N_WEB_SESSIONS
    cust_ids = cust["customer_id"].to_numpy()
    created = cust.set_index("customer_id")["created_date"]

    # each person uses 1-3 devices; the device id (a cookie) is how anonymous visits can be stitched
    devices = {cid: [f"dev_{rng.integers(16**8):08x}" for _ in range(rng.choice([1, 2, 3], p=[0.6, 0.3, 0.1]))]
               for cid in cust_ids}

    # sessions that ended in a booking made on web/app
    online = bookings[bookings["channel"].isin(["Web", "App"]) & (bookings["booking_date"] >= START)]
    conv = online.sample(min(int(n * 0.12), len(online)), random_state=RANDOM_SEED).reset_index(drop=True)
    n_conv, n_other = len(conv), n - len(conv)

    # sessions without a booking: some customers, some strangers
    w = rng.lognormal(0, 1.0, len(cust)); w /= w.sum()
    visitor = rng.random(n_other) < 0.13
    other_idx = rng.choice(len(cust), n_other, p=w)
    other_cid = np.where(visitor, None, cust_ids[other_idx])
    other_date = random_dates(np.maximum(cust["created_date"].to_numpy(dtype="datetime64[D]")[other_idx],
                                         np.datetime64(START_DATE)), np.datetime64(END_DATE), n_other)
    stage = rng.choice([1, 2, 3, 4, 5], n_other, p=[0.34, 0.26, 0.19, 0.13, 0.08])
    dest = rng.choice(routes["route_id"], n_other, p=routes["flights_per_week_each_way"] / routes["flights_per_week_each_way"].sum())

    truth_cid = np.concatenate([conv["truth_customer_id"].to_numpy(dtype=object), other_cid])
    date = np.concatenate([conv["booking_date"].to_numpy(dtype="datetime64[D]"), other_date])
    stage = np.concatenate([np.full(n_conv, 6), stage])
    route = np.concatenate([conv["flight_id"].map(lambda x: None).to_numpy(), dest])
    booking_id = np.concatenate([conv["booking_id"].to_numpy(dtype=object), np.full(n_other, None)])

    # route searched for converted sessions comes from the booked flight
    flights = pd.read_csv(KEY_DIR / "flights_truth.csv", usecols=["flight_id", "route_id"]).set_index("flight_id")["route_id"]
    route[:n_conv] = conv["flight_id"].map(flights).to_numpy()

    # some customer sessions are logged out (anonymous)
    is_cust = pd.notna(truth_cid)
    v = 1 - is_cust.mean()
    p_anon = max((ANONYMOUS_SESSION_RATE - v) / (1 - v), 0)
    anon = rng.random(n) < p_anon
    logged_cid = np.where(is_cust & ~anon, truth_cid, None)

    device = np.array([rng.choice(devices[c]) if c is not None else f"dev_{rng.integers(16**8):08x}"
                       for c in truth_cid], dtype=object)

    hour_w = np.array([1, 1, 1, 1, 1, 2, 3, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 8, 9, 9, 7, 4, 2])
    hour = rng.choice(24, n, p=hour_w / hour_w.sum())
    start_ts = pd.to_datetime(date) + pd.to_timedelta(hour, unit="h") + pd.to_timedelta(rng.integers(0, 3600, n), unit="s")

    df = pd.DataFrame({
        "session_start": start_ts, "customer_id": logged_cid, "device_id": device,
        "device_type": rng.choice(["Mobile", "Desktop", "Tablet"], n, p=[0.58, 0.35, 0.07]),
        "traffic_source": rng.choice(["Direct", "Organic search", "Paid search", "Email campaign", "Metasearch", "Social"],
                                     n, p=[0.30, 0.25, 0.18, 0.12, 0.10, 0.05]),
        "searched_route_id": route, "furthest_stage": stage, "booking_id": booking_id,
        "truth_customer_id": truth_cid,
    })
    df = df.sort_values("session_start").reset_index(drop=True)
    labels = {1: "1_search", 2: "2_results", 3: "3_select_flight", 4: "4_passenger_details", 5: "5_payment", 6: "6_confirmed"}
    df["furthest_stage"] = df["furthest_stage"].map(labels)
    df.insert(0, "session_id", [f"S{i + 1:07d}" for i in range(len(df))])
    return df.drop(columns=["truth_customer_id"]), df[["session_id", "truth_customer_id"]]


# ---------------------------------------------------------------------------
def build_service(cust, bookings):
    flights = pd.read_csv(KEY_DIR / "flights_truth.csv", usecols=["flight_id", "cancelled", "arr_delay_min"])
    b = bookings[bookings["booking_status"].isin(["Flown", "Flight cancelled"])].merge(flights, on="flight_id")
    w = np.where(b["cancelled"] == 1, 10.0, np.where(b["arr_delay_min"] >= 60, 5.0, 1.0))
    pick = rng.choice(len(b), N_SERVICE_CONTACTS, replace=False, p=w / w.sum())
    b = b.iloc[pick].reset_index(drop=True)

    topics = np.empty(len(b), dtype=object)
    groups = [(b["cancelled"] == 1, ["Refund / rebooking", "Compensation claim", "Complaint"], [0.50, 0.35, 0.15]),
              ((b["cancelled"] == 0) & (b["arr_delay_min"] >= 60), ["Compensation claim", "Complaint", "Change booking", "Refund / rebooking"], [0.45, 0.25, 0.15, 0.15]),
              ((b["cancelled"] == 0) & (b["arr_delay_min"] < 60), ["Baggage", "Change booking", "Loyalty points", "Refund / rebooking", "Special assistance", "Complaint", "Payment issue"], [0.22, 0.25, 0.15, 0.12, 0.08, 0.08, 0.10])]
    for mask, names, probs in groups:
        m = mask.to_numpy()
        topics[m] = rng.choice(names, m.sum(), p=probs)

    contact_date = b["flight_date"] + pd.to_timedelta(rng.integers(0, 15, len(b)), unit="D")
    contact_date = contact_date.clip(upper=END)

    sat = 3.9 - 1.2 * (b["cancelled"] == 1) - 0.6 * ((b["arr_delay_min"] >= 60) & (b["cancelled"] == 0)) + rng.normal(0, 1.0, len(b))
    sat = np.clip(np.round(sat), 1, 5)
    sat[rng.random(len(b)) < 0.35] = np.nan                      # many customers skip the survey

    unlinked = rng.random(len(b)) < UNLINKED_SERVICE_RATE
    cu = cust.set_index("customer_id")
    t = b["truth_customer_id"]
    df = pd.DataFrame({
        "contact_date": contact_date.dt.date,
        "customer_id": np.where(unlinked, None, t),
        "contact_name": (cu.loc[t, "first_name"].to_numpy() + " " + cu.loc[t, "last_name"].to_numpy()),
        "contact_email": [mangle_email(e) if u else e for e, u in zip(cu.loc[t, "email"], unlinked)],
        "channel": rng.choice(["Phone", "Email", "Chat", "Social media"], len(b), p=[0.35, 0.30, 0.25, 0.10]),
        "topic": topics, "booking_id": b["booking_id"], "flight_id": b["flight_id"],
        "resolution_hours": np.round(rng.gamma(2.0, 14, len(b)), 1),
        "satisfaction_1_5": sat, "truth_customer_id": t,
    }).sort_values("contact_date").reset_index(drop=True)
    df.insert(0, "contact_id", [f"SC{i + 1:06d}" for i in range(len(df))])
    return df.drop(columns=["truth_customer_id"]), df[["contact_id", "truth_customer_id"]]


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    cust, bookings, flights, routes = load()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    loyalty, loyalty_truth = build_loyalty(cust, bookings)
    web, web_truth = build_web(cust, bookings, routes)
    service, service_truth = build_service(cust, bookings)

    assert loyalty["member_id"].is_unique and web["session_id"].is_unique and service["contact_id"].is_unique
    assert web["booking_id"].dropna().isin(bookings["booking_id"]).all()
    assert service["flight_id"].isin(flights["flight_id"]).all()
    print("\nAll validation checks passed.")

    loyalty.to_csv(RAW_DIR / "loyalty_members.csv", index=False)
    web.to_csv(RAW_DIR / "web_sessions.csv", index=False)
    service.to_csv(RAW_DIR / "service_contacts.csv", index=False)
    loyalty_truth.to_csv(KEY_DIR / "loyalty_truth.csv", index=False)
    web_truth.to_csv(KEY_DIR / "web_sessions_truth.csv", index=False)
    service_truth.to_csv(KEY_DIR / "service_contacts_truth.csv", index=False)

    print(f"\nLOYALTY   rows: {len(loyalty):,}   duplicate profiles: {int(loyalty_truth['is_duplicate_profile'].sum()):,}"
          f"   missing phone: {loyalty['phone'].isna().mean():.0%}   missing address: {loyalty['street_address'].isna().mean():.0%}")
    print(loyalty["tier"].value_counts().to_string())
    print(f"\nWEB       rows: {len(web):,}   anonymous (no customer_id): {web['customer_id'].isna().mean():.0%}")
    print(web["furthest_stage"].value_counts().sort_index().to_string())
    print(f"\nSERVICE   rows: {len(service):,}   without customer_id: {service['customer_id'].isna().mean():.0%}")
    print(service["topic"].value_counts().to_string())
    print("\nSaved loyalty_members.csv, web_sessions.csv, service_contacts.csv to data/raw")
    print("Saved three *_truth.csv files to data/answer_key")