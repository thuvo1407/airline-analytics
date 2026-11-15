"""
Step 6: Project 2 data.

  A) A deliberately MESSY flight extract, like an operations system would export it.
       data/raw/flights_extract.csv
       data/answer_key/flight_issues.csv     every flaw that was inserted, with the correct value
ß
  B) CLEAN KPI tables, calculated the way an airline reports them (ASK, RPK, load factor, yield...).
       data/processed/kpis_monthly.csv
       data/processed/kpis_quarterly.csv
       data/processed/kpis_route_monthly.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

from config import (RANDOM_SEED, FLIGHT_DELAY_CAUSE_VARIANT_RATE, FLIGHT_DELAY_CAUSE_MISSING_RATE,
                    FLIGHT_AIRCRAFT_LABEL_VARIANT_RATE, FLIGHT_DUPLICATE_ROW_RATE,
                    FLIGHT_PAX_OVER_SEATS_RATE, FLIGHT_MISSING_DELAY_RATE)
from generate_network import AIRCRAFT

rng = np.random.default_rng(RANDOM_SEED + 50)
ROOT = Path(__file__).resolve().parent.parent
KEY_DIR, RAW_DIR, PROC_DIR = ROOT / "data" / "answer_key", ROOT / "data" / "raw", ROOT / "data" / "processed"

CAUSE_VARIANTS = {
    "Weather": ["weather", "WX", "Wx / weather", "Weather "],
    "ATC / airspace": ["ATC", "atc delay", "Air traffic control", "ATC/airspace"],
    "Ground handling / turnaround": ["Ground handling", "turnaround", "Ground ops", "GH / turnaround"],
    "Late inbound aircraft": ["Late inbound", "late arrival of aircraft", "Inbound aircraft late"],
    "Technical": ["Tech", "Technical fault", "technical issue"],
    "Crew": ["crew", "Crew availability"],
    "Airport infrastructure": ["Airport", "Infrastructure"],
    "Industrial action": ["Strike", "industrial action"],
    "Other": ["other", "Misc", "Other "],
}
AIRCRAFT_VARIANTS = lambda a: [f"Airbus {a}", f"{a[0]}-{a[1:]}", a.lower(), f"{a}-200" if a != "A350" else "A350-900"]


# ---------------------------------------------------------------------------
def make_messy(truth):
    df = truth.copy()
    issues = []

    def log(mask, issue_type, column, correct):
        sub = df.loc[mask, "flight_id"]
        for fid, c, m in zip(sub, correct, df.loc[mask, column]):
            issues.append((fid, issue_type, column, c, m))

    # 1. delay cause left blank
    has_cause = df["delay_cause"].notna()
    miss = has_cause & (rng.random(len(df)) < FLIGHT_DELAY_CAUSE_MISSING_RATE)
    correct = df.loc[miss, "delay_cause"].tolist()
    df.loc[miss, "delay_cause"] = np.nan
    log(miss, "missing_delay_cause", "delay_cause", correct)

    # 2. delay cause typed in a different way
    var = df["delay_cause"].notna() & (rng.random(len(df)) < FLIGHT_DELAY_CAUSE_VARIANT_RATE)
    correct = df.loc[var, "delay_cause"].tolist()
    df.loc[var, "delay_cause"] = [rng.choice(CAUSE_VARIANTS[c]) for c in correct]
    log(var, "delay_cause_variant", "delay_cause", correct)

    # 3. aircraft type labelled differently
    var = rng.random(len(df)) < FLIGHT_AIRCRAFT_LABEL_VARIANT_RATE
    correct = df.loc[var, "aircraft_type"].tolist()
    df.loc[var, "aircraft_type"] = [rng.choice(AIRCRAFT_VARIANTS(a)) for a in correct]
    log(var, "aircraft_label_variant", "aircraft_type", correct)

    # 4. more passengers than seats (a system error)
    op = df["cancelled"] == 0
    over = op & (rng.random(len(df)) < FLIGHT_PAX_OVER_SEATS_RATE)
    correct = df.loc[over, "pax_boarded"].tolist()
    df.loc[over, "pax_boarded"] = df.loc[over, "seats"] + rng.integers(1, 16, over.sum())
    log(over, "pax_over_seats", "pax_boarded", correct)

    # 5. missing arrival delay on an operated flight
    gone = op & (rng.random(len(df)) < FLIGHT_MISSING_DELAY_RATE)
    correct = df.loc[gone, "arr_delay_min"].tolist()
    df.loc[gone, "arr_delay_min"] = np.nan
    log(gone, "missing_arrival_delay", "arr_delay_min", correct)

    # 6. duplicate rows
    dup = df.sample(frac=FLIGHT_DUPLICATE_ROW_RATE, random_state=RANDOM_SEED)
    for fid in dup["flight_id"]:
        issues.append((fid, "duplicate_row", "(whole row)", "1 row", "2 rows"))
    df = pd.concat([df, dup]).sort_values(["flight_date", "sched_dep_hour", "flight_number"], kind="stable").reset_index(drop=True)

    key = pd.DataFrame(issues, columns=["flight_id", "issue_type", "column", "correct_value", "messy_value"])
    return df, key


# ---------------------------------------------------------------------------
def kpis(df, period_col):
    """Airline KPIs per period and region (plus a 'Total' row per period)."""
    d = df.copy()
    op = d["cancelled"] == 0
    cap_t = d["aircraft_type"].map({k: v[2] for k, v in AIRCRAFT.items()})
    d["ask_km"] = np.where(op, d["seats"] * d["gc_km"], 0.0)                    # seats x great-circle km
    d["ask_flown_km"] = np.where(op, d["seats"] * d["flown_km"], 0.0)            # seats x km actually flown
    d["rpk"] = d["pax_boarded"] * d["gc_km"]
    d["atk"] = np.where(op, cap_t * d["gc_km"], 0.0)
    d["rtk"] = d["cargo_tonnes"] * d["gc_km"]
    d["ontime"] = (op & (d["arr_delay_min"] < 15)).astype(int)
    d["operated"] = op.astype(int)

    sums = ["operated", "cancelled", "ontime", "pax_boarded", "ask_km", "ask_flown_km", "rpk", "pass_revenue_eur",
            "ancillary_revenue_eur", "atk", "rtk", "cargo_tonnes", "cargo_revenue_eur", "co2_t"]
    parts = [d.groupby([period_col, "region"])[sums].sum().reset_index(),
             d.groupby(period_col)[sums].sum().reset_index().assign(region="Total")]
    k = pd.concat(parts, ignore_index=True)

    out = pd.DataFrame({
        period_col: k[period_col], "region": k["region"],
        "flights_operated": k["operated"], "flights_cancelled": k["cancelled"],
        "regularity_pct": 100 * k["operated"] / (k["operated"] + k["cancelled"]),
        "ontime_pct": 100 * k["ontime"] / k["operated"],
        "passengers": k["pax_boarded"],
        "ask_million": k["ask_km"] / 1e6, "ask_flown_million": k["ask_flown_km"] / 1e6, "rpk_million": k["rpk"] / 1e6,
        "plf_pct": 100 * k["rpk"] / k["ask_km"],
        "pass_revenue_eur_m": k["pass_revenue_eur"] / 1e6,
        "yield_eurocent_per_rpk": 100 * k["pass_revenue_eur"] / k["rpk"],
        "rask_eurocent": 100 * k["pass_revenue_eur"] / k["ask_km"],
        "ancillary_per_pax_eur": k["ancillary_revenue_eur"] / k["pax_boarded"],
        "cargo_tonnes": k["cargo_tonnes"], "rtk_million": k["rtk"] / 1e6,
        "cargo_load_factor_pct": 100 * k["rtk"] / k["atk"],
        "cargo_revenue_eur_m": k["cargo_revenue_eur"] / 1e6,
        "co2_t": k["co2_t"],
    })
    return out.round(3).sort_values([period_col, "region"]).reset_index(drop=True)


if __name__ == "__main__":
    truth = pd.read_csv(KEY_DIR / "flights_truth.csv", parse_dates=["flight_date"])
    routes = pd.read_csv(PROC_DIR / "routes.csv")
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    messy, issues = make_messy(truth)
    messy.to_csv(RAW_DIR / "flights_extract.csv", index=False)
    issues.to_csv(KEY_DIR / "flight_issues.csv", index=False)

    truth["month"] = truth["flight_date"].dt.strftime("%Y-%m")
    truth["quarter"] = truth["flight_date"].dt.year.astype(str) + "-Q" + truth["flight_date"].dt.quarter.astype(str)
    monthly, quarterly = kpis(truth, "month"), kpis(truth, "quarter")
    route_monthly = kpis(truth.assign(region=truth["route_id"]), "month")
    route_monthly = route_monthly[route_monthly["region"] != "Total"].rename(columns={"region": "route_id"})
    monthly.to_csv(PROC_DIR / "kpis_monthly.csv", index=False)
    quarterly.to_csv(PROC_DIR / "kpis_quarterly.csv", index=False)
    route_monthly.to_csv(PROC_DIR / "kpis_route_monthly.csv", index=False)

    # checks
    assert len(messy) == len(truth) + (issues["issue_type"] == "duplicate_row").sum()
    assert truth["pax_boarded"].sum() == truth.loc[truth["cancelled"] == 0, "pax_boarded"].sum()
    assert quarterly[quarterly["region"] == "Total"]["passengers"].sum() == truth["pax_boarded"].sum()
    print("\nAll validation checks passed.")

    print(f"\nMESSY EXTRACT: {len(messy):,} rows (clean version has {len(truth):,})")
    print("Flaws inserted:")
    print(issues["issue_type"].value_counts().to_string())
    print(f"\nKPI tables: {len(monthly)} monthly rows, {len(quarterly)} quarterly rows, {len(route_monthly)} route-month rows")
    q = quarterly[quarterly["quarter"] == "2026-Q3"].set_index("region")
    print("\nQ3 2026 snapshot (we compare this with Finnair's real figures in Step 7):")
    print(q[["plf_pct", "yield_eurocent_per_rpk", "ontime_pct"]].round(1).to_string())
    print("\nSaved flights_extract.csv to data/raw, flight_issues.csv to data/answer_key,")
    print("and three kpis_*.csv files to data/processed")