# SHOW ITS WORK
**AIC 2026 · PS3 BUSINESSINTELLIGENCE.AI**  
**TEAM MANDALORIANS · IIT PATNA**

---

# THE CASE OF THE VANISHING REVENUE
### A ROOT-CAUSE INVESTIGATION THAT SHOWS ITS WORK — EVERY NUMBER TRACED TO THE TOOL THAT COMPUTED IT.

The CFO doesn’t want a chart. They want to know *why* revenue just vanished (R$103,394 gone in a single fortnight), and they want it before standup. 

The old way requires days of spreadsheets and Slack archaeology. The first AI copilots promised answers in seconds, but they didn't lie about the prose—**they lied about the numbers.**

Our solution, **Show Its Work**, is a deterministic intelligence-to-action engine that completely automates this diagnostic workflow. We strictly adhere to the Round 2 specifications. 

**One rule changes everything:**
### THE LLM NEVER COMPUTES A NUMBER

A deterministic core computes every figure. A proposer / skeptic / judge loop argues it out. Every sentence clicks through to the tool call and the source behind it. When the evidence isn’t there, it honestly says so.

---

## 1. THE ARCHITECTURE & DATA FLOW
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

## 2. THE CULPRIT: ONE SELLER’S DELIVERIES BROKE THE WHOLE METRIC
The culprit never touched revenue directly. The engine walked the chain link by link — each hop cited to a tool call and a source document.

* **On-Time Delivery ↓ (-26 pt):** `house_bravos` misses SLA 4+ weeks
* **Review Score ↓ (4.4 → 3.1):** buyers punish the late orders
* **Repeat Purchase ↓ (-18%):** they simply don't come back
* **Net Revenue ↓ (-R$103K):** the number the CFO saw

While a human or basic chatbot would blame the "Competitor Flash Sale" (a tidy, market-wide story), our engine evaluates it. The Skeptic explicitly rejects it because it leaves no structured footprint in the data.

### Solving "Simpson's Paradox"
A massive risk in BI is attributing drops to a driver when it is actually just a mix shift (e.g., a high-AOV category taking more volume). Our deterministic engine explicitly splits aggregate change into a within-group effect vs. a mix effect. If the mix effect heavily overrides the actual drop (`abs(mix) / denom > 0.4`), the `simpson_risk` flag fires and halts blind attribution.

---

## 3. THE SKEPTIC'S ARSENAL (Algorithmic Logic)
The Skeptic runs four explicit tests:
- *Temporal Alignment (`test_temporal_alignment`):* Locates onset days (`mean - 1.5*std`) to verify the cause strictly preceded the effect.
- *Control Group (`compare_control_group`):* Checks if the damage is concentrated. If a seller collapsed, did the rest of the market also collapse? If so, the claim is falsified.
- *Counterfactual (`counterfactual_estimate`):* Computes `1 - (remaining_delta / total_delta)`. If excluding the culprit removes >15% of the damage, the claim strengthens.
- *Signature:* Checks if predicted secondary ripples actually manifest.

---

## 4. EVERY CLAIM IS A RECEIPT
Each sentence in the final memo clicks through to its tool call and source document. Swap the model for a stub with no LLM — the numbers come back identical.

**THE LLM COMPUTED 0 NUMBERS.**
- **42%** Deterministic
- **26%** Statistical
- **20%** Retrieval
- **12%** Rule-based
- **0%** LLM Share of Compute

Our `LLMClient` features a robust Automatic Model Fallback mechanism. It securely pings Gemini via HTTP, automatically cascading through `gemini-flash-lite`, `3.6-flash`, etc., upon hitting rate limits. If all models fail, it returns the deterministic string template, ensuring the engine never crashes.

---

## 5. GOVERNED PER ROLE
**One Investigation, A Different Correct Answer Per Role.**
A semantic contract defines every metric — the engine can't invent one. Entitlements are enforced at the compute layer, not the UI. Redactions are explicit and audited.

* **Revenue Analyst:** Sees everything (-R$103,394 Net Revenue).
* **Ops / Fulfilment Lead:** Finance figures redacted. Sees SLA breach and On-Time Delivery drop.
* **Regional Manager (South):** Scoped to one region. Other regions hidden.

---

## 6. FROM DETECTIVE TO ADVISOR
Not a week of digging — minutes. Not a confident guess — a chain of evidence you can defend, line by line.

* **TIME TO ANSWER:** Seconds (not days)
* **WHAT YOU PRESENT:** A cited chain of evidence (not a plausible guess)
* **ALERTS THAT FIRE:** Only real moves (not every wiggle)
* **CONFIDENCE:** Calibrated — abstains when unsure

**Phase 0 (This Prototype):** 4 connected KPIs, skeptic + decoy rejection, abstention, personas, telemetry, causal memory.  
**Phase 1 (Vision):** Connect real sources (Warehouse + ticketing / CRM connectors).  
**Phase 2:** The Decision Loop (Recommend → simulate expected impact → grade its own prediction later).  

---

### RUN IT LOCALLY
1. `git clone https://github.com/6sLOGAN78/show-its-work.git`
2. `pip install -e .`
3. Export the secure proxy (no personal API key needed):
   ```bash
   export SIW_API_BASE="https://show-its-work.vercel.app/api/proxy"
   export SIW_API_KEY="dummy-key"
   ```
4. Start the engine: `./run_local.sh`
