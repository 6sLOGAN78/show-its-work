# SHOW ITS WORK

**AIC 2026 · PS3 BUSINESSINTELLIGENCE.AI**  
**TEAM MANDALORIANS · IIT PATNA**

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/Pandas-2.2+-orange.svg" alt="Pandas">
  <img src="https://img.shields.io/badge/LLM-Agnostic-purple.svg" alt="LLM Agnostic">
</div>

---

## The Case of the Vanishing Revenue
*A root-cause investigation that shows its work — every number traced to the tool that computed it.*

The CFO doesn’t want a chart. They want to know *why* revenue just vanished (R$103,394 gone in a single fortnight), and they want it before standup. 

The old way requires days of spreadsheets and Slack archaeology. The first AI copilots promised answers in seconds, but they didn't lie about the prose—**they lied about the numbers.**

**Show Its Work** is a deterministic intelligence-to-action engine that completely automates this diagnostic workflow. We strictly adhere to the Round 2 specifications. 

### One Rule Changes Everything: The LLM NEVER Computes a Number
A deterministic core computes every figure. A proposer / skeptic / judge loop argues it out. Every sentence clicks through to the tool call and the source behind it. When the evidence isn’t there, it honestly says so.

---

## 1. The Architecture & Data Flow
Our architecture is split into a **Deterministic Core** (Pandas/Scipy computation) and a **Reasoning Layer** (Multi-Agent framework).

### The 8-Step Pipeline (How It Works)

1. **INTENT:** The user submits a question. The engine maps it to a governed metric (e.g., `net_revenue`) defined in `semantic_contract.json`.
2. **GATE (Is It Real?):** Most alerts are noise. Before any LLM call, our `detect_change()` gate checks if the move is statistically material. It deseasonalizes daily structure by subtracting day-of-week means, calculates a **Median Absolute Deviation (MAD)** of the baseline, and runs a robust z-test. If `z < 3.0` or history is sparse, the engine aborts.
3. **FACTPACK:** Gathers governed semantic metrics, computing the exact additive contribution (`delta = wval - bval`).
4. **PROPOSE (The Suspects):** The Proposer mathematically decomposes the loss across dimensions (seller, category).
5. **SKEPTIC (The Interrogation):** Every hypothesis must declare a falsifiable signature; the Skeptic attacks the strongest candidates.
6. **JUDGE (The Honest Detective):** Scores the surviving evidence based on a strict `sum(crit)` rubric. Sometimes the right answer is *"I don't know yet"*. If the drop is diffuse (no seller concentrated) or contradictory, it outputs **INSUFFICIENT**.
7. **ACTIONS:** Recommend deterministic business levers based on the surviving culprit (e.g., driver -> lever -> action -> impact -> owner).
8. **VERIFY:** The Narrative LLM receives the fact-pack and drafts the memo. Crucially, a `verify_citations()` guard regex-scans the text for invalid `[F###]` citations. If the LLM invents a number, the citations are audited and flagged (`clean=False`), enforcing strict provenance.

---

## 2. The Skeptic's Arsenal & Simpson's Paradox
The most critical part of our engine is that it actively falsifies correlations. A massive risk in BI is attributing drops to a driver when it is actually just a mix shift (e.g., a high-AOV category taking more volume). Our deterministic engine explicitly splits aggregate change into a within-group effect vs. a mix effect (`check_mix_shift`). If the mix effect heavily overrides the actual drop (`abs(mix) / denom > 0.4`), the `simpson_risk` flag fires and halts blind attribution.

The Skeptic then runs four explicit tests:
- *Temporal Alignment (`test_temporal_alignment`):* Locates onset days (`mean - 1.5*std`) to verify the cause strictly preceded the effect.
- *Control Group (`compare_control_group`):* Checks if the damage is concentrated. If a seller collapsed, did the rest of the market also collapse? If so, the claim is falsified.
- *Counterfactual (`counterfactual_estimate`):* Computes `1 - (remaining_delta / total_delta)`. If excluding the culprit removes >15% of the damage, the claim strengthens.
- *Signature:* Checks if predicted secondary ripples actually manifest.

---

## 3. Every Claim Is A Receipt
Each sentence in the final memo clicks through to its tool call and source document. Swap the model for a stub with no LLM — the numbers come back identical.

**THE LLM COMPUTED 0 NUMBERS.**
- **42%** Deterministic
- **26%** Statistical
- **20%** Retrieval
- **12%** Rule-based
- **0%** LLM Share of Compute

Our `LLMClient` features a robust Automatic Model Fallback mechanism. It securely pings Gemini via HTTP, automatically cascading through `gemini-flash-lite`, `3.6-flash`, etc., upon hitting rate limits. If all models fail, it returns the deterministic string template, ensuring the engine never crashes.

---

## 4. Run It Locally

We have built a secure proxy into our live deployment so you can test this locally without needing to provision your own Gemini API keys.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/6sLOGAN78/show-its-work.git
   cd show-its-work
   ```
2. **Install dependencies:**
   ```bash
   pip install -e .
   ```
3. **Point the engine to the AI Proxy:**
   ```bash
   export SIW_API_BASE="https://show-its-work.vercel.app/api/proxy"
   export SIW_API_KEY="dummy-key"
   ```
4. **Start the server:**
   ```bash
   ./run_local.sh
   ```
   *Navigate to `http://127.0.0.1:8533` to view the UI.*

---

## 5. Key features (mapped to the brief's Minimum Prototype Expectations)

| Brief expectation | Where |
|---|---|
| 3–5 connected KPIs, 2–3 sources, different grains/cadences | `contracts/kpi_semantic_contract.yaml` |
| Semantic contract (defn, calc, drivers, thresholds, lineage, access) | same |
| ≥2 personas, different narratives/actions | Revenue Analyst · Ops Lead · Regional Manager |
| One multi-factor movement w/ known drivers | injection harness + `ground_truth.json` |
| One low-confidence → clarify/abstain | ambiguous (diffuse) + noise scenarios |
| One sparse-history / new KPI | sparse-window scenario (`low_history` path) |
| One role-based security / entitlement | Ops Lead redaction + row-scoped Regional Manager |
| Evidence: freshness, method, contribution, confidence, lineage | Receipts section / provenance |
| LLM vs non-LLM breakdown | Telemetry section / `telemetry.py` |
| Runtime telemetry (latency, calls, tokens, cost) | Telemetry section / `telemetry.py` |

---

## Repo Map
```
contracts/   governed semantic contract + personas/entitlements
src/show_its_work/
  data/      synthetic generator · Olist mapper · injection harness · evidence trail · build
  metrics/   deterministic KPI computation
  tools/     detect_change · decompose_drivers · check_mix_shift · falsification · retrieval
  agents/    reasoning.py (deterministic) · narrative.py (the only LLM touchpoint)
  llm/       swappable client (stub/ollama/api)
  memory.py  causal graph + episodic store + feedback
  telemetry.py  latency/tokens/cost + LLM-vs-non-LLM ledger
  engine.py  orchestrates one investigation · run.py CLI · eval.py scorecard
web/         FastAPI backend (api.py) + cyber-brutalist frontend (static/)
docs/        Mandalorians_BusinessIntelligence.ai.pdf
```
