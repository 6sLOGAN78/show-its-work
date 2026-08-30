"""Deterministic reasoning agents — intent, factpack, proposer, skeptic, judge.

NONE of these call an LLM. Every number is a tool return value wrapped in a Fact with
provenance; every hypothesis is grounded in facts + evidence; the skeptic's attacks
are falsification-tool verdicts, not opinions; the judge applies an explicit rubric.
This whole module is the "non-LLM" side of the brief's #9 breakdown.
"""
from __future__ import annotations

import re

from .. import tools as T
from ..models import (Attack, ConfidenceLevel, Evidence, Fact, Hypothesis,
                      HypothesisStatus, Producer, Provenance, Verdict)
from ..semantics import load_semantic_contract

_KPI_KEYWORDS = {
    "net_revenue": ["revenue", "sales", "gmv", "top line", "topline"],
    "on_time_delivery_rate": ["delivery", "on-time", "on time", "shipping", "sla", "late"],
    "avg_review_score": ["review", "rating", "csat", "satisfaction", "stars"],
    "repeat_purchase_rate": ["repeat", "retention", "churn", "loyalty", "reorder"],
}


class _Ids:
    def __init__(self, prefix): self.p, self.n = prefix, 0
    def next(self): self.n += 1; return f"{self.p}{self.n:03d}"


def parse_intent(question: str, default_kpi="net_revenue") -> dict:
    """Rule-based NL->structured (orchestration, deterministic). Maps the question to a
    governed KPI + dimension. Window defaults to the engine's detected anomaly window."""
    q = question.lower()
    kpi = next((k for k, kws in _KPI_KEYWORDS.items() if any(w in q for w in kws)), default_kpi)
    dim = "seller_id"
    if "categor" in q or "product" in q:
        dim = "category"
    elif "region" in q or "state" in q:
        dim = "region"
    return {"kpi": kpi, "dimension": dim}


def build_factpack(inv, sig, entitlement, tele, fid: _Ids, did: _Ids) -> None:
    """Deterministic + cached fact pack: the signal, the driver waterfall, the mix
    guard, and retrieved evidence — each a Fact/Evidence with provenance."""
    c = load_semantic_contract()
    kpi, window = inv.kpi, tuple(sig.window)

    inv.facts.append(Fact(
        id=fid.next(), value=sig.delta_pct, unit="pct",
        statement=(f"{c.kpi(kpi).label} moved {sig.delta_pct:+.1%} "
                   f"({sig.window_value:.1f} vs baseline {sig.baseline_value:.1f}); "
                   f"z={sig.zscore}, {'material' if sig.material else 'not material'}."),
        provenance=Provenance(producer=Producer.STATISTICAL, tool="detect_change",
                              args={"kpi": kpi, "window": window})))

    with tele.track("decompose_drivers", Producer.DETERMINISTIC):
        drivers = T.decompose_drivers(kpi, window, "seller_id", region=entitlement.region)
    inv._drivers = drivers                       # stash for proposer
    for d in drivers[:3]:
        inv.facts.append(Fact(
            id=fid.next(), value=d.contribution, unit="BRL",
            statement=(f"{d.group} contributed {d.contribution:,.0f} to the move "
                       f"({d.contribution_share:+.0%} of the total delta)."),
            provenance=Provenance(producer=Producer.DETERMINISTIC, tool="decompose_drivers",
                                  args={"dimension": "seller_id", "group": d.group})))

    with tele.track("check_mix_shift", Producer.DETERMINISTIC):
        mix = T.check_mix_shift("on_time_delivery_rate", window, "category")
    inv._mix = mix
    inv.facts.append(Fact(
        id=fid.next(), statement=f"Mix-shift check: {mix.note}",
        provenance=Provenance(producer=Producer.STATISTICAL, tool="check_mix_shift",
                              args={"dimension": "category"})))

    # retrieve evidence: the top driver's mechanism AND a broad "what else happened"
    # context sweep — so competing narratives (the decoy) get their day in court too.
    top = drivers[0].group if drivers else ""
    seen: set[str] = set()
    with tele.track("search_evidence(driver)", Producer.RETRIEVAL):
        hits = T.search_evidence(f"{top} late delivery fulfilment problem cause", window, None, k=6)
    with tele.track("search_evidence(context)", Producer.RETRIEVAL):
        hits += T.search_evidence("competitor promotion sale market demand external event stockout system glitch outage weather payment failure",
                                  window, None, k=4)
    for h in hits:
        key = h["text"]
        if key in seen:
            continue
        seen.add(key)
        inv.evidence.append(Evidence(id=did.next(), source=h["source"], text=h["text"],
                                     entity_ids=h["entity_ids"], score=h["score"]))


