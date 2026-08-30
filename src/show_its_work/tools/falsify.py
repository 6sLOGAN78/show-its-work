"""Falsification tools — the skeptic's arsenal. ⭐ the differentiator.

These turn "these moved together" into "this survived attempts to kill it":
  test_temporal_alignment  did the cause move at/before the effect?
  compare_control_group     is the damage concentrated in the entity, or market-wide?  (kills the decoy)
  counterfactual_estimate   how much of the delta remains if we remove this group?
All deterministic; the LLM only decides which to run and reads the verdicts.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..metrics import RECOGNIZED_STATUS, kpi_series, load_orders


@dataclass
class TemporalTest:
    cause: str
    effect: str
    cause_onset: str | None
    effect_onset: str | None
    passed: bool                 # cause onset at/before effect onset
    detail: str


@dataclass
class ControlTest:
    entity: str
    treated_delta_pct: float
    control_delta_pct: float
    concentrated: bool           # damage concentrated in the entity (not market-wide)
    passed: bool                 # supports an entity-specific cause / refutes market-wide
    detail: str


@dataclass
class Counterfactual:
    dimension: str
    excluded: str
    total_delta: float
    remaining_delta: float
    explained_share: float       # share of the delta attributable to the excluded group
    detail: str


def _onset(series: pd.Series, w0, w1, k: float = 1.5) -> str | None:
    s = series.dropna()
    pre = s.loc[:w0].iloc[:-1]
    if len(pre) < 7:
        return None
    thr = pre.mean() - k * pre.std()
    scan = s.loc[w0 - pd.Timedelta(days=5):w1]
    hit = scan[scan < thr]
    return str(hit.index[0].date()) if len(hit) else None


def test_temporal_alignment(cause_kpi: str, effect_kpi: str, window,
                            region=None) -> TemporalTest:
    w0, w1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    c_on = _onset(kpi_series(cause_kpi, region=region), w0, w1)
    e_on = _onset(kpi_series(effect_kpi, region=region), w0, w1)
    if c_on is None or e_on is None:
        return TemporalTest(cause_kpi, effect_kpi, c_on, e_on, False,
                            "could not locate an onset for one series")
    passed = pd.Timestamp(c_on) <= pd.Timestamp(e_on)
    rel = "before/with" if passed else "AFTER"
    return TemporalTest(cause_kpi, effect_kpi, c_on, e_on, passed,
                        f"{cause_kpi} onset {c_on} is {rel} {effect_kpi} onset {e_on}")


_RATE_COL = {"on_time_delivery_rate": "on_time", "avg_review_score": "review_score"}


def _delta_fn(kpi: str, w0, w1, baseline_days: int):
    """Return a function frame -> (window - baseline) for the given KPI, and a formatter."""
    wl = len(pd.date_range(w0, w1))

    def slice_wb(frame):
        win = frame[(frame["order_purchase_date"] >= w0) & (frame["order_purchase_date"] <= w1)]
        base = frame[(frame["order_purchase_date"] >= w0 - pd.Timedelta(days=baseline_days)) &
                     (frame["order_purchase_date"] < w0)]
        return win, base

    if kpi == "net_revenue":
        def delta(frame):
            ok = frame[frame["order_status"].isin(RECOGNIZED_STATUS)]
            win, base = slice_wb(ok)
            return (win["price"] + win["freight_value"]).sum() - \
                   (base["price"] + base["freight_value"]).sum() / baseline_days * wl
        return delta, lambda v: f"{v:,.0f}", "shortfall"

    col = _RATE_COL.get(kpi)
    if col is None:
        raise KeyError(f"falsification not supported for KPI '{kpi}'")

    def delta(frame):
        f = frame if col != "on_time" else frame[frame["delivered"]]
        win, base = slice_wb(f)
        wv = win[col].mean() if len(win) else 0.0
        bv = base[col].mean() if len(base) else 0.0
        return (wv - bv) if pd.notna(wv) and pd.notna(bv) else 0.0
    return delta, lambda v: f"{v:+.3f}", "rate move"


def compare_control_group(entity: str, window, dimension: str = "seller_id",
                          kpi: str = "net_revenue", baseline_days: int = 28) -> ControlTest:
    """Treated = the entity; control = everyone else. If the entity collapsed while
    controls held, the damage is concentrated -> an entity cause is supported and a
    market-wide narrative (the decoy) is refuted. KPI-aware (revenue or rate)."""
    df = load_orders()
    w0, w1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    delta, _, _ = _delta_fn(kpi, w0, w1, baseline_days)

    def rel(frame):
        d = delta(frame)
        if kpi == "net_revenue":
            ok = frame[frame["order_status"].isin(RECOGNIZED_STATUS)]
            base = ok[(ok["order_purchase_date"] >= w0 - pd.Timedelta(days=baseline_days)) &
                      (ok["order_purchase_date"] < w0)]
            bv = (base["price"] + base["freight_value"]).sum() / baseline_days * len(pd.date_range(w0, w1))
            return d / bv if bv else 0.0
        return d                                    # rate KPIs: absolute move (already comparable)

    treated = rel(df[df[dimension] == entity])
    control = rel(df[df[dimension] != entity])
    thr = 0.05 if kpi == "net_revenue" else 0.03
    concentrated = treated < control - thr and treated < -(2 * thr)
    unit = "%" if kpi == "net_revenue" else ""
    fmt = (lambda v: f"{v:+.1%}") if kpi == "net_revenue" else (lambda v: f"{v:+.3f}")
    detail = (f"{entity} moved {fmt(treated)} vs the rest of the market {fmt(control)}. "
              + ("Damage is concentrated here, not market-wide."
                 if concentrated else "Not clearly concentrated."))
    return ControlTest(entity, round(treated, 4), round(control, 4), concentrated,
                       concentrated, detail)


def counterfactual_estimate(dimension: str, excluded: str, window,
                            kpi: str = "net_revenue", baseline_days: int = 28) -> Counterfactual:
    """Share of the delta attributable to `excluded` = 1 - (delta without it / total delta)."""
    df = load_orders()
    w0, w1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    delta, fmt, word = _delta_fn(kpi, w0, w1, baseline_days)
    total = delta(df)
    remaining = delta(df[df[dimension] != excluded])
    share = 1 - remaining / total if total else 0.0
    share = max(-1.0, min(1.0, share))              # cap for display sanity
    detail = (f"Excluding {excluded}, the {kpi} {word} goes from {fmt(total)} to "
              f"{fmt(remaining)} — it explains {share:.0%} of the move.")
    return Counterfactual(dimension, excluded, round(total, 3), round(remaining, 3),
                          round(float(share), 3), detail)
