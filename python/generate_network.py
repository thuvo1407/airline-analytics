"""
Step 2: Build the fictional airline's network and simulate every flight.

Airline: "Nordic Horizon Airways" (FICTIONAL). Numbers are only calibrated to the
rough shape of public airline figures. Everything here is synthetic.

Outputs
  data/processed/routes.csv          one row per route
  data/processed/events.csv          invented disruption scenarios
  data/answer_key/flights_truth.csv  every flight, clean (the "right answer")
"""
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from config import RANDOM_SEED, START_DATE, END_DATE

rng = np.random.default_rng(RANDOM_SEED + 10)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"
KEY_DIR = ROOT / "data" / "answer_key"

# ---------------------------------------------------------------------------
# Reference data (illustrative, not official)
# ---------------------------------------------------------------------------
# aircraft: seats, fuel burn (kg per km flown), belly cargo capacity (tonnes)
AIRCRAFT = {
    "A319": (144, 3.0, 1.0), "A320": (174, 3.3, 1.5), "A321": (209, 3.7, 2.0),
    "A330": (279, 6.8, 14.0), "A350": (278, 6.3, 16.0),
}
REGIONS = ["Asia", "North Atlantic", "Europe", "Middle East", "Domestic"]

# destination, city, country, region, great-circle km from HEL, flights per week each way,
# aircraft, joint business partner, last operating date, flown-distance factor (detours)
ROUTES = [
    ("OUL", "Oulu", "Finland", "Domestic", 535, 14, "A320", None, None, 1.0),
    ("RVN", "Rovaniemi", "Finland", "Domestic", 700, 10, "A320", None, None, 1.0),
    ("IVL", "Ivalo", "Finland", "Domestic", 885, 7, "A319", None, None, 1.0),
    ("KTT", "Kittila", "Finland", "Domestic", 840, 10, "A320", None, None, 1.0),
    ("VAA", "Vaasa", "Finland", "Domestic", 330, 7, "A319", None, None, 1.0),
    ("ARN", "Stockholm", "Sweden", "Europe", 395, 28, "A320", None, None, 1.0),
    ("CPH", "Copenhagen", "Denmark", "Europe", 890, 21, "A320", None, None, 1.0),
    ("OSL", "Oslo", "Norway", "Europe", 790, 14, "A320", None, None, 1.0),
    ("LHR", "London", "United Kingdom", "Europe", 1830, 21, "A321", None, None, 1.0),
    ("AMS", "Amsterdam", "Netherlands", "Europe", 1500, 21, "A321", None, None, 1.0),
    ("FRA", "Frankfurt", "Germany", "Europe", 1510, 21, "A321", None, None, 1.0),
    ("CDG", "Paris", "France", "Europe", 1900, 21, "A321", None, None, 1.0),
    ("MUC", "Munich", "Germany", "Europe", 1610, 14, "A320", None, None, 1.0),
    ("BCN", "Barcelona", "Spain", "Europe", 2700, 14, "A321", None, None, 1.0),
    ("FCO", "Rome", "Italy", "Europe", 2500, 10, "A321", None, None, 1.0),
    ("MAD", "Madrid", "Spain", "Europe", 3260, 10, "A321", None, None, 1.0),
    ("ATH", "Athens", "Greece", "Europe", 2500, 7, "A321", None, None, 1.0),
    ("JFK", "New York", "United States", "North Atlantic", 6620, 7, "A350", "Atlantic JB", None, 1.0),
    ("ORD", "Chicago", "United States", "North Atlantic", 6880, 3, "A350", "Atlantic JB", None, 1.0),
    ("NRT", "Tokyo", "Japan", "Asia", 7830, 6, "A350", "Siberian JB", None, 1.35),
    ("KIX", "Osaka", "Japan", "Asia", 8100, 2, "A350", "Siberian JB", None, 1.35),
    ("ICN", "Seoul", "South Korea", "Asia", 7500, 3, "A350", None, None, 1.35),
    ("BKK", "Bangkok", "Thailand", "Asia", 7900, 2, "A350", None, None, 1.30),
    ("SIN", "Singapore", "Singapore", "Asia", 9500, 2, "A350", None, None, 1.30),
    ("DEL", "Delhi", "India", "Asia", 6300, 2, "A330", None, None, 1.15),
    ("HKG", "Hong Kong", "China", "Asia", 8450, 2, "A350", None, None, 1.35),
    ("DOH", "Doha", "Qatar", "Middle East", 4300, 2, "A330", None, "2026-02-27", 1.0),
    ("DXB", "Dubai", "UAE", "Middle East", 4700, 1, "A330", None, "2026-02-27", 1.0),
]

