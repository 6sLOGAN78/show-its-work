"""Build the demo dataset: source -> inject anomaly -> evidence trail -> persist.

Uses real Olist if data/raw/ has it, else the synthetic generator. Writes:
  data/synthetic/orders_fact.parquet   the canonical order table (all 4 KPIs derive from it)
  data/synthetic/evidence.parquet      the unstructured trail
  data/synthetic/ground_truth.json     the answer key (planted causes + decoy)

Run:  python -m show_its_work.data.build
"""
from __future__ import annotations

import json

from ..config import GROUND_TRUTH, SYNTH, ensure_dirs
from . import olist
from .evidence import generate_evidence
from .inject import inject_anomalies, inject_ambiguous
from .synth import generate_clean


def build(seed: int = 7) -> dict:
    ensure_dirs()
    try:
        tables = olist.load()
        clean = olist.to_orders_fact(tables)
        source = "olist_real"
    except FileNotFoundError:
        clean = generate_clean(seed=seed)
        source = "synthetic"

    damaged, gt = inject_anomalies(clean, seed=seed)
    damaged, amb = inject_ambiguous(damaged, seed=seed)   # a second, DIFFUSE event
    gt["ambiguous_case"] = amb
    gt["data_source"] = source
    evidence = generate_evidence(damaged, gt, seed=seed)

    damaged.to_parquet(SYNTH / "orders_fact.parquet", index=False)
    evidence.to_parquet(SYNTH / "evidence.parquet", index=False)
    GROUND_TRUTH.write_text(json.dumps(gt, indent=2, default=str))

    print(f"[build] source={source}  orders={len(damaged):,}  evidence={len(evidence)}")
    print(f"[build] window={gt['window']}  revenue_lost=~{gt['total_revenue_lost']:,.0f}")
    for c in gt["causes"]:
        print(f"        {c['role']:14} {c['entity']:26} share={c['explains_share']}")
    print(f"        ambiguous_case {amb['window']} (diffuse; engine should abstain)")
    print(f"[build] wrote -> {SYNTH}/  (orders_fact.parquet, evidence.parquet, ground_truth.json)")
    return gt


if __name__ == "__main__":
    build()
