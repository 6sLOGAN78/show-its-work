"""Evaluation harness — scores the engine against the planted answer key.

Because we constructed the ground truth (data/synthetic/ground_truth.json), we can grade
objectively. These are the numbers to put on a slide:
  root-cause top-1     did the flagship crown the planted primary cause?
  decoy rejection      did the skeptic reject the innocent market-wide narrative?
  abstention correct   did the ambiguous / sparse / noise cases refuse to guess?
  false-alert rate     over quiet windows, how often did the gate wrongly fire?
  citation precision    fraction of cited sentences whose IDs all resolve

Run:  python -m show_its_work.eval
"""
from __future__ import annotations

import json

import pandas as pd

from .config import GROUND_TRUTH
from .engine import investigate


def _primary(inv):
    surv = [h for h in inv.hypotheses if h.status.value == "survived"
            and "market-wide" not in h.claim.lower()]
    surv.sort(key=lambda h: h.explained_share, reverse=True)
    return surv[0] if surv else None


def _decoy(inv):
    return next((h for h in inv.hypotheses if "market-wide" in h.claim.lower()), None)


def run_eval() -> dict:
    gt = json.loads(GROUND_TRUTH.read_text())
    planted = gt["causes"][0]["entity"]
    results = {}

    # 1) flagship: root-cause top-1 + decoy rejection + confidence
    r = investigate("Why did net revenue drop last week?", "revenue_analyst")
    prim = _primary(r.investigation)
    decoy = _decoy(r.investigation)
    results["root_cause_top1"] = bool(prim and planted in prim.claim)
    results["primary_confidence"] = r.investigation.verdict.level.value
    results["decoy_rejected"] = bool(decoy and decoy.status.value == "killed")
    results["citation_clean"] = r.verification["clean"]

    # 2) abstention correctness (must NOT confidently attribute)
    abstains = {
        "ambiguous_diffuse": investigate("why did revenue move mid-March?", "revenue_analyst",
                                         window=tuple(gt["ambiguous_case"]["window"])),
        "sparse_new_kpi": investigate("revenue in first days?", "revenue_analyst",
                                      window=("2024-01-02", "2024-01-12")),
    }
    results["abstained_when_it_should"] = {
        k: v.investigation.verdict.level.value == "INSUFFICIENT" for k, v in abstains.items()}

    # 3) false-alert rate over quiet windows (want ~0 material)
    quiet = [("2024-02-05", "2024-02-20"), ("2024-01-15", "2024-01-30"),
             ("2024-02-19", "2024-03-05")]
    from .tools import detect_change
    fired = sum(detect_change("net_revenue", w).material for w in quiet)
    results["false_alert_rate"] = f"{fired}/{len(quiet)}"

    # 4) persona differentiation (same Q, different memo/entitlement)
    ops = investigate("Why did net revenue drop last week?", "ops_lead")
    results["persona_differentiated"] = (ops.investigation.kpi != r.investigation.kpi
                                         and len(ops.investigation.redactions) > 0)
    return results


def print_scorecard() -> None:
    r = run_eval()
    print("=" * 60)
    print("  SHOW ITS WORK — evaluation scorecard")
    print("=" * 60)
    def row(k, v, ok): print(f"  {'✓' if ok else '✗'}  {k:34} {v}")
    row("root-cause top-1 (crowned planted cause)", r["root_cause_top1"], r["root_cause_top1"])
    row("primary confidence", r["primary_confidence"], r["primary_confidence"] == "HIGH")
    row("decoy rejected (skeptic killed it)", r["decoy_rejected"], r["decoy_rejected"])
    row("citation verification clean", r["citation_clean"], r["citation_clean"])
    for k, v in r["abstained_when_it_should"].items():
        row(f"abstained: {k}", v, v)
    row("false-alert rate (quiet windows)", r["false_alert_rate"], r["false_alert_rate"].startswith("0/"))
    row("persona-differentiated output", r["persona_differentiated"], r["persona_differentiated"])
    print("=" * 60)


if __name__ == "__main__":
    print_scorecard()
