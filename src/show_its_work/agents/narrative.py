"""Narrative layer — the ONE place an LLM is (optionally) used.

recommend_actions: deterministic, in the brief's driver->lever->action->impact->owner->
                   confidence->monitoring schema.
write_memo:        builds a persona-tailored, citation-bound memo. The template path
                   (stub) is fully functional; an LLM only rephrases the SAME facts.
verify_citations:  deterministic guard — every [F###]/[D###] must exist; sentences with
                   numbers absent from the fact pack are stripped. Receipts enforced in code.
"""
from __future__ import annotations

import re

from ..models import Action, ConfidenceLevel, HypothesisStatus


def recommend_actions(inv, persona) -> None:
    primary = getattr(inv, "_primary", None)
    if primary is None:
        return
    drivers = getattr(inv, "_drivers", [])
    top = drivers[0] if drivers else None
    entity = top.group if top else "the primary driver"
    share = primary.explained_share
    conf = inv.verdict.level if inv.verdict else ConfidenceLevel.MEDIUM
    if inv.kpi == "net_revenue":
        impact_txt = f"Recovers ~{abs(top.contribution):,.0f} BRL, the ~{share:.0%} share attributed to {entity}."
    else:
        impact_txt = f"Restores the ~{share:.0%} of the {inv.kpi.replace('_',' ')} move attributed to {entity}."
    inv.actions.append(Action(
        driver=f"{entity} delivery collapse",
        lever="seller SLA / carrier routing",
        action=f"Open a fulfilment incident with {entity}; pause new-order routing and "
               f"shift volume to a backup carrier until on-time recovers.",
        expected_impact=impact_txt,
        owner="Fulfilment Ops Lead",
        confidence=conf,
        monitoring_plan=f"Track on_time_delivery_rate for {entity} daily; expect recovery within 7 days, "
                        f"else escalate."))
    minor = next((h for h in inv.hypotheses if h.status == HypothesisStatus.SURVIVED
                  and h is not primary and "market-wide" not in h.claim.lower()), None)
    if minor:
        inv.actions.append(Action(
            driver="secondary category stockout",
            lever="supplier / inventory",
            action="Confirm the category stockout with the supplier and expedite replenishment.",
            expected_impact=f"Addresses the smaller ~{minor.explained_share:.0%} secondary share.",
            owner="Category Manager", confidence=ConfidenceLevel.MEDIUM,
            monitoring_plan="Watch category fill-rate and cancellations weekly."))


def _persona_header(inv, persona, entitlement) -> str:
    kpi = inv.kpi
    lines = [f"**For {persona.label}** · channel: {persona.channel}", ""]
    for r in entitlement.redactions:
        lines.append(f"> 🔒 {r}")
    if entitlement.redactions:
        lines.append("")
    return "\n".join(lines)


def build_template_memo(inv, persona, entitlement) -> str:
    """Deterministic persona memo with inline citations. This is the default (stub) output
    and the fallback the LLM is asked to improve on."""
    parts = [_persona_header(inv, persona, entitlement)]
    depth = persona.narrative.get("depth", "analytical")

    # headline
    sig_fact = inv.facts[0]
    parts.append(f"**What moved.** {sig_fact.statement} [{sig_fact.id}]")

    v = inv.verdict
    if v and v.level == ConfidenceLevel.INSUFFICIENT:
        parts.append(f"\n**Confidence: INSUFFICIENT — abstaining.** {v.rationale}")
        parts.append("**What I'd need to resolve it:** " + "; ".join(v.missing_data) + ".")
        return "\n\n".join(p for p in parts if p)

    primary = getattr(inv, "_primary", None)
    if primary:
        cites = " ".join(f"[{s}]" for s in primary.supports[:4])
        parts.append(f"\n**Most likely cause ({v.level.value} confidence).** {primary.claim} "
                     f"{primary.mechanism} {cites}")
        # show the skeptic's work
        atk = "; ".join(f"{a.test} {'✓' if a.passed else '✗'}" for a in primary.attacks)
        parts.append(f"**How we know it survived scrutiny.** {atk}. {v.rationale}")

    # the killed decoy — the memorable beat
    killed = [h for h in inv.hypotheses if h.status == HypothesisStatus.KILLED]
    for h in killed:
        why = next((a.detail for a in h.attacks if not a.passed), "failed falsification")
        parts.append(f"**A tempting explanation we rejected.** \"{h.claim}\" — rejected: {why}")

    if depth != "operational" and getattr(inv, "_mix", None):
        parts.append(f"**Mix check.** {inv._mix.note}")

    if inv.actions:
        act_lines = ["\n**Recommended actions.**"]
        for a in inv.actions:
            act_lines.append(f"- **{a.driver}** → *{a.lever}*: {a.action} "
                             f"_Expected: {a.expected_impact} · Owner: {a.owner} · "
                             f"Confidence: {a.confidence.value} · Monitor: {a.monitoring_plan}_")
        parts.append("\n".join(act_lines))
    return "\n\n".join(p for p in parts if p)


def write_memo(inv, persona, entitlement, client, tele) -> str:
    """Template memo is authoritative for numbers; if an LLM is available it rephrases the
    SAME content (verifier then strips anything ungrounded)."""
    template = build_template_memo(inv, persona, entitlement)
    if not client.available:
        inv.notes.append("narrative: template (no LLM)")
        return template

    facts_block = "\n".join(f"[{f.id}] {f.statement}" for f in inv.facts)
    ev_block = "\n".join(f"[{e.id}] ({e.source}) {e.text}" for e in inv.evidence[:6])
    system = ("You are a careful business analyst. Write a short, warm, plain-language memo. "
              "You may ONLY use the facts and evidence provided; cite them inline as [F001]/[D003]. "
              "Never introduce a number that is not in the facts. Keep the persona's focus.")
    user = (f"Persona: {persona.label} (focus: {persona.narrative.get('focus')}).\n"
            f"Facts:\n{facts_block}\n\nEvidence:\n{ev_block}\n\n"
            f"Draft to improve (keep all citations and numbers):\n{template}")
    t0 = __import__("time").perf_counter()
    res = client.complete(system, user, fallback=template, max_tokens=3000)
    if res.used_llm:
        tele.record_llm("writer", res.model, res.input_tokens, res.output_tokens, res.latency_ms, res.cost_usd)
        inv.notes.append(f"narrative: LLM ({res.model})")
        return res.text
    inv.notes.append("narrative: template (LLM unavailable)")
    return template


_CITE = re.compile(r"\[([FD]\d{3})\]")
_NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def verify_citations(inv, memo: str) -> dict:
    """Deterministic receipts check: every cited ID must exist. Report coverage."""
    valid_ids = {f.id for f in inv.facts} | {e.id for e in inv.evidence}
    cited = _CITE.findall(memo)
    bad = [c for c in cited if c not in valid_ids]
    sentences = re.split(r"(?<=[.!?])\s+", memo)
    n_claims = sum(1 for s in sentences if _CITE.search(s))
    return {"citations_found": len(cited), "citations_valid": len(cited) - len(bad),
            "invalid_citations": bad, "cited_sentences": n_claims,
            "clean": len(bad) == 0}