BASE_PLF = {  # average share of seats filled, by region and year
    "Asia": {2023: 0.80, 2024: 0.81, 2025: 0.82, 2026: 0.795},
    "North Atlantic": {2023: 0.78, 2024: 0.77, 2025: 0.75, 2026: 0.735},
    "Europe": {2023: 0.76, 2024: 0.76, 2025: 0.75, 2026: 0.725},
    "Middle East": {2023: 0.72, 2024: 0.74, 2025: 0.76, 2026: 0.78},
    "Domestic": {2023: 0.63, 2024: 0.64, 2025: 0.64, 2026: 0.62},
}
SEASON = {  # month multipliers, Jan..Dec
    "Europe": [0.89, 0.91, 0.97, 0.99, 1.01, 1.05, 1.07, 1.07, 1.04, 1.01, 0.95, 0.97],
    "Asia": [0.95, 0.96, 0.99, 1.00, 1.00, 1.02, 1.04, 1.04, 1.02, 1.00, 0.97, 0.98],
    "North Atlantic": [0.92, 0.94, 0.98, 1.00, 1.03, 1.06, 1.06, 1.05, 1.03, 1.00, 0.95, 0.97],
    "Domestic": [1.00, 1.05, 1.02, 0.97, 0.93, 0.95, 0.98, 0.98, 0.97, 0.98, 0.98, 1.05],
    "Middle East": [0.95, 0.96, 0.99, 1.00, 1.00, 1.02, 1.04, 1.04, 1.02, 1.00, 0.97, 0.98],
}
DOW_PLF = [0.97, 0.98, 0.98, 1.00, 1.03, 0.97, 1.03]          # Mon..Sun

YIELD = {"Asia": 7.6, "North Atlantic": 7.1, "Europe": 7.9, "Domestic": 18.7, "Middle East": 7.0}  # euro cents per RPK
YIELD_YEAR = {2023: 1.03, 2024: 1.00, 2025: 0.96, 2026: 1.00}
PRICE_SEASON = [0.95, 0.95, 0.98, 1.00, 1.00, 1.02, 1.05, 1.05, 1.02, 1.00, 0.98, 1.04]
ANCILLARY_PER_PAX = {2023: 14.5, 2024: 15.5, 2025: 17.3, 2026: 18.7}
ANCILLARY_REGION = {"Domestic": 0.55, "Europe": 0.95, "Asia": 1.15, "North Atlantic": 1.15, "Middle East": 1.10}
CARGO_LF = {"Asia": 0.62, "North Atlantic": 0.52, "Middle East": 0.60, "Europe": 0.40, "Domestic": 0.25}
CARGO_EUR_PER_T = {"Asia": 2300, "North Atlantic": 1700, "Middle East": 1500, "Europe": 1100, "Domestic": 700}
CARGO_YEAR = {2023: 1.00, 2024: 0.95, 2025: 0.92, 2026: 1.00}

LATE_BASE = [0.28, 0.22, 0.17, 0.17, 0.15, 0.20, 0.23, 0.20, 0.18, 0.16, 0.22, 0.30]  # share 15+ min late
CAUSES = ["Weather", "ATC / airspace", "Ground handling / turnaround", "Late inbound aircraft",
          "Technical", "Crew", "Airport infrastructure", "Industrial action", "Other"]
CAUSE_P_WINTER = np.array([0.38, 0.10, 0.20, 0.16, 0.08, 0.03, 0.02, 0.00, 0.03])
CAUSE_P_SUMMER = np.array([0.12, 0.26, 0.17, 0.25, 0.10, 0.04, 0.02, 0.00, 0.04])
CAUSE_P_SHOULDER = (CAUSE_P_WINTER + CAUSE_P_SUMMER) / 2

