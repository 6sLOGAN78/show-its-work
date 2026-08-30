"""decompose_drivers + check_mix_shift — deterministic driver attribution.

decompose_drivers: waterfall attribution of a KPI's move across a dimension
(seller / category / region). For net_revenue this is exact additive contribution;
for rate KPIs it is a within-group approximation, clearly flagged.

check_mix_shift: Simpson's-paradox guard — splits the aggregate move into a
within-group effect and a mix (composition) effect, so we never blame a driver for
what is actually a change in the mix of business.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..metrics import RECOGNIZED_STATUS, load_orders


@dataclass
class Contribution:
    dimension: str
    group: str
    contribution: float              # signed, in KPI units over the window
    contribution_share: float        # fraction of total delta
    window_value: float
    baseline_value: float
    direction: str


@dataclass
class MixReport:
    kpi: str
    dimension: str
    aggregate_delta: float
    within_effect: float
    mix_effect: float
    simpson_risk: bool
    note: str
    detail: list[dict] = field(default_factory=list)


def _win_base(df, w0, w1, baseline_days):
    win = df[(df["order_purchase_date"] >= w0) & (df["order_purchase_date"] <= w1)]
    base = df[(df["order_purchase_date"] >= w0 - pd.Timedelta(days=baseline_days)) &
              (df["order_purchase_date"] < w0)]
    return win, base, len(pd.date_range(w0, w1)), baseline_days


def decompose_drivers(kpi: str, window, dimension: str = "seller_id",
                      baseline_days: int = 28, region=None, top: int = 6) -> list[Contribution]:
    df = load_orders()
    if region is not None:
        df = df[df["region"].isin(region)]
    w0, w1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    win, base, win_len, base_len = _win_base(df, w0, w1, baseline_days)

    if kpi == "net_revenue":
        def rec(x):
            ok = x[x["order_status"].isin(RECOGNIZED_STATUS)]
            return (ok["price"] + ok["freight_value"]).groupby(ok[dimension]).sum()
        wtot = rec(win)
        btot = rec(base) / base_len * win_len          # scale baseline to window length
        groups = sorted(set(wtot.index) | set(btot.index))
        contrib = {g: float(wtot.get(g, 0.0) - btot.get(g, 0.0)) for g in groups}
        total = sum(contrib.values()) or 1e-9
        out = [Contribution(dimension, g, round(c, 2), round(c / total, 3),
                            round(float(wtot.get(g, 0.0)), 2),
                            round(float(btot.get(g, 0.0)), 2),
                            "down" if c < 0 else "up") for g, c in contrib.items()]
    else:
        # rate KPI: within-group approximation weighted by baseline volume share
        col = {"on_time_delivery_rate": "on_time", "avg_review_score": "review_score"}.get(kpi)
        if col is None:
            raise KeyError(f"decompose_drivers not supported for '{kpi}'")
        wv = win.groupby(dimension)[col].mean()
        bv = base.groupby(dimension)[col].mean()
        wgt = base.groupby(dimension).size() / max(1, len(base))
        groups = sorted(set(bv.index) | set(wv.index))
        contrib = {g: float((wv.get(g, bv.get(g, 0)) - bv.get(g, 0)) * wgt.get(g, 0)) for g in groups}
        total = sum(contrib.values()) or 1e-9
        out = [Contribution(dimension, g, round(c, 4), round(c / total, 3),
                            round(float(wv.get(g, 0)), 3), round(float(bv.get(g, 0)), 3),
                            "down" if c < 0 else "up") for g, c in contrib.items()]

    out.sort(key=lambda c: c.contribution)          # most negative (biggest drag) first
    return out[:top]


def check_mix_shift(kpi: str, window, dimension: str = "category",
                    baseline_days: int = 28) -> MixReport:
    """Split aggregate mean change into within-group vs mix (composition) effects."""
    df = load_orders()
    col = {"on_time_delivery_rate": "on_time", "avg_review_score": "review_score"}.get(kpi)
    if col is None:
        # revenue: use average order value as the "rate" for a mix check
        df = df[df["order_status"].isin(RECOGNIZED_STATUS)].assign(aov=lambda x: x["price"] + x["freight_value"])
        col = "aov"
    w0, w1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    win, base, _, _ = _win_base(df, w0, w1, baseline_days)

    bw = base.groupby(dimension).size() / max(1, len(base))     # baseline weights
    ww = win.groupby(dimension).size() / max(1, len(win))       # window weights
    br = base.groupby(dimension)[col].mean()
    wr = win.groupby(dimension)[col].mean()
    groups = sorted(set(br.index) | set(wr.index))
    within = sum(bw.get(g, 0) * (wr.get(g, br.get(g, 0)) - br.get(g, 0)) for g in groups)
    mix = sum((ww.get(g, 0) - bw.get(g, 0)) * br.get(g, 0) for g in groups)
    agg = float(win[col].mean() - base[col].mean())
    denom = abs(within) + abs(mix) or 1e-9
    simpson = abs(mix) / denom > 0.4
    note = ("mix shift is a large share of the move — attribute with care (Simpson's risk)"
            if simpson else "move is mostly within-group; safe to attribute to drivers")
    detail = [{"group": g, "baseline_weight": round(float(bw.get(g, 0)), 3),
               "window_weight": round(float(ww.get(g, 0)), 3),
               "baseline_rate": round(float(br.get(g, 0)), 3),
               "window_rate": round(float(wr.get(g, 0)), 3)} for g in groups]
    return MixReport(kpi, dimension, round(agg, 4), round(within, 4), round(mix, 4),
                     simpson, note, detail)
