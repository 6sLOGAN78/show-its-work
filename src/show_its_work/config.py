"""Central config — paths, thresholds, and the swappable LLM/provider settings.

Nothing here computes analytics; it just tells the rest of the system where things
live and which knobs to turn. Thresholds default to the semantic contract but can be
overridden per run.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # .../accenture
DATA = ROOT / "data"
RAW = DATA / "raw"
SYNTH = DATA / "synthetic"
CONTRACTS = ROOT / "contracts"
TELEMETRY_DIR = ROOT / "telemetry" / "runs"

SEMANTIC_CONTRACT = CONTRACTS / "kpi_semantic_contract.yaml"
PERSONAS = CONTRACTS / "personas.yaml"
GROUND_TRUTH = SYNTH / "ground_truth.json"


@dataclass
class LLMConfig:
    """Swappable LLM. provider: 'stub' | 'ollama' | 'api'.

    'stub' -> no LLM at all; deterministic templated phrasing. Always runs.
    'ollama' -> local model via http://localhost:11434 (falls back to stub if absent).
    'api' -> any OpenAI-compatible /chat/completions endpoint (base_url + key + model),
             set via SIW_API_BASE / SIW_API_KEY / SIW_API_MODEL. No vendor SDK required.
    Cost is derived from configurable per-million-token prices, so runtime telemetry
    reports a real cost-per-insight for whichever model you point it at.
    """
    provider: str = field(default_factory=lambda: os.environ.get("SIW_LLM", "api"))
    ollama_model: str = field(default_factory=lambda: os.environ.get("SIW_OLLAMA_MODEL", "llama3.2"))
    ollama_host: str = field(default_factory=lambda: os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    # default targets a LOCAL gemini-proxy; for a key-free clone experience, set this to
    # your deployed proxy URL (e.g. https://<app>.vercel.app/v1) via env or here.
    api_base: str = field(default_factory=lambda: os.environ.get("SIW_API_BASE", "http://localhost:3000/v1"))
    api_key: str = field(default_factory=lambda: os.environ.get("SIW_API_KEY", "proxy-bypass-key"))
    api_model: str = field(default_factory=lambda: os.environ.get("SIW_API_MODEL", "gemini-3.6-flash"))
    price_in_per_mtok: float = field(default_factory=lambda: float(os.environ.get("SIW_PRICE_IN", "0.075")))
    price_out_per_mtok: float = field(default_factory=lambda: float(os.environ.get("SIW_PRICE_OUT", "0.30")))
    temperature: float = 0.0          # determinism: same question -> same words


@dataclass
class RunConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    max_hypotheses: int = 5           # cost cap
    skeptic_attacks_top_k: int = 3    # skeptic only attacks the strongest few
    high_conf_min_share: float = 0.50 # a hypothesis must explain >=50% of delta for HIGH
    seed: int = 7


def ensure_dirs() -> None:
    try:
        for d in (SYNTH, TELEMETRY_DIR):
            d.mkdir(parents=True, exist_ok=True)
    except (OSError, PermissionError):
        pass
