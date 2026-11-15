"""
Step 3: Create the master customer table.
Output: data/answer_key/customers_truth.csv
"""
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

from config import (RANDOM_SEED, END_DATE, N_CUSTOMERS, CUSTOMER_SINCE,
                    COUNTRY_WEIGHTS, NEVER_UPDATED_RATE, MARKETING_CONSENT_RATE)

ROOT = Path(__file__).resolve().parent.parent
KEY_DIR = ROOT / "data" / "answer_key"

LOCALE = {"Finland": "fi_FI", "Sweden": "sv_SE", "Germany": "de_DE", "United Kingdom": "en_GB",
          "France": "fr_FR", "Netherlands": "nl_NL", "Spain": "es_ES", "Italy": "it_IT"}
LANGUAGE = {"Finland": ["fi", "fi", "fi", "sv", "en"], "Sweden": ["sv"], "Germany": ["de"],
            "United Kingdom": ["en"], "France": ["fr"], "Netherlands": ["nl"],
            "Spain": ["es"], "Italy": ["it"]}
EMAIL_DOMAINS = ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "example.com"]

rng = np.random.default_rng(RANDOM_SEED + 20)
Faker.seed(RANDOM_SEED + 20)
fakers = {c: Faker(LOCALE[c]) for c in LOCALE}


def slug(text):
    """'Mäkinen' -> 'makinen' (plain letters only, for email addresses)."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", text.lower())


def random_date(start, end, n):
    days = (end - start).days
    return [start + timedelta(days=int(d)) for d in rng.integers(0, days + 1, n)]


def build_customers():
    end = date.fromisoformat(END_DATE)
    since = date.fromisoformat(CUSTOMER_SINCE)
    countries = rng.choice(list(COUNTRY_WEIGHTS), N_CUSTOMERS, p=list(COUNTRY_WEIGHTS.values()))
    ages = np.clip(rng.normal(44, 15, N_CUSTOMERS), 18, 85).astype(int)
    births = [end - timedelta(days=int(a * 365.25 + rng.integers(0, 365))) for a in ages]
    created = random_date(since, end, N_CUSTOMERS)

    rows = []
    used_emails = set()
    for i in range(N_CUSTOMERS):
        c = countries[i]
        fk = fakers[c]
        gender = rng.choice(["F", "M", "X"], p=[0.49, 0.49, 0.02])
        first = fk.first_name_female() if gender == "F" else fk.first_name_male() if gender == "M" else fk.first_name()
        last = fk.last_name()
        # account cannot be created before the customer turned 18
        adult = births[i] + timedelta(days=18 * 365 + 5)
        created_i = min(max(created[i], adult), end)
        if rng.random() < NEVER_UPDATED_RATE:
            updated = created_i
        else:
            updated = created_i + timedelta(days=int(rng.integers(0, max((end - created_i).days, 0) + 1)))
        while True:   # keep trying until the email is not used by anyone else
            email = f"{slug(first)}.{slug(last)}{rng.integers(1, 9999)}@{rng.choice(EMAIL_DOMAINS)}"
            if email not in used_emails:
                used_emails.add(email)
                break
        rows.append({
            "customer_id": f"C{i + 1:06d}", "first_name": first, "last_name": last,
            "email": email, "phone": fk.phone_number(), "birth_date": births[i], "gender": gender,
            "country": c, "city": fk.city(), "street_address": fk.street_address().replace("\n", ", "),
            "postal_code": fk.postcode(), "preferred_language": rng.choice(LANGUAGE[c]),
            "marketing_consent": int(rng.random() < MARKETING_CONSENT_RATE),
            "created_date": created_i, "last_updated_date": updated,
        })
    return pd.DataFrame(rows)


def validate(df):
    assert len(df) == N_CUSTOMERS
    assert df["customer_id"].is_unique
    assert df["email"].is_unique, "duplicate emails"
    assert (df["last_updated_date"] >= df["created_date"]).all()
    assert (df["created_date"] <= date.fromisoformat(END_DATE)).all()
    age_at_created = [(c - b).days / 365.25 for c, b in zip(df["created_date"], df["birth_date"])]
    assert min(age_at_created) >= 17.9, "customer younger than 18 at sign-up"
    print("\nAll validation checks passed.")


if __name__ == "__main__":
    KEY_DIR.mkdir(parents=True, exist_ok=True)
    customers = build_customers()
    validate(customers)
    customers.to_csv(KEY_DIR / "customers_truth.csv", index=False)
    print(f"\nCustomers: {len(customers):,}")
    print("\nCustomers per country:")
    print(customers["country"].value_counts().to_string())
    print(f"\nMarketing consent: {customers['marketing_consent'].mean():.0%}")
    print("\nFirst 5 customers:")
    print(customers.head(5)[["customer_id", "first_name", "last_name", "email", "country", "city"]].to_string())
    print("\nSaved customers_truth.csv to data/answer_key")