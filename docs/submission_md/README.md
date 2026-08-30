# SHOW ITS WORK
**AIC 2026 · PS3 BUSINESSINTELLIGENCE.AI**  
**TEAM MANDALORIANS · IIT PATNA**

---

# THE CASE OF THE VANISHING REVENUE
### A ROOT-CAUSE INVESTIGATION THAT SHOWS ITS WORK — EVERY NUMBER TRACED TO THE TOOL THAT COMPUTED IT.

The CFO doesn’t want a chart. They want to know *why* revenue just vanished (R$103,394 gone in a single fortnight), and they want it before standup. 

The old way requires days of spreadsheets and Slack archaeology. The first AI copilots promised answers in seconds, but they didn't lie about the prose—**they lied about the numbers.**

**One rule changes everything:**
### THE LLM NEVER COMPUTES A NUMBER

A deterministic core computes every figure. A proposer / skeptic / judge loop argues it out. Every sentence clicks through to the tool call and the source behind it. When the evidence isn’t there, it says so.

---

## 1. THE MACHINE (How It Works)
Gate runs before any LLM call; Verify strips any ungrounded sentence.

1. **INTENT:** Maps the user question.
2. **GATE (Is It Real?):** Most alerts are noise. Before accusing anyone, the gate asks whether the move is even real using a deseasonalised, robust mean-shift test against a local baseline. Run before any LLM call.
3. **FACTPACK:** Gathers governed semantic metrics.
4. **PROPOSE (The Suspects):** The engine decomposes the loss across every dimension. (e.g., `house_bravos`, `health_beauty`, competitor flash sale).
5. **SKEPTIC (The Interrogation):** Every hypothesis must declare a falsifiable signature; the skeptic attacks the strongest few. No correlation survives all four tests:
   - *Temporal Alignment*
   - *Control Group*
   - *Counterfactual*
   - *Signature*
6. **JUDGE (The Honest Detective):** Sometimes the right answer is *"I don't know yet"*. If a dip is diffuse and evidence contradicts itself, it outputs **INSUFFICIENT**. It would rather flag this than hand you a story that sounds right.
7. **ACTIONS:** Recommend business levers based on the surviving culprit.
8. **VERIFY:** The LLM receives the fact-pack and drafts the memo. The Verifier strips any sentence if the model invented the number.

---

## 2. THE CULPRIT: ONE SELLER’S DELIVERIES BROKE THE WHOLE METRIC
The culprit never touched revenue directly. The engine walked the chain link by link — each hop cited to a tool call and a source document.

* **On-Time Delivery ↓ (-26 pt):** `house_bravos` misses SLA 4+ weeks
* **Review Score ↓ (4.4 → 3.1):** buyers punish the late orders
* **Repeat Purchase ↓ (-18%):** they simply don't come back
* **Net Revenue ↓ (-R$103K):** the number the CFO saw

While a human or basic chatbot would blame the "Competitor Flash Sale" (a tidy, market-wide story), the Skeptic rejects it because it leaves no structured footprint in the data.

---

## 3. EVERY CLAIM IS A RECEIPT
Each sentence in the final memo clicks through to its tool call and source document. Swap the model for a stub with no LLM — the numbers come back identical.

**THE LLM COMPUTED 0 NUMBERS.**
- **42%** Deterministic
- **26%** Statistical
- **20%** Retrieval
- **12%** Rule-based
- **0%** LLM Share of Compute

---

## 4. GOVERNED PER ROLE
**One Investigation, A Different Correct Answer Per Role.**
A semantic contract defines every metric — the engine can't invent one. Entitlements are enforced at the compute layer, not the UI. Redactions are explicit and audited.

* **Revenue Analyst:** Sees everything (-R$103,394 Net Revenue).
* **Ops / Fulfilment Lead:** Finance figures redacted. Sees SLA breach and On-Time Delivery drop.
* **Regional Manager (South):** Scoped to one region. Other regions hidden.

---

## 5. FROM DETECTIVE TO ADVISOR
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
3. Export the secure proxy (no API key needed):
   ```bash
   export SIW_API_BASE="https://show-its-work.vercel.app/api/proxy"
   export SIW_API_KEY="dummy-key"
   ```
4. Start the engine: `./run_local.sh`