def propose(inv, tele, hid: _Ids) -> None:
    """Rule-based hypothesis generation from the fact pack: the top driver (primary), the
    innocent market-wide decoy, and a category minor driver tied to stockout evidence.
    inv._targets records each hypothesis's (dimension, value) so the skeptic runs the
    right falsification test."""
    drivers = getattr(inv, "_drivers", [])
    if not drivers:
        return
    inv._targets: dict[str, tuple] = {}
    top = drivers[0]
    ev_for_top = [e.id for e in inv.evidence if top.group in e.entity_ids]

    h1 = Hypothesis(
        id=hid.next(), origin=Producer.RULE,
        claim=f"{top.group}'s delivery collapse drove the {inv.kpi} drop.",
        mechanism="Late/failed fulfilment -> cancellations + poor reviews -> lost recognised revenue.",
        supports=[f.id for f in inv.facts if top.group in f.statement] + ev_for_top,
        predicted_signature=["on_time_delivery_rate down for this seller",
                             "avg_review_score down for this seller"],
        explained_share=min(1.0, abs(top.contribution_share)))
    inv.hypotheses.append(h1)
    inv._targets[h1.id] = ("seller_id", top.group)

    # decoy: a market-wide narrative present in evidence but with no structured footprint
    decoy_ev = [e for e in inv.evidence if "market_wide_narrative" in e.entity_ids]
    if decoy_ev:
        h2 = Hypothesis(
            id=hid.next(), origin=Producer.RULE,
            claim="A market-wide competitor flash sale pulled demand away, causing the drop.",
            mechanism="External promotion diverts customers across the whole market.",
            supports=[decoy_ev[0].id],
            predicted_signature=["all sellers down roughly uniformly (market-wide)"],
            explained_share=0.0)
        inv.hypotheses.append(h2)
        inv._targets[h2.id] = ("market", None)

    # minor: a category stockout tied to its CRM evidence (real but smaller)
    cat_ev = [e for e in inv.evidence if any(str(x).startswith("category:") for x in e.entity_ids)]
    if cat_ev:
        cat = [x for x in cat_ev[0].entity_ids if str(x).startswith("category:")][0].split(":", 1)[1]
        h3 = Hypothesis(
            id=hid.next(), origin=Producer.RULE,
            claim=f"A stockout in the {cat} category removed a smaller, separate share of revenue.",
            mechanism="Supplier stockout -> unfulfillable orders cancelled in that category.",
            supports=[cat_ev[0].id],
            predicted_signature=[], explained_share=0.0)
        inv.hypotheses.append(h3)
        inv._targets[h3.id] = ("category", cat)


def attack(inv, tele) -> None:
    """The SKEPTIC. Runs the right falsification test per hypothesis kind; sets survived/killed."""
    window = tuple(inv.period) if inv.period else None
    drivers = getattr(inv, "_drivers", [])
    top_group = drivers[0].group if drivers else None
    targets = getattr(inv, "_targets", {})

    for h in inv.hypotheses:
        dim, val = targets.get(h.id, (None, None))

        if dim == "market":
            # DECOY: killed if the damage is concentrated in one seller (not market-wide)
            with tele.track("compare_control_group", Producer.STATISTICAL):
                ct = T.compare_control_group(top_group, window, kpi=inv.kpi)
            passed = not ct.concentrated       # market-wide survives only if NOT concentrated
            h.attacks.append(Attack(test="heterogeneity/control", passed=passed,
                detail=("Market-wide claim fails — " + ct.detail) if not passed else ct.detail,
                provenance=Provenance(producer=Producer.STATISTICAL, tool="compare_control_group")))
            h.status = HypothesisStatus.SURVIVED if passed else HypothesisStatus.KILLED

        elif dim == "seller_id":
            with tele.track("compare_control_group", Producer.STATISTICAL):
                ct = T.compare_control_group(val, window, kpi=inv.kpi)
            h.attacks.append(Attack(test="control_group", passed=ct.passed, detail=ct.detail,
                provenance=Provenance(producer=Producer.STATISTICAL, tool="compare_control_group")))
            with tele.track("test_temporal_alignment", Producer.STATISTICAL):
                tt = T.test_temporal_alignment("on_time_delivery_rate", inv.kpi, window)
            h.attacks.append(Attack(test="temporal_alignment", passed=tt.passed, detail=tt.detail,
                provenance=Provenance(producer=Producer.STATISTICAL, tool="test_temporal_alignment")))
            with tele.track("counterfactual_estimate", Producer.DETERMINISTIC):
                cf = T.counterfactual_estimate("seller_id", val, window, kpi=inv.kpi)
            h.explained_share = min(1.0, max(h.explained_share, abs(cf.explained_share)))
            h.attacks.append(Attack(test="counterfactual", passed=abs(cf.explained_share) >= 0.15,
                detail=cf.detail,
                provenance=Provenance(producer=Producer.DETERMINISTIC, tool="counterfactual_estimate")))
            sigpass, sigdetail = _check_signature(h, window)
            h.attacks.append(Attack(test="signature", passed=sigpass, detail=sigdetail,
                provenance=Provenance(producer=Producer.STATISTICAL, tool="detect_change")))
            h.status = (HypothesisStatus.SURVIVED if sum(a.passed for a in h.attacks) >= 3
                        else HypothesisStatus.KILLED)

        elif dim == "category":
            with tele.track("counterfactual_estimate", Producer.DETERMINISTIC):
                cf = T.counterfactual_estimate("category", val, window, kpi=inv.kpi)
            share = abs(cf.explained_share)
            h.explained_share = share
            # a real but SMALL contributor: survives, but must not rival the primary
            passed = 0.03 <= share <= 0.5
            h.attacks.append(Attack(test="counterfactual", passed=passed, detail=cf.detail,
                provenance=Provenance(producer=Producer.DETERMINISTIC, tool="counterfactual_estimate")))
            h.status = HypothesisStatus.SURVIVED if passed else HypothesisStatus.KILLED

        else:
            h.status = HypothesisStatus.SURVIVED


