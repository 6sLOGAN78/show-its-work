"""The engine — orchestrates one investigation end to end.

Pipeline (a deterministic proposer/skeptic/judge loop; plain Python, no graph lib):
  intent -> gate -> [entitlement pivot] -> factpack -> propose -> skeptic -> judge
         -> actions -> write -> verify

The gate runs before any hypothesis work; if the move isn't material the run stops with
an honest "within normal variation" (kills alert fatigue + LLM cost). Every stage is
telemetered and tagged LLM/non-LLM.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from .agents import narrative, reasoning
from .agents.reasoning import _Ids
from .config import GROUND_TRUTH, RunConfig
from .entitlements import resolve
from .llm import make_client
from .models import ConfidenceLevel, Fact, Investigation, Producer, Provenance, Verdict
from .semantics import load_personas, load_semantic_contract
from .memory import CausalMemory, EpisodicStore, record_outcome
from .telemetry import Telemetry
from .tools import detect_change


def _default_window() -> tuple[str, str]:
    if GROUND_TRUTH.exists():
        gt = json.loads(GROUND_TRUTH.read_text())
        return tuple(gt["window"])
    return ("2024-05-08", "2024-05-23")


@dataclass
class Result:
    investigation: Investigation
    telemetry: dict
    memo: str
    verification: dict
    telemetry_events: list = None      # per-step ledger for the LLM/non-LLM breakdown


def investigate(question: str, persona: str = "revenue_analyst",
                window: tuple[str, str] | None = None,
                cfg: RunConfig | None = None) -> Result:
    cfg = cfg or RunConfig()
    tele = Telemetry()
    client = make_client(cfg.llm)
    personas = load_personas()
    p = personas.get(persona, personas["revenue_analyst"])
    contract = load_semantic_contract()
    window = window or _default_window()
    fid, did, hid = _Ids("F"), _Ids("D"), _Ids("H")

    intent = reasoning.parse_intent(question)
    trigger_kpi = intent["kpi"]
    ent = resolve(p, trigger_kpi)

    # --- entitlement pivot: if the persona can't see the asked KPI, analyse a KPI they can
    analysis_kpi = trigger_kpi
    if not ent.can_view_trigger:
        analysis_kpi = next((d for d in ent.visible_drivers if d in contract.kpis),
                            "on_time_delivery_rate")
    inv = Investigation(trigger=question, persona=persona, kpi=analysis_kpi,
                        period=list(window), redactions=ent.redactions)

    # --- GATE (before any hypothesis/LLM work) ---
    with tele.track("detect_change(gate)", Producer.STATISTICAL):
        sig = detect_change(analysis_kpi, window, region=ent.region)
    if sig.low_history:
        inv.facts.append(Fact(id=fid.next(),
            statement=f"{contract.kpi(analysis_kpi).label}: too few days of history in/before this "
                      f"window to separate signal from noise (newly launched / sparse).",
            provenance=Provenance(producer=Producer.STATISTICAL, tool="detect_change")))
        inv.verdict = Verdict(level=ConfidenceLevel.INSUFFICIENT,
            rationale="Sparse history: not enough baseline to judge whether this is a real move.",
            missing_data=["~6 weeks of history for this KPI/segment before a reliable read",
                          "a seasonally-comparable prior period to benchmark against"])
        return _finish(inv, tele, narrative.build_template_memo(inv, p, ent), client)

    if not sig.material:
        inv.facts.append(Fact(id=fid.next(), value=sig.delta_pct, unit="pct",
            statement=f"{contract.kpi(analysis_kpi).label} moved {sig.delta_pct:+.1%} "
                      f"(z={sig.zscore}) — within normal variation.",
            provenance=Provenance(producer=Producer.STATISTICAL, tool="detect_change")))
        inv.verdict = Verdict(level=ConfidenceLevel.INSUFFICIENT,
            rationale="Move is within normal variation; no investigation warranted (signal gate).",
            missing_data=[])
        memo = narrative.build_template_memo(inv, p, ent)
        return _finish(inv, tele, memo, client)

    # --- causal MEMORY prior: does a known mechanism reach this KPI? (learns over time) ---
    inv._run_id = tele.run_id
    causal, episodic = CausalMemory(), EpisodicStore()
    known, w = causal.path_known("on_time_delivery_rate", analysis_kpi if analysis_kpi != "on_time_delivery_rate" else "avg_review_score")
    if known:
        with tele.track("causal_memory.prior", Producer.RULE):
            seen = len(episodic.similar(analysis_kpi))
        inv.facts.append(Fact(id=fid.next(),
            statement=(f"Causal memory recalls a known mechanism reaching {analysis_kpi} "
                       f"(confidence {w}); {seen} similar case(s) resolved before. Used as a prior."),
            provenance=Provenance(producer=Producer.RULE, tool="causal_memory",
                                  args={"path": f"on_time_delivery_rate->...->{analysis_kpi}"})))

    # --- FACTPACK -> PROPOSE -> SKEPTIC -> JUDGE ---
    reasoning.build_factpack(inv, sig, ent, tele, fid, did)
    reasoning.propose(inv, tele, hid)
    reasoning.attack(inv, tele)
    reasoning.judge(inv, cfg, tele)
    narrative.recommend_actions(inv, p)

    # --- record outcome: strengthen the mechanism edge on a confirmed HIGH verdict ---
    mem_note = record_outcome(inv, causal, episodic)
    if mem_note.get("known_mechanism"):
        inv.notes.append(f"causal memory: mechanism confidence now {mem_note['mechanism_confidence']}, "
                         f"seen {mem_note['times_seen']}x")

    # --- WRITE (LLM optional) -> VERIFY ---
    memo = narrative.write_memo(inv, p, ent, client, tele)
    return _finish(inv, tele, memo, client)


def _finish(inv, tele, memo, client) -> Result:
    from dataclasses import asdict
    ver = narrative.verify_citations(inv, memo)
    inv.memo = memo
    tele.persist()
    return Result(investigation=inv, telemetry=tele.summary(), memo=memo, verification=ver,
                  telemetry_events=[asdict(e) for e in tele.events])
