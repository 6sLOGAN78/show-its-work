"""Synthetic, Olist-shaped order stream — the self-contained fallback.

If real Olist CSVs aren't in data/raw/, the whole engine still runs on this. It
produces a CLEAN baseline (no anomalies); inject.py then plants the anomaly + decoy
and records the answer key. Deterministic given a seed, so ground truth is exact.

Everything is emitted into ONE canonical frame `orders_fact` (see COLUMNS) that the
real-Olist path also maps into, so downstream tools are source-agnostic.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

COLUMNS = [
    "order_id", "order_purchase_date", "order_status", "seller_id", "category",
    "region", "price", "freight_value", "promised_days", "actual_days", "on_time",
    "delivered", "review_score", "review_creation_date", "review_text",
    "customer_unique_id",
]

# GoT-house seller names echo Olist's anonymisation; one is the future culprit.
SELLERS = ["house_stark", "house_lannister", "house_targaryen", "house_bravos",
           "house_martell", "house_tully", "house_arryn", "house_baratheon"]
SELLER_WEIGHTS = np.array([0.14, 0.16, 0.12, 0.18, 0.10, 0.11, 0.09, 0.10])  # bravos is big
CATEGORIES = ["electronics", "home_decor", "health_beauty", "sports_leisure", "toys"]
CAT_WEIGHTS = np.array([0.30, 0.22, 0.20, 0.16, 0.12])
CAT_BASE_PRICE = {"electronics": 220.0, "home_decor": 90.0, "health_beauty": 60.0,
                  "sports_leisure": 110.0, "toys": 45.0}
REGIONS = ["SP", "RJ", "MG", "PR", "SC", "RS"]           # SP/PR/SC/RS = South scope
REGION_WEIGHTS = np.array([0.42, 0.18, 0.14, 0.10, 0.08, 0.08])


def generate_clean(n_days: int = 180, start: str = "2024-01-01",
                   base_daily: int = 380, seed: int = 7) -> pd.DataFrame:
    """A realistic baseline: weekly seasonality, mild trend, repeat customers, reviews
    that lag purchase and track on-time delivery. No anomaly yet."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=n_days, freq="D")

    # a pool of customers, so repeat-purchase rate is meaningful
    n_customers = base_daily * n_days // 3
    customers = np.array([f"cust_{i:06d}" for i in range(n_customers)])

    rows = []
    order_seq = 0
    for di, day in enumerate(dates):
        dow = day.dayofweek
        weekend = 0.78 if dow >= 5 else 1.0                 # weekends quieter
        trend = 1.0 + 0.0008 * di                           # slow growth
        month_season = 1.0 + 0.06 * np.sin(2 * np.pi * di / 90)
        lam = base_daily * weekend * trend * month_season
        n = int(rng.poisson(lam))
        if n <= 0:
            continue
        sellers = rng.choice(SELLERS, size=n, p=SELLER_WEIGHTS)
        cats = rng.choice(CATEGORIES, size=n, p=CAT_WEIGHTS)
        regions = rng.choice(REGIONS, size=n, p=REGION_WEIGHTS)
        # repeat customers: 35% draw from a "returning" head of the pool
        returning = rng.random(n) < 0.35
        cust = np.where(
            returning,
            rng.choice(customers[: n_customers // 3], size=n),
            rng.choice(customers, size=n),
        )
        for k in range(n):
            cat = cats[k]
            price = float(max(5.0, rng.normal(CAT_BASE_PRICE[cat], CAT_BASE_PRICE[cat] * 0.16)))
            freight = float(max(0.0, rng.normal(18, 6)))
            promised = int(rng.integers(7, 16))
            actual = int(max(1, rng.normal(promised - 1.0, 2.5)))   # usually a bit early
            on_time = actual <= promised
            delivered = rng.random() > 0.03                          # 3% not delivered
            # review score tracks on-time; lags purchase by a few days
            base_score = 4.4 if on_time else 3.1
            score = float(np.clip(rng.normal(base_score, 0.7), 1, 5))
            reviewed = rng.random() < 0.62
            rev_date = day + pd.Timedelta(days=int(rng.integers(3, 9))) if reviewed else pd.NaT
            rev_text = _review_text(rng, on_time, score) if reviewed else None
            rows.append((
                f"ord_{order_seq:07d}", day, "delivered" if delivered else "unavailable",
                sellers[k], cat, regions[k], round(price, 2), round(freight, 2),
                promised, actual, on_time, delivered,
                round(score, 1) if reviewed else np.nan, rev_date, rev_text, cust[k],
            ))
            order_seq += 1

    df = pd.DataFrame(rows, columns=COLUMNS)
    df["order_purchase_date"] = pd.to_datetime(df["order_purchase_date"])
    df["review_creation_date"] = pd.to_datetime(df["review_creation_date"])
    return df


_POS = ["Arrived earlier than expected, very happy.", "Great quality, fast shipping.",
        "Exactly as described, would buy again.", "Smooth delivery, no issues."]
_NEG = ["Package arrived very late, disappointed.", "Delivery took forever, still waiting feel.",
        "Late again, the estimate was way off.", "Slow shipping and poor updates."]
_MID = ["Product ok, delivery a little slow.", "Average experience overall.",
        "Fine but nothing special."]


def _review_text(rng, on_time: bool, score: float) -> str:
    if score >= 4:
        return str(rng.choice(_POS))
    if score <= 2.5 or not on_time:
        return str(rng.choice(_NEG))
    return str(rng.choice(_MID))