def _check_signature(h, window) -> tuple[bool, str]:
    checks = []
    for pred in h.predicted_signature:
        for kpi in ("on_time_delivery_rate", "avg_review_score"):
            if kpi.split("_")[0] in pred or kpi in pred:
                s = T.detect_change(kpi, window)
                want_down = "down" in pred
                ok = (s.direction == "down") == want_down and s.significant
                checks.append((f"{kpi} {s.direction} (z={s.zscore})", ok))
    if not checks:
        return True, "no structured signature to test"
    passed = all(ok for _, ok in checks)
    return passed, "; ".join(f"{d} {'✓' if ok else '✗'}" for d, ok in checks)


def judge(inv, cfg, tele) -> None:
    """Explicit rubric, not judgement calls:
    HIGH = temporal ✓ AND control ✓ AND >=1 corroborating doc AND explains >= high_conf_min_share."""
    survivors = [h for h in inv.hypotheses if h.status == HypothesisStatus.SURVIVED
                 and "market-wide" not in h.claim.lower()]
    survivors.sort(key=lambda h: h.explained_share, reverse=True)

    if not survivors:
        inv.verdict = _insufficient(inv)
        return
    best = survivors[0]
    passed = {a.test: a.passed for a in best.attacks}
    has_doc = any(best.supports and eid.startswith("D") for eid in best.supports)
    crit = [passed.get("temporal_alignment", False), passed.get("control_group", False),
            has_doc, best.explained_share >= cfg.high_conf_min_share]
    n = sum(crit)
    if n == 4:
        level = ConfidenceLevel.HIGH
    elif n >= 2:
        level = ConfidenceLevel.MEDIUM
    else:
        inv.verdict = _insufficient(inv); return
    inv._primary = best
    rationale = (f"Best hypothesis {best.id} explains {best.explained_share:.0%} of the delta; "
                 f"temporal={'✓' if crit[0] else '✗'}, control={'✓' if crit[1] else '✗'}, "
                 f"corroborating_doc={'✓' if crit[2] else '✗'}, share>=50%={'✓' if crit[3] else '✗'}.")
    inv.verdict = Verdict(level=level, rationale=rationale, missing_data=[])


def _insufficient(inv):
    # context-aware rationale: was the move DIFFUSE (no seller concentrated)?
    diffuse = any(h.status == HypothesisStatus.KILLED and
                  any(a.test in ("control_group",) and not a.passed for a in h.attacks)
                  for h in inv.hypotheses)
    contradictory = any("ambiguous" in e.entity_ids for e in inv.evidence)
    bits = []
    if diffuse:
        bits.append("the drop is diffuse — no single seller or category is concentrated enough "
                    "to blame (the control test rejected the leading candidate)")
    if contradictory:
        bits.append("the evidence is contradictory (competing explanations, none corroborated)")
    rationale = ("No hypothesis survived falsification with enough support to attribute a cause"
                 + (": " + "; ".join(bits) if bits else "") + ".")
    return Verdict(level=ConfidenceLevel.INSUFFICIENT, rationale=rationale,
                   missing_data=["a driver that is both concentrated AND temporally aligned",
                                 "at least one corroborating document tied to that driver",
                                 "resolution of the contradictory evidence before attributing a cause"])