# Invented scenario events (loosely inspired by disruptions real airlines face)
EVENTS = [
    dict(event_id="E01", name="Heavy snowfall at hub", event_type="Weather", start="2024-11-20",
         end="2024-11-23", cancel_add=0.10, late_add=0.30, plf_add=0.0, cause="Weather"),
    dict(event_id="E02", name="Hub runway renovation", event_type="Infrastructure", start="2024-05-01",
         end="2024-05-31", cancel_add=0.0, late_add=0.10, plf_add=0.0, cause="Airport infrastructure"),
    dict(event_id="E03", name="European ATC capacity restrictions", event_type="Airspace",
         start="2024-07-01", end="2024-07-31", cancel_add=0.0, late_add=0.08, plf_add=0.0, cause="ATC / airspace"),
    dict(event_id="E04", name="Industrial action (first period)", event_type="Industrial action",
         start="2025-03-03", end="2025-03-31", cancel_add=0.25, late_add=0.05, plf_add=0.03, cause="Industrial action"),
    dict(event_id="E05", name="Industrial action (second period)", event_type="Industrial action",
         start="2025-07-04", end="2025-07-31", cancel_add=0.30, late_add=0.05, plf_add=0.03, cause="Industrial action"),
    dict(event_id="E06", name="European ATC capacity restrictions", event_type="Airspace",
         start="2026-07-01", end="2026-07-31", cancel_add=0.0, late_add=0.03, plf_add=0.0, cause="ATC / airspace"),
    dict(event_id="E07", name="Middle East flights suspended; market capacity falls", event_type="Geopolitical",
         start="2026-02-28", end="2026-10-31", cancel_add=0.0, late_add=0.0, plf_add=0.03, cause=None),
]
MARKET_YIELD_UPLIFT = 1.04      # from 2026-03-01, routes outside the Middle East
MARKET_CARGO_UPLIFT = 1.20      # Asia cargo rates from 2026-03-01
HOURS_SHORT = [6, 8, 10, 12, 14, 16, 18, 20]


# ---------------------------------------------------------------------------
def build_routes_table():
    rows = []
    for i, (dest, city, country, region, km, freq, ac, jb, last, flown) in enumerate(ROUTES):
        rows.append({
            "route_id": f"HEL-{dest}", "route_no": i, "origin_hub": "HEL", "destination": dest,
            "city": city, "country": country, "region": region, "gc_km": km,
            "flown_km_factor": flown, "flights_per_week_each_way": freq, "aircraft_type": ac,
            "seats": AIRCRAFT[ac][0], "joint_business": jb or "", "last_operating_date": last or "",
        })
    return pd.DataFrame(rows)


