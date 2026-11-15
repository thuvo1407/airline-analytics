"""
Step 7: Does the fictional airline behave like the real one?

Compares synthetic KPIs with figures Finnair has published for Q3 2026
(Interim report Jan-Sep 2026). 

"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"

# (what, our value function key, Finnair published value, allowed difference)
PLF_TARGET = {"Asia": 85.6, "North Atlantic": 80.5, "Europe": 80.2, "Domestic": 64.3, "Total": 81.8}
YIELD_TARGET = {"Asia": 8.38, "North Atlantic": 7.79, "Europe": 8.59, "Domestic": 19.37, "Total": 8.61}
ASK_SHARE_TARGET = {"Asia": (36, 40), "North Atlantic": (10, 14), "Europe": (42, 46), "Middle East": (0, 2), "Domestic": (3, 7)}

q = pd.read_csv(PROC / "kpis_quarterly.csv")
m = pd.read_csv(PROC / "kpis_monthly.csv")
q3 = q[q["quarter"] == "2026-Q3"].set_index("region")
rows = []


def check(name, ours, target, tol, unit=""):
    ok = abs(ours - target) <= tol
    rows.append((name, f"{ours:.1f}{unit}", f"{target:.2f}{unit}", f"+/-{tol}", "OK" if ok else "CHECK"))


for r, t in PLF_TARGET.items():
    check(f"Load factor Q3 2026, {r}", q3.loc[r, "plf_pct"], t, 1.0, "%")
for r, t in YIELD_TARGET.items():
    check(f"Yield Q3 2026, {r} (c/RPK)", q3.loc[r, "yield_eurocent_per_rpk"], t, 0.30)
check("On-time Q3 2026, Total", q3.loc["Total", "ontime_pct"], 79.7, 2.0, "%")

# on-time for January-September 2026 (flight-weighted)
jan_sep = m[(m["month"] >= "2026-01") & (m["month"] <= "2026-09") & (m["region"] == "Total")]
ontime = (jan_sep["ontime_pct"] * jan_sep["flights_operated"]).sum() / jan_sep["flights_operated"].sum()
check("On-time Jan-Sep 2026, Total", ontime, 78.6, 2.0, "%")
check("Ancillary revenue per passenger Q3 2026 (EUR)", q3.loc["Total", "ancillary_per_pax_eur"], 18.66, 1.5)

# capacity mix Jan-Sep 2026, measured on flown distance
js = m[(m["month"] >= "2026-01") & (m["month"] <= "2026-09") & (m["region"] != "Total")]
share = js.groupby("region")["ask_flown_million"].sum()
share = 100 * share / share.sum()
for r, (lo, hi) in ASK_SHARE_TARGET.items():
    ours = share.get(r, 0)
    rows.append((f"Capacity share Jan-Sep 2026, {r}", f"{ours:.1f}%", f"{lo}-{hi}%", "range", "OK" if lo <= ours <= hi else "CHECK"))

print(f"\n{'Check':<50}{'Ours':>9}{'Finnair':>11}{'Allowed':>11}   Result")
print("-" * 92)
for r in rows:
    print(f"{r[0]:<50}{r[1]:>9}{r[2]:>11}{r[3]:>11}   {r[4]}")
bad = sum(1 for r in rows if r[4] == "CHECK")
print(f"\n{len(rows) - bad} of {len(rows)} checks within range.")
if bad:
    print("Anything marked CHECK is outside the range. Tell me which and we can nudge the settings.")