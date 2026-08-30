"""The typed blackboard — how every stage of the engine communicates.

Agents never pass free-form chat to each other; they read and write this Pydantic
state. That keeps numbers exact, context small, and every claim traceable back to
the tool that produced it. This module is the backbone of "show its work".
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Producer(str, Enum):
    """WHO produced a value — the heart of the LLM-vs-non-LLM breakdown (brief #9)."""
    DETERMINISTIC = "deterministic"   # pandas/statsmodels tool: a number
    STATISTICAL = "statistical"       # a stat test
    RETRIEVAL = "retrieval"           # embedding / BM25 search over evidence
    RULE = "rule"                     # business rule from the semantic contract
    LLM = "llm"                       # a language model: phrasing / orchestration ONLY


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    INSUFFICIENT = "INSUFFICIENT"     # -> abstain / request clarification (brief #5)


class HypothesisStatus(str, Enum):
    PROPOSED = "proposed"
    SURVIVED = "survived"             # withstood the skeptic
    KILLED = "killed"                 # a falsification test rejected it (e.g. a decoy)


class Provenance(BaseModel):
    """Where a value came from. Every Fact carries one; this is the receipt."""
    producer: Producer
    tool: Optional[str] = None                 # e.g. "decompose_drivers"
    args: dict = Field(default_factory=dict)   # exact call args -> reproducible
    source_ids: list[str] = Field(default_factory=list)  # evidence ids backing it


class Fact(BaseModel):
    """A quantitative or structured claim produced by a tool. Never by the LLM."""
    id: str                                     # "F007"
    statement: str                              # human-readable
    value: Optional[float] = None
    unit: Optional[str] = None
    provenance: Provenance


class Evidence(BaseModel):
    """A retrieved unstructured item (ticket, CRM note, release log, news, review)."""
    id: str                                     # "D023"
    source: str                                 # ticket|crm|release|news|review
    text: str
    timestamp: Optional[datetime] = None
    entity_ids: list[str] = Field(default_factory=list)
    score: float = 0.0                          # retrieval relevance


class Attack(BaseModel):
    """A skeptic's falsification test against a hypothesis."""
    test: str                                   # "temporal_alignment" | "control_group" | ...
    passed: bool                                # True = hypothesis SURVIVED this attack
    detail: str
    provenance: Provenance


class Hypothesis(BaseModel):
    """A candidate explanation. Grounded in facts; must state falsifiable consequences."""
    id: str                                     # "H2"
    claim: str
    mechanism: str
    supports: list[str] = Field(default_factory=list)      # Fact/Evidence ids
    predicted_signature: list[str] = Field(default_factory=list)  # what ELSE must be true
    explained_share: float = 0.0                # fraction of the delta this accounts for
    status: HypothesisStatus = HypothesisStatus.PROPOSED
    attacks: list[Attack] = Field(default_factory=list)
    origin: Producer = Producer.LLM             # proposer source (LLM or rule/prior)


class Action(BaseModel):
    """Recommended next step in the brief's exact schema (brief solutioning area)."""
    driver: str
    lever: str                                  # the controllable lever
    action: str
    expected_impact: str
    owner: str
    confidence: ConfidenceLevel
    monitoring_plan: str


class Verdict(BaseModel):
    """The judge's calibrated ruling."""
    level: ConfidenceLevel
    rationale: str
    missing_data: list[str] = Field(default_factory=list)   # what would resolve ambiguity


class Investigation(BaseModel):
    """The working-memory blackboard for ONE run. Discarded after; the durable
    learning goes to episodic + causal memory."""
    trigger: str                                # the question / detected movement
    persona: str = "revenue_analyst"
    kpi: str = ""
    period: list[str] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    verdict: Optional[Verdict] = None
    actions: list[Action] = Field(default_factory=list)
    memo: str = ""                              # the final persona narrative
    redactions: list[str] = Field(default_factory=list)     # entitlement withholds (brief #7)
    notes: list[str] = Field(default_factory=list)          # trace breadcrumbs

    # --- convenience lookups ---
    def fact(self, fid: str) -> Optional[Fact]:
        return next((f for f in self.facts if f.id == fid), None)

    def ev(self, eid: str) -> Optional[Evidence]:
        return next((e for e in self.evidence if e.id == eid), None)

    def surviving(self) -> list[Hypothesis]:
        return [h for h in self.hypotheses if h.status == HypothesisStatus.SURVIVED]
