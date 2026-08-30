"""Synthetic evidence trail — the unstructured half of the join.

Generates support tickets, CRM notes, ops/release logs, and external news that
reference the planted causes (and the innocent decoy), plus unrelated noise so
retrieval has to actually discriminate. Deterministic given a seed.

Emitted as an `evidence` frame: [id, source, text, timestamp, entity_ids, category].
entity_ids let the falsification tools line evidence up against structured movements.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

_LATE_TICKETS = [
    "Customer reports order from {s} arrived {d} days late. Very frustrated, wants refund.",
    "Escalation: {s} shipment stuck, delivery estimate missed by {d} days.",
    "Repeat complaint about {s} — package delayed again, {d} days past promised date.",
    "Where is my order? {s} tracking hasn't updated in {d} days.",
    "Angry customer, {s} delivery {d} days late, threatening to leave a 1-star review.",
]
_OPS_PRIMARY = [
    "Ops incident: {s} relocated its primary warehouse May 09; fulfilment backlog through May 24.",
    "Carrier handoff failures at {s} hub — outbound scans delayed ~2 weeks starting mid-May.",
    "{s} staffing shortage in dispatch created a processing-time spike from May 10.",
]
_CRM_MINOR = [
    "CRM note: supplier stockout on health_beauty SKUs; ~2-week fulfilment gap, several cancellations.",
    "Category team flags health_beauty inventory shortfall mid-May; orders cancelled where unfulfillable.",
]
_DECOY_NEWS = [
    "MegaStore (competitor) launched a national flash sale May 12-15 with aggressive discounts.",
    "Industry press: e-commerce price war heats up as MegaStore undercuts on electronics this week.",
]
_DECOY_CRM = [
    "Sales speculation: last week's revenue dip might just be the MegaStore promo pulling demand.",
]
_NOISE = [
    "Marketing: new loyalty email campaign scheduled for next quarter.",
    "IT maintenance window completed on payments gateway, no incidents.",
    "Routine review: {s} packaging feedback generally positive this month.",
    "HR: dispatch team training day booked for June.",
    "Finance: freight cost renegotiation with carrier ongoing, no change yet.",
]


def generate_evidence(df: pd.DataFrame, ground_truth: dict, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    w0, w1 = pd.Timestamp(ground_truth["window"][0]), pd.Timestamp(ground_truth["window"][1])
    causes = {c["role"]: c for c in ground_truth["causes"]}
    primary = causes["primary_cause"]["entity"]
    minor_cat = causes["minor_driver"]["entity"].split(":", 1)[-1]
    rows: list[tuple] = []
    n = 0

    def add(source, text, ts, entities, category):
        nonlocal n
        rows.append((f"D{n:03d}", source, text, ts, entities, category))
        n += 1

    def rand_ts(a, b):
        span = (b - a).days
        return a + pd.Timedelta(days=int(rng.integers(0, max(1, span))),
                                hours=int(rng.integers(0, 24)))

    # PRIMARY: many late-delivery tickets for house_bravos in-window (the loud signal)
    for _ in range(28):
        t = _LATE_TICKETS[rng.integers(len(_LATE_TICKETS))]
        d = int(rng.integers(10, 20))
        add("ticket", t.format(s=primary, d=d), rand_ts(w0, w1),
            [primary], "late_delivery")
    # PRIMARY mechanism: a few ops/release logs (the WHY)
    for txt in _OPS_PRIMARY:
        add("release", txt.format(s=primary), rand_ts(w0, w0 + pd.Timedelta(days=3)),
            [primary], "ops_incident")

    # MINOR: health_beauty stockout CRM notes
    for txt in _CRM_MINOR:
        add("crm", txt.replace("health_beauty", minor_cat), rand_ts(w0, w1), [f"category:{minor_cat}"], "stockout")

    # DECOY: competitor flash-sale news + speculative CRM (temporally aligned, innocent)
    for txt in _DECOY_NEWS:
        add("news", txt, rand_ts(w0, w0 + pd.Timedelta(days=5)), ["market_wide_narrative"], "competitor")
    for txt in _DECOY_CRM:
        add("crm", txt, rand_ts(w0, w1), ["market_wide_narrative"], "competitor")

    # A handful of genuine negative reviews (structured<->unstructured join), sampled
    late = df[(df["seller_id"] == primary) &
              (df["order_purchase_date"] >= w0) & (df["order_purchase_date"] <= w1) &
              (df["review_text"].notna())]
    for _, r in late.sample(min(10, len(late)), random_state=seed).iterrows():
        add("review", r["review_text"], r["review_creation_date"], ["house_bravos"], "review")

    # NOISE: unrelated items across the whole timeline (retrieval must ignore these)
    lo, hi = df["order_purchase_date"].min(), df["order_purchase_date"].max()
    for _ in range(20):
        txt = _NOISE[rng.integers(len(_NOISE))]
        s = rng.choice(["house_stark", "house_tully", "house_martell"])
        add("crm", txt.format(s=s), rand_ts(lo, hi), [], "noise")

    # CONTRADICTORY evidence for the ambiguous window (brief #5): no clear story
    amb = ground_truth.get("ambiguous_case")
    if amb:
        a0, a1 = pd.Timestamp(amb["window"][0]), pd.Timestamp(amb["window"][1])
        add("crm", "Support suspects a payments-gateway glitch caused dropped orders this week.",
            rand_ts(a0, a1), ["ambiguous"], "contradictory")
        add("crm", "Ops thinks it was a spell of bad weather across regions, not a system issue.",
            rand_ts(a0, a1), ["ambiguous"], "contradictory")
        add("ticket", "A few customers reported checkout failures, but most orders went through fine.",
            rand_ts(a0, a1), ["ambiguous"], "contradictory")

    ev = pd.DataFrame(rows, columns=["id", "source", "text", "timestamp", "entity_ids", "category"])
    ev["timestamp"] = pd.to_datetime(ev["timestamp"])
    return ev.sort_values("timestamp").reset_index(drop=True)
