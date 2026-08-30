"""Role-based entitlements — row, column, and domain-level (brief #7).

Enforced at the data/analysis boundary, not just hidden in the UI:
  ROW      persona.region_filter() restricts which rows a KPI is computed over.
  COLUMN   persona.can_see(kpi.access) gates whole KPIs (e.g. finance_restricted).
When a persona asks about a KPI they can't see, the engine does NOT silently drop it
— it records a visible redaction and pivots to what they ARE entitled to.
"""
from __future__ import annotations

from dataclasses import dataclass

from .semantics import Persona, load_semantic_contract


@dataclass
class Entitlement:
    region: list[str] | None          # row-level scope (None = all)
    can_view_trigger: bool            # may the persona see the asked KPI?
    redactions: list[str]             # human-readable withholds
    visible_drivers: list[str]        # driver KPIs the persona may see


def resolve(persona: Persona, trigger_kpi: str) -> Entitlement:
    c = load_semantic_contract()
    spec = c.kpi(trigger_kpi)
    region = persona.region_filter()
    can_view = persona.can_see(spec.access)
    redactions: list[str] = []
    if not can_view:
        redactions.append(
            f"1 metric withheld — {spec.label} is '{spec.access}'; "
            f"{persona.label} lacks that entitlement. Ask a Finance-entitled viewer for the $ attribution.")
    visible = [d for d in spec.drivers
               if d not in c.kpis or persona.can_see(c.kpi(d).access)]
    return Entitlement(region=region, can_view_trigger=can_view,
                       redactions=redactions, visible_drivers=visible)
