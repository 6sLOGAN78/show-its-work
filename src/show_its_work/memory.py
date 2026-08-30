"""Memory — the tiers that make the engine LEARN (brief objective #7).

  Semantic   governed business context -> semantics.py (loaded every run).
  Working    the Investigation blackboard -> models.py (one run, discarded).
  Episodic   past investigations, persisted + queryable (this file).
  Causal     confirmed cause->effect edges that persist and STRENGTHEN on confirmation,
             DECAY on contradiction. Seeded from the contract's causal_priors; grows with
             use. Next investigation queries it as a prior instead of starting blank —
             which is why a second similar anomaly resolves faster and more confidently.

Feedback from analysts/business users flows in via record_feedback(), adjusting edge
weights — a concrete learning loop, not hand-waving.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import networkx as nx

from .config import SYNTH
from .semantics import load_semantic_contract

CAUSAL_PATH = SYNTH / "causal_memory.json"
EPISODIC_PATH = SYNTH / "episodic.jsonl"


@dataclass
class Episode:
    run_id: str
    when: str
    kpi: str
    window: list
    verdict: str
    primary_cause: str
    explained_share: float
    feedback: str = ""             # analyst confirmation/correction, if any


class CausalMemory:
    """A persistent cause->effect graph. Edge weight = confidence in the mechanism."""
    def __init__(self, path: Path = CAUSAL_PATH):
        self.path = path
        self.g = nx.DiGraph()
        self._load_or_seed()

    def _load_or_seed(self):
        if self.path.exists():
            data = json.loads(self.path.read_text())
            for e in data["edges"]:
                self.g.add_edge(e["cause"], e["effect"], weight=e["weight"],
                                confirmations=e.get("confirmations", 0))
        else:
            for pr in load_semantic_contract().causal_priors:
                self.g.add_edge(pr["cause"], pr["effect"], weight=pr["strength"], confirmations=0)
            self.save()

    def prior(self, cause: str, effect: str) -> float:
        return self.g[cause][effect]["weight"] if self.g.has_edge(cause, effect) else 0.0

    def strengthen(self, cause: str, effect: str, amount: float = 0.05):
        if self.g.has_edge(cause, effect):
            d = self.g[cause][effect]
            d["weight"] = min(0.99, d["weight"] + amount)
            d["confirmations"] = d.get("confirmations", 0) + 1
        else:
            self.g.add_edge(cause, effect, weight=0.55, confirmations=1)
        self.save()

    def decay(self, cause: str, effect: str, amount: float = 0.10):
        if self.g.has_edge(cause, effect):
            self.g[cause][effect]["weight"] = max(0.0, self.g[cause][effect]["weight"] - amount)
            self.save()

    def path_known(self, cause: str, effect: str) -> tuple[bool, float]:
        """Is there a known mechanism chain cause -> ... -> effect? Return (yes, weakest link)."""
        try:
            p = nx.shortest_path(self.g, cause, effect)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return False, 0.0
        w = min(self.g[p[i]][p[i + 1]]["weight"] for i in range(len(p) - 1)) if len(p) > 1 else 0.0
        return True, round(w, 3)

    def edges(self) -> list[dict]:
        return [{"cause": u, "effect": v, "weight": round(d["weight"], 3),
                 "confirmations": d.get("confirmations", 0)} for u, v, d in self.g.edges(data=True)]

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"edges": self.edges()}, indent=2))
        except (OSError, PermissionError):
            pass


class EpisodicStore:
    def __init__(self, path: Path = EPISODIC_PATH):
        self.path = path

    def append(self, ep: Episode):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(json.dumps(asdict(ep)) + "\n")
        except (OSError, PermissionError):
            pass

    def all(self) -> list[Episode]:
        if not self.path.exists():
            return []
        return [Episode(**json.loads(l)) for l in self.path.read_text().splitlines() if l.strip()]

    def similar(self, kpi: str) -> list[Episode]:
        return [e for e in self.all() if e.kpi == kpi]


def record_outcome(inv, causal: CausalMemory, episodic: EpisodicStore) -> dict:
    """Persist the run and, if HIGH-confidence, strengthen the mechanism edge that fired.
    Returns a small note the writer can surface ('matches a known mechanism, seen N times')."""
    prim = None
    for h in inv.hypotheses:
        if h.status.value == "survived" and "market-wide" not in h.claim.lower():
            prim = h if prim is None or h.explained_share > prim.explained_share else prim
    v = inv.verdict.level.value if inv.verdict else "INSUFFICIENT"
    ep = Episode(run_id=getattr(inv, "_run_id", "?"), when=datetime.utcnow().isoformat(timespec="seconds"),
                 kpi=inv.kpi, window=list(inv.period), verdict=v,
                 primary_cause=prim.claim if prim else "(none)",
                 explained_share=round(prim.explained_share, 3) if prim else 0.0)
    episodic.append(ep)

    note = {}
    if v == "HIGH" and prim:
        # the fired mechanism for our demo chain: on-time delivery -> revenue (via reviews/repeat)
        causal.strengthen("on_time_delivery_rate", inv.kpi if inv.kpi != "on_time_delivery_rate" else "avg_review_score")
        seen = len(episodic.similar(inv.kpi))
        known, w = causal.path_known("on_time_delivery_rate", "net_revenue")
        note = {"known_mechanism": known, "mechanism_confidence": w, "times_seen": seen}
    return note
