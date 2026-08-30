"""Anomaly injection harness — and the answer key.

Plants a controlled multi-factor movement into a CLEAN order stream (synthetic or
real Olist mapped to the same schema) and records exactly what it did, so we can
grade root-cause accuracy and decoy rejection objectively.

Data-agnostic: the target seller, target category, and window are derived from the
data if not given, so this runs unchanged on synthetic or real Olist.

Three planted elements (the demo's spine):
  PRIMARY  <biggest seller> delivery collapse -> the true cause (~two-thirds of delta)
  MINOR    <a category> supplier stockout      -> real but small contributor (down-rank)
  DECOY    competitor flash-sale narrative      -> innocent; NO structured footprint; reject

The decoy has zero structured footprint on purpose: that is why it is rejectable. It
lives only in the evidence trail (evidence.py), tempting a naive explanation; the
skeptic's control/heterogeneity test kills it because the damage is concentrated in
one seller, not market-wide.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _recognized(df: pd.DataFrame) -> pd.Series:
    ok = df["order_status"].isin(["delivered", "shipped", "invoiced"])
    return (df["price"] + df["freight_value"]).where(ok, 0.0)


def _derive_window(df: pd.DataFrame, length_days: int = 15) -> tuple[pd.Timestamp, pd.Timestamp]:
    lo, hi = df["order_purchase_date"].min(), df["order_purchase_date"].max()
    span = (hi - lo).days
    w0 = lo + pd.Timedelta(days=int(span * 0.72))
    return w0, w0 + pd.Timedelta(days=length_days)


def inject_anomalies(df: pd.DataFrame,
                     window: tuple[str, str] | None = None,
                     target_seller: str | None = None,
                     target_category: str = "health_beauty",
                     seed: int = 7) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
    df = df.copy()
    if window is None:
        w0, w1 = _derive_window(df)
    else:
        w0, w1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    in_win = (df["order_purchase_date"] >= w0) & (df["order_purchase_date"] <= w1)

    # pick the biggest in-window seller as the culprit if not specified
    if target_seller is None:
        rec = _recognized(df[in_win]).groupby(df.loc[in_win, "seller_id"]).sum()
        target_seller = str(rec.idxmax())
    if target_category not in set(df["category"]):
        catrec = _recognized(df[in_win]).groupby(df.loc[in_win, "category"]).sum()
        target_category = str(catrec.sort_values().index[len(catrec) // 2])  # a mid-size one

    rev_before = float(_recognized(df[in_win]).sum())

    # ---- PRIMARY: target seller delivery collapse -----------------------------
    b = in_win & (df["seller_id"] == target_seller)
    bi = df.index[b]
    df.loc[bi, "actual_days"] = df.loc[bi, "actual_days"] + rng.integers(10, 18, size=len(bi))
    df.loc[bi, "on_time"] = df.loc[bi, "actual_days"] <= df.loc[bi, "promised_days"]
    rev_mask = bi[df.loc[bi, "review_score"].notna()]
    df.loc[rev_mask, "review_score"] = np.clip(rng.normal(2.0, 0.6, size=len(rev_mask)), 1, 5).round(1)
    df.loc[rev_mask, "review_text"] = "Delivery was extremely late, very disappointed."
    cancel_b = rng.random(len(bi)) < 0.45
    df.loc[bi[cancel_b], ["order_status", "delivered"]] = ["canceled", False]

    # ---- MINOR: target category supplier stockout -----------------------------
    hb = in_win & (df["category"] == target_category)
    hbi = df.index[hb]
    cancel_hb = rng.random(len(hbi)) < 0.11
    df.loc[hbi[cancel_hb], ["order_status", "delivered"]] = ["canceled", False]

    rev_after = float(_recognized(df[in_win]).sum())

    # ---- realized attribution for the answer key (before churn touches the index)
    clean_rec = (df["price"] + df["freight_value"]).where(in_win, 0.0)
    damaged_rec = _recognized(df).where(in_win, 0.0)
    lost = clean_rec - damaged_rec
    total_lost = float(lost.sum()) or 1.0
    seller_lost = float(lost[b].sum())
    cat_lost = float(lost[hb & (df["seller_id"] != target_seller)].sum())

    # ---- CHURN (lagged): burned customers reorder less for 3 weeks after the window
    # gives repeat_purchase_rate a dip AFTER the window (the lagging KPI in the chain)
    hit = df.loc[b, "customer_unique_id"].unique()
    post = ((df["order_purchase_date"] > w1) & (df["order_purchase_date"] <= w1 + pd.Timedelta(days=21))
            & df["customer_unique_id"].isin(hit))
    posti = df.index[post]
    churn = rng.random(len(posti)) < 0.55
    df = df.drop(posti[churn]).reset_index(drop=True)

    ground_truth = {
        "window": [str(w0.date()), str(w1.date())],
        "trigger_kpi": "net_revenue",
        "revenue_recognized_before_damage": round(rev_before, 2),
        "revenue_recognized_after_damage": round(rev_after, 2),
        "total_revenue_lost": round(total_lost, 2),
        "causes": [
            {"id": "primary", "role": "primary_cause", "type": "delivery_degradation",
             "entity": target_seller,
             "kpi_chain": ["on_time_delivery_rate", "avg_review_score",
                           "repeat_purchase_rate", "net_revenue"],
             "explains_share": round(seller_lost / total_lost, 3),
             "expect": "crowned #1; survives temporal+control+counterfactual"},
            {"id": "minor", "role": "minor_driver", "type": "supplier_stockout",
             "entity": f"category:{target_category}",
             "explains_share": round(cat_lost / total_lost, 3),
             "expect": "mentioned as secondary; NOT crowned"},
            {"id": "decoy", "role": "decoy", "type": "competitor_flash_sale",
             "entity": "market_wide_narrative", "structured_footprint": False,
             "explains_share": 0.0,
             "expect": "REJECTED by skeptic: damage concentrated in one seller, "
                       "not market-wide; no counterfactual support."},
        ],
    }
    return df, ground_truth


def inject_ambiguous(df: pd.DataFrame, window: tuple[str, str] | None = None,
                     seed: int = 11) -> tuple[pd.DataFrame, dict]:
    """A genuinely ambiguous event: a diffuse, platform-wide revenue dip with NO single-
    seller concentration and contradictory evidence. The engine should refuse to attribute
    a cause here (brief #5) — the honest mirror of the decoy."""
    rng = np.random.default_rng(seed)
    df = df.copy()
    if window is None:
        lo, hi = df["order_purchase_date"].min(), df["order_purchase_date"].max()
        span = (hi - lo).days
        w0 = lo + pd.Timedelta(days=int(span * 0.40))
        w1 = w0 + pd.Timedelta(days=10)
    else:
        w0, w1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    in_win = (df["order_purchase_date"] >= w0) & (df["order_purchase_date"] <= w1)
    idx = df.index[in_win]
    # cancel ~9% of ALL orders uniformly -> material but diffuse (no concentration)
    hit = rng.random(len(idx)) < 0.09
    df.loc[idx[hit], ["order_status", "delivered"]] = ["canceled", False]
    record = {"window": [str(w0.date()), str(w1.date())], "type": "diffuse_platform_dip",
              "entity": "no single concentration", "expect": "engine ABSTAINS (INSUFFICIENT) — "
              "material but diffuse; contradictory evidence; no seller/category explains it."}
    return df, record
