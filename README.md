# Show Its Work — a KPI intelligence-to-action engine

> **Accenture Innovation Challenge 2026 · PS3 BusinessIntelligence.ai · Round 2**
> Team **Mandalorians** — IIT Patna (Ayush Maurya · Aakash Rajput)

A KPI engine that explains *why* a business metric moved, in plain language, where **every
number traces to a tool call**, an internal **skeptic** rejects plausible-but-wrong stories
before you see them, and it **abstains** — honestly — when the evidence isn't there.

**Core principle (the brief's headline rule):** *the LLM is never the source of quantitative
truth.* It parses the question and phrases the memo; **deterministic tools compute every
figure**, and a verifier strips any sentence whose numbers aren't in the fact pack. Swap the
LLM for a stub and the numbers don't change — that's the proof, not a promise.

```bash
pip install -e .
python -m show_its_work.data.build          # build dataset + answer key (no download needed)
python -m show_its_work.run demo            # run the full scenario suite in the terminal
python -m show_its_work.run eval            # the evaluation scorecard
python -m show_its_work.run serve           # the web UI at http://localhost:8533
```

---

## 🚀 Using the Gemini Proxy (feature/gemini-proxy branch)

This specific branch includes a completely secure public proxy architecture. It allows anyone to clone this repository and immediately use the Gemini AI features **without** needing their own API key. 

### For End-Users (Running the App)
1. **Pull this branch:** `git clone -b feature/gemini-proxy <your-repo-url>`
2. **Run it:** `python -m show_its_work.run serve`
3. If the maintainer has deployed the proxy and pointed `SIW_API_BASE` at it, Gemini writes the memo automatically — no keys or `.env` needed. If not, the app **still runs** and falls back to the deterministic template memo (nothing breaks; you'll see one line noting the LLM was unreachable).

> Fully key-free out of the box requires the maintainer to deploy the proxy once (below) and set the default `SIW_API_BASE` to their Vercel URL. To run against a local proxy instead, see [`gemini-proxy/README.md`](gemini-proxy/README.md).

### For Developers (Hosting your own Proxy)
If you fork this repository and want to host your own secure proxy so your users don't need API keys:
1. Navigate to the `gemini-proxy/` folder.
2. Run `npx vercel` to deploy the Node.js Express app to Vercel (or deploy it anywhere that supports Node.js).
3. In your Vercel Dashboard, add your `GEMINI_API_KEY` to the Environment Variables.
4. Update `SIW_API_BASE` in `src/show_its_work/config.py` to point to your new `https://your-url.vercel.app/v1`.
*(Note: Be sure to disable "Vercel Authentication" for preview branches in your Vercel Project settings, otherwise the CLI will get a 401 error!)*

---

## 1. Solution approach

Dashboards show *what* changed; the days-long slog is finding *why*. This engine closes
movement → root cause → action, and is built around the three hard problems the brief plants:

| Hard problem | How we answer it |
|---|---|
| **Signal vs. noise** | A statistical **gate** runs *before any LLM call* — deseasonalised, robust (MAD) mean-shift test + governed materiality thresholds. Noise never reaches the LLM. |
| **Correlation → cause** | A proposer/**skeptic**/judge loop runs **falsification tools** (temporal, control-group, counterfactual, signature), not guesswork. The skeptic's job is to *kill* hypotheses. |
| **Genuine ambiguity** | The judge scores against an explicit rubric and **abstains** (INSUFFICIENT) with calibrated confidence + "what I'd need", instead of guessing. |

## 2. Architecture

```
question ─▶ intent ─▶ GATE ─▶ [entitlement pivot] ─▶ factpack ─▶ propose ─▶ SKEPTIC ─▶ judge
                       │                                                                  │
              not material / sparse                                             actions ─▶ WRITE ─▶ verify
                       ▼                                                                  │
                  abstain (honest)                                          receipts-checked memo ◀┘
```

Two layers, cleanly separated (this *is* the LLM-vs-non-LLM boundary):

- **Deterministic core** (`tools/`, `metrics/`) — pandas/statsmodels/scipy. Computes every KPI
  and every falsification test. Reproducible, cached, temperature-free.
- **Reasoning layer** (`agents/`) — `reasoning.py` (intent, factpack, propose, skeptic, judge) is
  **fully deterministic**; `narrative.py` is the **only** place an LLM is used, and only to phrase
  a memo it cannot add numbers to.

**Typed blackboard** (`models.py`): agents communicate through Pydantic objects (`Fact`,
`Evidence`, `Hypothesis`, `Attack`, `Verdict`, `Action`) — never free-form chat — so numbers stay
exact and every claim carries **provenance** (which tool, which args, which producer).

**Four memory tiers** (`semantics.py`, `memory.py`): governed **semantic** contract (loaded every
run), the **working** blackboard, an **episodic** store of past runs, and a **causal graph** that
strengthens confirmed cause→effect links — so a second similar anomaly resolves faster and more
confidently. That's the learning loop (objective #7).

## 3. Implementation

- **Data** (`data/`): backbone is [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
  (real structured↔unstructured join via `order_id`). If it isn't downloaded, a **synthetic
  generator** produces an Olist-shaped stream so the repo runs with zero external dependencies.
  An **injection harness** plants a controlled anomaly (a seller's delivery collapse), a minor
  driver (a category stockout), an **innocent decoy** (a competitor-sale narrative with no
  structured footprint), and a **diffuse ambiguous** event — recording every planted cause as the
  **answer key** (`ground_truth.json`).
- **4 connected KPIs across 3 sources, different cadences** — net revenue (hourly), on-time
  delivery (hourly), avg review score (event-lagging), repeat-purchase rate (weekly). Chain:
  delivery → reviews → repeat → revenue, with realistic lags.
- **Swappable LLM** (`llm/`): `stub` (default, no LLM — the whole thing still runs) · `ollama`
  (local, e.g. `ollama pull llama3.2`) · `api` (any OpenAI-compatible endpoint). 
  *Note:* By default, the `api` provider now automatically routes to a secure public proxy deployed via `gemini-proxy/` to allow seamless use of Gemini without requiring your own API key. You can still override this by setting `SIW_API_BASE` and `SIW_API_KEY` to your own endpoint. Cost/latency/tokens are metered per call.
- **Stack:** Python 3.11 · pandas/numpy/statsmodels/scipy · scikit-learn (retrieval) · NetworkX
  (causal memory) · Pydantic · FastAPI + a hand-built HTML/CSS/JS frontend (SVG charts, canvas) · optional local Ollama or Gemini proxy for the LLM layer.

## 4. Key features (mapped to the brief's Minimum Prototype Expectations)

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

**Headline metrics** (`python -m show_its_work.run eval`): root-cause top-1 · **decoy-rejection**
· abstention correctness · false-alert rate · citation precision.

## Honesty note
Anomalies are **injected for evaluation** with a recorded answer key. We never imply synthetic
results are real-world validation — the constructed ground truth is what lets us grade objectively.

## Repo map
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
docs/        proposal.md
```