def build_schedule(routes):
    """Weekly timetable: which flight numbers run on which weekday and hour."""
    rows = []
    for _, r in routes.iterrows():
        per_day, extra = divmod(int(r.flights_per_week_each_way), 7)
        extra_days = set(np.round(np.linspace(0, 6, extra)).astype(int)) if extra else set()
        long_haul = r.region in ("Asia", "North Atlantic", "Middle East")
        for wd in range(7):
            n = per_day + (1 if wd in extra_days else 0)
            for k in range(n):
                for direction in (0, 1):                       # 0 = out of HEL, 1 = into HEL
                    if long_haul:
                        hour = {"Asia": (17, 9), "North Atlantic": (12, 16), "Middle East": (14, 3)}[r.region][direction]
                    else:
                        hour = min(HOURS_SHORT[(k * len(HOURS_SHORT)) // max(n, 1) % len(HOURS_SHORT)] + direction, 23)
                    rows.append({
                        "route_id": r.route_id, "direction": "OUT" if direction == 0 else "IN", "weekday": wd,
                        "flight_number": f"NH{100 + int(r.route_no) * 10 + direction * 5 + k}", "sched_dep_hour": hour,
                    })
    return pd.DataFrame(rows)


def simulate_flights(routes):
    dates = pd.DataFrame({"flight_date": pd.date_range(START_DATE, END_DATE)})
    dates["weekday"] = dates["flight_date"].dt.weekday
    f = build_schedule(routes).merge(dates, on="weekday")
    f = f.merge(routes[["route_id", "destination", "region", "gc_km", "flown_km_factor", "aircraft_type",
                        "seats", "joint_business", "last_operating_date"]], on="route_id")
    last = pd.to_datetime(f["last_operating_date"].replace("", np.nan))
    f = f[last.isna() | (f["flight_date"] <= last)]
    f = f.sort_values(["flight_date", "sched_dep_hour", "flight_number"]).reset_index(drop=True)
    n = len(f)

    date = f["flight_date"]
    year, month, dow = date.dt.year.to_numpy(), date.dt.month.to_numpy(), date.dt.weekday.to_numpy()
    region, seats, ac = f["region"].to_numpy(), f["seats"].to_numpy(), f["aircraft_type"].to_numpy()
    gc_km = f["gc_km"].to_numpy().astype(float)
    flown_km = gc_km * f["flown_km_factor"].to_numpy()
    hour = f["sched_dep_hour"].to_numpy()
    long_haul = np.isin(region, ["Asia", "North Atlantic", "Middle East"])

    # scenario events switch extra cancellations / delays / demand on for date ranges
    cancel_add, late_add, plf_add = np.zeros(n), np.zeros(n), np.zeros(n)
    event_cause = np.full(n, None, dtype=object)
    for e in EVENTS:
        m = ((date >= e["start"]) & (date <= e["end"])).to_numpy()
        cancel_add[m] += e["cancel_add"]; late_add[m] += e["late_add"]; plf_add[m] += e["plf_add"]
        if e["cause"]:
            event_cause[m] = e["cause"]
    market_event = (date >= "2026-03-01").to_numpy() & (region != "Middle East")

    # cancellations
    winter = np.isin(month, [12, 1, 2])
    cancelled = rng.random(n) < np.clip(0.007 + 0.012 * winter + cancel_add, 0, 0.9)

    # passengers
    base, season = np.zeros(n), np.zeros(n)
    for r in REGIONS:
        m = region == r
        base[m] = [BASE_PLF[r][y] for y in year[m]]
        season[m] = np.array(SEASON[r])[month[m] - 1]
    plf = base * season * np.array(DOW_PLF)[dow] + plf_add + 0.01 * market_event
    plf = np.clip(plf + rng.normal(0, 0.055, n), 0.30, 0.99)
    pax = np.round(seats * plf).astype(int)
    pax[cancelled] = 0
    realised = pax / seats
    codeshare = np.where(f["joint_business"].to_numpy() != "", np.round(pax * rng.uniform(0.10, 0.22, n)), 0).astype(int)

    # revenue (fuller flights sell slightly higher fares)
    fare_mult = (0.85 + 0.30 * realised) / (0.85 + 0.30 * 0.8)
    yield_c = (np.array([YIELD[r] for r in region]) * np.array([YIELD_YEAR[y] for y in year])
               * np.array(PRICE_SEASON)[month - 1] * np.where(market_event, MARKET_YIELD_UPLIFT, 1.0)
               * fare_mult * rng.lognormal(0, 0.06, n))
    pass_rev = np.round(pax * gc_km * yield_c / 100, 2)
    ancillary = np.round(pax * np.array([ANCILLARY_PER_PAX[y] for y in year])
                         * np.array([ANCILLARY_REGION[r] for r in region]) * rng.lognormal(0, 0.05, n), 2)

    # cargo
    cap_t = np.array([AIRCRAFT[a][2] for a in ac])
    cargo_t = np.clip(cap_t * np.array([CARGO_LF[r] for r in region]) * rng.normal(1, 0.15, n), 0, cap_t)
    cargo_t = np.where(cancelled, 0, np.round(cargo_t, 2))
    cargo_rate = (np.array([CARGO_EUR_PER_T[r] for r in region]) * np.array([CARGO_YEAR[y] for y in year])
                  * np.where(market_event & (region == "Asia"), MARKET_CARGO_UPLIFT, 1.0) * rng.lognormal(0, 0.08, n))
    cargo_rev = np.round(cargo_t * cargo_rate, 2)

    # fuel and CO2
    fuel_t = np.array([AIRCRAFT[a][1] for a in ac]) * flown_km / 1000 * (1 + 0.10 * (realised - 0.8))
    fuel_t = np.where(cancelled, 0, np.round(fuel_t, 2))
    co2_t = np.round(fuel_t * 3.16, 2)

    # punctuality: share of flights arriving 15+ minutes late
    late_p = np.clip(np.array(LATE_BASE)[month - 1] + 0.02 * long_haul - 0.02 * (region == "Domestic")
                     + 0.03 * (hour >= 16) + late_add, 0.02, 0.9)
    is_late = (rng.random(n) < late_p) & ~cancelled
    arr_delay = np.where(is_late, np.minimum(15 + rng.exponential(40, n), 480),
                         np.minimum(rng.normal(-4, 8, n), 14)).round().astype(float)
    arr_delay[cancelled] = np.nan

    cause = np.full(n, None, dtype=object)
    for months, probs in (([12, 1, 2], CAUSE_P_WINTER), ([6, 7, 8], CAUSE_P_SUMMER), ([3, 4, 5, 9, 10, 11], CAUSE_P_SHOULDER)):
        m = is_late & np.isin(month, months)
        cause[m] = np.array(CAUSES, dtype=object)[rng.choice(len(CAUSES), m.sum(), p=probs)]
    override = is_late & pd.notna(event_cause) & (rng.random(n) < 0.75)
    cause[override] = event_cause[override]

    cancel_reason = np.full(n, None, dtype=object)
    cancel_reason[cancelled] = np.array(["Weather", "Technical", "Crew", "ATC / airspace", "Other"], dtype=object)[
        rng.choice(5, cancelled.sum(), p=[0.40, 0.30, 0.10, 0.10, 0.10])]
    ov = cancelled & pd.notna(event_cause)
    cancel_reason[ov] = event_cause[ov]

    out_dir = f["direction"] == "OUT"
    return pd.DataFrame({
        "flight_id": date.dt.strftime("%Y%m%d") + "-" + f["flight_number"],
        "flight_date": date.dt.date, "flight_number": f["flight_number"], "route_id": f["route_id"],
        "origin": np.where(out_dir, "HEL", f["destination"]), "destination": np.where(out_dir, f["destination"], "HEL"),
        "region": region, "direction": f["direction"], "aircraft_type": ac, "seats": seats,
        "sched_dep_hour": hour, "cancelled": cancelled.astype(int), "cancel_reason": cancel_reason,
        "arr_delay_min": arr_delay, "delay_cause": cause, "pax_boarded": pax, "partner_codeshare_pax": codeshare,
        "gc_km": gc_km.astype(int), "flown_km": flown_km.round().astype(int),
        "pass_revenue_eur": pass_rev, "ancillary_revenue_eur": ancillary,
        "cargo_tonnes": cargo_t, "cargo_revenue_eur": cargo_rev, "fuel_burn_t": fuel_t, "co2_t": co2_t,
    })


def events_table():
    return pd.DataFrame([{
        "event_id": e["event_id"], "name": e["name"], "event_type": e["event_type"],
        "start_date": e["start"], "end_date": e["end"], "extra_cancel_prob": e["cancel_add"],
        "extra_late_prob": e["late_add"], "load_factor_effect": e["plf_add"],
        "note": "Invented scenario for this fictional airline"} for e in EVENTS])


def validate(df):
    """Sanity checks: the clean flight table must obey basic physical rules."""
    op = df["cancelled"] == 0
    assert df["flight_id"].is_unique, "duplicate flight ids"
    assert (df.loc[op, "pax_boarded"] <= df.loc[op, "seats"]).all(), "more passengers than seats"
    assert (df.loc[~op, "pax_boarded"] == 0).all(), "cancelled flight has passengers"
    assert df.loc[op, "arr_delay_min"].notna().all(), "missing delay on operated flight"
    me = df[df["region"] == "Middle East"]
    assert me["flight_date"].max() <= datetime(2026, 2, 27).date(), "Middle East flight after suspension"
    assert df["flight_date"].min() >= pd.Timestamp(START_DATE).date()
    assert df["flight_date"].max() <= pd.Timestamp(END_DATE).date()
    print("\nAll validation checks passed.")


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    routes = build_routes_table()
    flights = simulate_flights(routes)
    validate(flights)
    routes.to_csv(DATA_DIR / "routes.csv", index=False)
    events_table().to_csv(DATA_DIR / "events.csv", index=False)
    flights.to_csv(KEY_DIR / "flights_truth.csv", index=False)

    print("\nNETWORK DATASET")
    print("---------------")
    print(f"Routes: {len(routes)}   Flights: {len(flights):,}   Cancelled: {flights['cancelled'].mean():.1%}")
    print("\nFlights per region:")
    print(flights["region"].value_counts().to_string())
    op = flights[flights["cancelled"] == 0]
    print(f"\nOn-time (arrived <15 min late): {(op['arr_delay_min'] < 15).mean():.1%}")
    print(f"Average seats filled: {op['pax_boarded'].sum() / op['seats'].sum():.1%}")
    print("\nFirst 3 flights:")
    print(flights.head(3).to_string())
    print("\nSaved routes.csv and events.csv to data/processed, flights_truth.csv to data/answer_key")