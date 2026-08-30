"""Thin HTTP API over the engine — serves the web UI and returns investigations as JSON.

Run:  uvicorn web.api:app --port 8533   (or: python -m show_its_work.run serve)
The engine does all the work; this only serialises it for the frontend.
"""
from __future__ import annotations

from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from show_its_work.config import LLMConfig, RunConfig
from show_its_work.engine import investigate
from show_its_work.memory import CausalMemory
from show_its_work.metrics import kpi_series
from show_its_work.semantics import load_personas, load_semantic_contract
from show_its_work.tools import decompose_drivers

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="Show Its Work")


class Ask(BaseModel):
    question: str = "Why did our net revenue drop last week?"
    persona: str = "revenue_analyst"
    window: list[str] | None = None
    provider: str | None = None


SCENARIOS = [
    {"id": "flagship", "code": "SCN_01", "label": "Revenue drop — full analysis",
     "question": "Why did our net revenue drop last week?", "persona": "revenue_analyst", "window": None},
    {"id": "entitlement", "code": "SCN_02", "label": "Same question, Ops Lead — role-gated",
     "question": "Why did our net revenue drop last week?", "persona": "ops_lead", "window": None},
    {"id": "ambiguous", "code": "SCN_03", "label": "A diffuse move — must abstain",
     "question": "Why did revenue move in mid-March?", "persona": "revenue_analyst",
     "window": ["2024-03-12", "2024-03-22"]},
    {"id": "sparse", "code": "SCN_04", "label": "A newly launched window — sparse",
     "question": "How is revenue in the first days?", "persona": "revenue_analyst",
     "window": ["2024-01-02", "2024-01-12"]},
    {"id": "noise", "code": "SCN_05", "label": "A quiet week — gate ignores it",
     "question": "Why did revenue move?", "persona": "revenue_analyst",
     "window": ["2024-02-05", "2024-02-20"]},
]


def _series(kpi: str, window, region=None) -> dict:
    s = kpi_series(kpi, region=region).dropna()
    return {"kpi": kpi,
            "dates": [d.strftime("%Y-%m-%d") for d in s.index],
            "values": [round(float(v), 3) for v in s.values],
            "window": [str(window[0]), str(window[1])]}


def to_payload(r) -> dict:
    inv = r.investigation
    c = load_semantic_contract()
    drivers = []
    try:
        for d in decompose_drivers(inv.kpi, tuple(inv.period), "seller_id")[:6]:
            drivers.append({"group": d.group, "contribution": d.contribution,
                            "share": d.contribution_share, "direction": d.direction})
    except Exception:
        pass
    try:
        fr = c.source_freshness(inv.kpi); lineage = c.kpi(inv.kpi).lineage
    except Exception:
        fr, lineage = {}, []
    return {
        "question": inv.trigger, "persona": inv.persona, "analysis_kpi": inv.kpi,
        "period": inv.period,
        "verdict": {"level": inv.verdict.level.value, "rationale": inv.verdict.rationale,
                    "missing_data": inv.verdict.missing_data} if inv.verdict else None,
        "redactions": inv.redactions, "memo": inv.memo, "notes": inv.notes,
        "facts": [{"id": f.id, "statement": f.statement, "producer": f.provenance.producer.value,
                   "tool": f.provenance.tool, "value": f.value, "unit": f.unit} for f in inv.facts],
        "evidence": [{"id": e.id, "source": e.source, "text": e.text, "score": e.score}
                     for e in inv.evidence],
        "hypotheses": [{"id": h.id, "claim": h.claim, "mechanism": h.mechanism,
                        "status": h.status.value, "explained_share": h.explained_share,
                        "origin": h.origin.value,
                        "attacks": [{"test": a.test, "passed": a.passed, "detail": a.detail}
                                    for a in h.attacks]} for h in inv.hypotheses],
        "actions": [{"driver": a.driver, "lever": a.lever, "action": a.action,
                     "expected_impact": a.expected_impact, "owner": a.owner,
                     "confidence": a.confidence.value, "monitoring_plan": a.monitoring_plan}
                    for a in inv.actions],
        "drivers": drivers,
        "series": _series(inv.kpi, inv.period),
        "telemetry": r.telemetry, "telemetry_events": r.telemetry_events,
        "verification": r.verification,
        "freshness": fr, "lineage": lineage,
    }


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/bootstrap")
def bootstrap():
    personas = load_personas()
    c = load_semantic_contract()
    return {"scenarios": SCENARIOS,
            "personas": [{"key": k, "label": p.label, "goal": p.goal} for k, p in personas.items()],
            "kpis": [{"name": n, "label": c.kpi(n).label, "access": c.kpi(n).access} for n in c.kpis]}


@app.post("/api/investigate")
def api_investigate(ask: Ask):
    window = tuple(ask.window) if ask.window else None
    llm_kwargs = {"provider": ask.provider} if ask.provider else {}
    cfg = RunConfig(llm=LLMConfig(**llm_kwargs))
    r = investigate(ask.question, ask.persona, window=window, cfg=cfg)
    return JSONResponse(to_payload(r))


@app.get("/api/memory")
def api_memory():
    return {"edges": CausalMemory().edges()}


app.mount("/static", StaticFiles(directory=STATIC), name="static")
