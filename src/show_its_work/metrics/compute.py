"""Deterministic KPI computation from the canonical order table.

Every KPI series here is produced by pandas per the governed semantic-contract
definition — never by an LLM. Row-level entitlement (region filter) is applied at
this layer so a persona physically cannot compute outside its scope.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from ..config import SYNTH

RECOGNIZED_STATUS = ["delivered", "shipped", "invoiced"]


@lru_cache(maxsize=1)
def load_orders() -> pd.DataFrame:
    fp = SYNTH / "orders_fact.parquet"
    if not fp.exists():
        raise FileNotFoundError("No dataset. Run:  python -m show_its_work.data.build")
    return pd.read_parquet(fp)


@lru_cache(maxsize=1)
def load_evidence() -> pd.DataFrame:
    fp = SYNTH / "evidence.parquet"
    if not fp.exists():
        raise FileNotFoundError("No evidence. Run:  python -m show_its_work.data.build")
    return pd.read_parquet(fp)


def _scope(df: pd.DataFrame, region: list[str] | None) -> pd.DataFrame:
    return df if region is None else df[df["region"].isin(region)]


def kpi_series(name: str, df: pd.DataFrame | None = None,
               region: list[str] | None = None) -> pd.Series:
    """Return the KPI as a time-indexed series (daily; repeat_purchase_rate is weekly).

    `region` applies row-level security (entitlement). Deterministic and cached-friendly.
    """
    df = load_orders() if df is None else df
    df = _scope(df, region)

    if name == "net_revenue":
        ok = df[df["order_status"].isin(RECOGNIZED_STATUS)]
        s = (ok.assign(rev=ok["price"] + ok["freight_value"])
                .groupby(ok["order_purchase_date"].dt.date)["rev"].sum())
        s.index = pd.to_datetime(s.index)
        return s.asfreq("D", fill_value=0.0).rename("net_revenue")

    if name == "on_time_delivery_rate":
        d = df[df["delivered"]]
        s = d.groupby(d["order_purchase_date"].dt.date)["on_time"].mean()
        s.index = pd.to_datetime(s.index)
        return s.asfreq("D").rename("on_time_delivery_rate")

    if name == "avg_review_score":
        r = df[df["review_score"].notna() & df["review_creation_date"].notna()]
        s = r.groupby(r["review_creation_date"].dt.date)["review_score"].mean()
        s.index = pd.to_datetime(s.index)
        return s.asfreq("D").rename("avg_review_score")

    if name == "repeat_purchase_rate":
        return _repeat_rate_weekly(df)

    raise KeyError(f"Unknown KPI '{name}'")


def _repeat_rate_weekly(df: pd.DataFrame) -> pd.Series:
    """Weekly: share of active customers who had a prior order in the trailing 30 days."""
    o = df[["customer_unique_id", "order_purchase_date"]].sort_values("order_purchase_date").copy()
    o["prev"] = o.groupby("customer_unique_id")["order_purchase_date"].shift(1)
    o["is_repeat"] = (o["order_purchase_date"] - o["prev"]).dt.days.le(30)
    o["week"] = o["order_purchase_date"].dt.to_period("W").dt.start_time
    g = o.groupby("week").agg(active=("customer_unique_id", "nunique"),
                              repeat=("is_repeat", "sum"))
    return (g["repeat"] / g["active"]).rename("repeat_purchase_rate")
