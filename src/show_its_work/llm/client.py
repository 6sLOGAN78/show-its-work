"""Swappable LLM client. provider = stub | ollama | api.

Design intent: the LLM is a *language* layer only — phrase the memo. It never computes a
number (the tools do) and the verifier strips any sentence whose figures aren't in the fact
pack. Because of that, `stub` (no LLM at all) runs the entire pipeline; ollama/api just make
the prose nicer. Swapping providers and getting the same numbers is the live proof that the
model is not the source of quantitative truth.

`api` targets any OpenAI-compatible /chat/completions endpoint (OpenAI, a local vLLM/LM Studio
server, a gateway, ...) via plain HTTP — no vendor SDK.
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass

from ..config import LLMConfig


@dataclass
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    used_llm: bool                      # False for the stub
    cost_usd: float = 0.0


def _approx_tokens(s: str) -> int:
    return max(1, len(s) // 4)


class LLMClient:
    """Base: a stub that returns the caller's deterministic fallback at zero cost."""
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.provider = cfg.provider

    @property
    def available(self) -> bool:
        return False

    def complete(self, system: str, user: str, fallback: str = "",
                 max_tokens: int = 800) -> LLMResult:
        return LLMResult(text=fallback, model="stub", input_tokens=0,
                         output_tokens=0, latency_ms=0.0, used_llm=False)


class OllamaClient(LLMClient):
    @property
    def available(self) -> bool:
        try:
            urllib.request.urlopen(f"{self.cfg.ollama_host}/api/tags", timeout=1.5)
            return True
        except Exception:
            return False

    def complete(self, system, user, fallback="", max_tokens=800) -> LLMResult:
        body = json.dumps({
            "model": self.cfg.ollama_model, "stream": False,
            "options": {"temperature": self.cfg.temperature, "num_predict": max_tokens},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }).encode()
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(f"{self.cfg.ollama_host}/api/chat", data=body,
                                         headers={"Content-Type": "application/json"})
            resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
            text = resp["message"]["content"]
        except Exception:
            return LLMResult(fallback, "stub(ollama-unreachable)", 0, 0, 0.0, False)
        dt = (time.perf_counter() - t0) * 1000
        return LLMResult(text, self.cfg.ollama_model, _approx_tokens(system + user),
                         _approx_tokens(text), dt, True, 0.0)


class ApiClient(LLMClient):
    """Any OpenAI-compatible /chat/completions endpoint via plain HTTP."""
    @property
    def available(self) -> bool:
        return bool(self.cfg.api_key)

    def complete(self, system, user, fallback="", max_tokens=800) -> LLMResult:
        body = json.dumps({
            "model": self.cfg.api_model, "temperature": self.cfg.temperature,
            "max_tokens": max_tokens,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }).encode()
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(
                f"{self.cfg.api_base.rstrip('/')}/chat/completions", data=body,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {self.cfg.api_key}"})
            resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
            text = resp["choices"][0]["message"]["content"]
            usage = resp.get("usage", {})
            it = usage.get("prompt_tokens", _approx_tokens(system + user))
            ot = usage.get("completion_tokens", _approx_tokens(text))
        except Exception:
            return LLMResult(fallback, "stub(api-error)", 0, 0, 0.0, False)
        dt = (time.perf_counter() - t0) * 1000
        cost = it / 1e6 * self.cfg.price_in_per_mtok + ot / 1e6 * self.cfg.price_out_per_mtok
        return LLMResult(text, self.cfg.api_model, it, ot, dt, True, round(cost, 6))


def make_client(cfg: LLMConfig | None = None) -> LLMClient:
    """Pick a client; fall back to stub if the requested provider isn't usable, so the
    pipeline always runs."""
    cfg = cfg or LLMConfig()
    if cfg.provider == "api":
        c = ApiClient(cfg)
        return c if c.available else LLMClient(cfg)
    if cfg.provider == "ollama":
        c = OllamaClient(cfg)
        return c if c.available else LLMClient(cfg)
    return LLMClient(cfg)
