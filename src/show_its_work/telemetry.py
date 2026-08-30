"""Runtime telemetry — latency, model calls, tokens, cost, and the LLM/non-LLM split.

Every tool call and every model call flows through here, tagged by producer. This is
what makes the brief's mandatory telemetry (#10) and LLM-vs-non-LLM breakdown (#9) real
rather than claimed. A run's ledger is both summarised for the UI and written to
telemetry/runs/<id>.jsonl for audit.
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field

from .config import TELEMETRY_DIR
from .models import Producer


@dataclass
class Event:
    step: str
    kind: str                     # Producer value: deterministic|statistical|retrieval|rule|llm
    latency_ms: float
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@dataclass
class Telemetry:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    events: list[Event] = field(default_factory=list)

    # ---- recording ----
    @contextmanager
    def track(self, step: str, kind: Producer | str):
        """Time a deterministic/statistical/retrieval/rule block."""
        k = kind.value if isinstance(kind, Producer) else kind
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.events.append(Event(step=step, kind=k,
                                     latency_ms=round((time.perf_counter() - t0) * 1000, 2)))

    def record_llm(self, step: str, model: str, in_tok: int, out_tok: int,
                   latency_ms: float, cost_usd: float = 0.0):
        # cost is computed by the client from configurable per-token prices
        self.events.append(Event(step=step, kind=Producer.LLM.value, latency_ms=round(latency_ms, 2),
                                 model=model, input_tokens=in_tok, output_tokens=out_tok,
                                 cost_usd=round(cost_usd, 6)))

    # ---- reporting ----
    def summary(self) -> dict:
        llm = [e for e in self.events if e.kind == "llm"]
        non = [e for e in self.events if e.kind != "llm"]
        return {
            "run_id": self.run_id,
            "total_latency_ms": round(sum(e.latency_ms for e in self.events), 2),
            "llm_calls": len(llm),
            "llm_latency_ms": round(sum(e.latency_ms for e in llm), 2),
            "non_llm_calls": len(non),
            "non_llm_latency_ms": round(sum(e.latency_ms for e in non), 2),
            "input_tokens": sum(e.input_tokens for e in llm),
            "output_tokens": sum(e.output_tokens for e in llm),
            "estimated_cost_usd": round(sum(e.cost_usd for e in llm), 6),
            "work_by_producer": self._by_producer(),
        }

    def _by_producer(self) -> dict:
        out: dict[str, int] = {}
        for e in self.events:
            out[e.kind] = out.get(e.kind, 0) + 1
        return out

    def persist(self) -> str:
        TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
        fp = TELEMETRY_DIR / f"{self.run_id}.jsonl"
        with fp.open("w") as f:
            for e in self.events:
                f.write(json.dumps(asdict(e)) + "\n")
            f.write(json.dumps({"summary": self.summary()}) + "\n")
        return str(fp)
