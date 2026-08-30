"""detect_change — the SIGNAL GATE. Deterministic; runs before any LLM call.

Separates a real, material move from normal noise (brief Q1). Deseasonalises weekly
structure, then runs a robust (MAD) mean-shift z-test of the window against its LOCAL
prior baseline, and applies the governed materiality thresholds (statistical AND
business). If it isn't significant, the whole investigation stops here — which is what
kills alert fatigue and the bulk of LLM cost.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..metrics import kpi_series
from ..semantics import load_semantic_contract


@dataclass
class ChangeSignal:
    kpi: str
    window: tuple[str, str]
    baseline_value: float
    window_value: float
    delta: float
    delta_pct: float
    abs_delta_period: float          # total shortfall over the window (business impact)
    zscore: float
    significant: bool                # passed the statistical gate
    material: bool                   # passed statistical AND business gate
    direction: str                   # "down" | "up" | "flat"
    low_history: bool = False        # too few pre-window points to judge (sparse/new KPI)
    method: str = "STL residual z-score + governed materiality"
    notes: list[str] = field(default_factory=list)


def _deseasonalize(s: pd.Series) -> pd.Series:
    """Strip weekly seasonality by subtracting day-of-week means (for daily series)."""
    if not _is_daily(s) or len(s) < 21:
        return s
    dow = s.index.dayofweek
    eff = s.groupby(dow).transform("mean")
    return s - eff


def _zscore(series: pd.Series, w0, w1, baseline_days: int = 28) -> tuple[float, str]:
    """Mean-shift z-test vs the LOCAL prior baseline. Deseasonalise weekly structure, then
    compare the window's residual mean to the immediately-preceding baseline's residual
    center, scaled by that baseline's robust (MAD) daily noise. Local baseline avoids
    trend/monthly leakage; MAD keeps a prior anomaly from desensitising us; the SE shrinks
    with window length because a sustained shift is easier to see than a one-day spike."""
    s = series.dropna()
    win = s.loc[w0:w1]
    pre_all = s.loc[:w0].iloc[:-1]
    if len(pre_all) < 14 or len(win) == 0:
        return 0.0, "insufficient-history"
    ds = _deseasonalize(s)
    base_r = ds.loc[w0 - pd.Timedelta(days=baseline_days):w0 - pd.Timedelta(days=1)]
    win_r = ds.loc[w0:w1]
    if len(base_r) < 7:
        base_r = ds.loc[:w0].iloc[:-1]
    center = base_r.median()
    noise = 1.4826 * (base_r - center).abs().median()
    if not noise or np.isnan(noise):
        noise = base_r.std() or 1e-9
    n_eff = min(len(win_r), 10)                 # discount autocorrelation (effective n)
    se = noise / np.sqrt(n_eff)
    z = (win_r.mean() - center) / se
    return float(z), "deseasonalized robust (MAD) mean-shift z-test"


def _is_daily(s: pd.Series) -> bool:
    if len(s.index) < 3:
        return False
    return pd.infer_freq(s.index[:10]) in ("D", None) and (s.index.to_series().diff().median() <= pd.Timedelta(days=2))


def detect_change(kpi: str, window: tuple[str, str], baseline_days: int = 28,
                  region: list[str] | None = None) -> ChangeSignal:
    spec = load_semantic_contract().kpi(kpi)
    s = kpi_series(kpi, region=region).dropna()
    w0, w1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    win = s.loc[w0:w1]
    base = s.loc[w0 - pd.Timedelta(days=baseline_days):w0 - pd.Timedelta(days=1)]
    bval, wval = float(base.mean()), float(win.mean())
    delta = wval - bval
    pct = delta / bval if bval else 0.0
    abs_delta_period = delta * len(win)
    z, method = _zscore(s, w0, w1, baseline_days)
    low_history = method == "insufficient-history"

    m = spec.materiality
    significant = abs(z) >= m.get("z_threshold", 2.0)
    business = abs(abs_delta_period) > m.get("min_abs_delta", 0.0) or abs(pct) > m.get("min_pct", 0.05)
    material = significant and business
    direction = "down" if delta < 0 else ("up" if delta > 0 else "flat")

    notes = []
    if not significant:
        notes.append(f"|z|={abs(z):.2f} < {m.get('z_threshold')} -> within normal variation; gate stops here.")
    elif not business:
        notes.append("statistically real but below business materiality; low priority.")
    return ChangeSignal(kpi=kpi, window=(str(w0.date()), str(w1.date())),
                        baseline_value=round(bval, 3), window_value=round(wval, 3),
                        delta=round(delta, 3), delta_pct=round(pct, 4),
                        abs_delta_period=round(abs_delta_period, 2), zscore=round(z, 2),
                        significant=significant, material=material, direction=direction,
                        low_history=low_history,
                        method=f"{method} + governed materiality", notes=notes)
