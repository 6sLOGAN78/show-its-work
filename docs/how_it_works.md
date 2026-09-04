# How It Works: The 5-Step Engine

The "Show Its Work" Business Intelligence engine operates on a strict pipeline designed to prevent AI hallucinations. By strictly separating deterministic mathematical computation from language generation, the system ensures that every metric and root cause is mathematically verifiable.

Below is a detailed breakdown of the 5 core components, how they function, and the underlying technologies powering them.

---

## 1. The Statistical Gate (Is the drop even real?)

**What it does:**  
Prevents alert fatigue and saves compute costs by halting the system if a metric movement is just normal seasonal variance or noise. The LLM is never invoked if the data isn't statistically material.

**How it works:**  
1. It fetches the raw time-series data for a given metric.
2. It strips out weekly seasonality by subtracting day-of-week means from the data.
3. It establishes a local baseline using a **Median Absolute Deviation (MAD)** robust mean-shift Z-test. MAD is used instead of standard deviation because it is highly resistant to extreme outliers.
4. If the resulting Z-score is below a strict threshold (e.g., `< 3.0`), or if the absolute business impact (e.g., total dollars lost) is too small, the system terminates the run early.

**What is used there:**  
- **Files:** `src/show_its_work/tools/detect.py`
- **Libraries/Tech:** `pandas`, `numpy`, `scipy` (for deseasonalization and statistical thresholds).

---

## 2. The Proposer (Who is the suspect?)

**What it does:**  
If a drop passes the Statistical Gate, the Proposer breaks down the aggregate loss to find the specific segments (e.g., a specific seller, a product category, or a region) responsible for the shortfall.

**How it works:**  
1. **Waterfall Attribution:** It executes an exact additive breakdown of the KPI over the anomalous window versus the baseline. For example, it calculates exactly how much revenue was lost by `seller_A` vs `seller_B`.
2. **Simpson's Paradox Guard:** It splits the aggregate change into a *within-group effect* and a *mix effect*. If a metric changed simply because a high-performing category artificially took more volume share (a mix shift), the engine calculates the `simpson_risk`. If the risk is high, it halts blind attribution, preventing the system from blaming a false driver.

**What is used there:**  
- **Files:** `src/show_its_work/tools/decompose.py`
- **Libraries/Tech:** `pandas` (for highly efficient split-apply-combine aggregations and weighting).

---

## 3. The Skeptic (Interrogating the suspect)

**What it does:**  
This is the core analytical differentiator. The Skeptic acts as a prosecutor against the Proposer's hypotheses. Just because two events happened at the same time does not mean one caused the other; the Skeptic actively tries to falsify correlations.

**How it works:**  
It runs four explicit, deterministic tests:
1. **Temporal Alignment:** Locates the exact onset day of the cause and effect (using a `mean - 1.5*std` bound). It verifies that the cause strictly preceded the effect.
2. **Control Group Test:** If the hypothesis claims a "market-wide competitor sale" caused the drop, the Skeptic checks the control group (the rest of the market). If the damage is heavily concentrated in just one seller, the market-wide narrative is falsified and killed.
3. **Counterfactual Estimate:** It mathematically removes the suspected culprit from the dataset. If the overall KPI drop disappears (or closes by >15%), the hypothesis is strengthened.
4. **Signature Match:** It checks if predicted secondary ripples actually manifest in the data (e.g., if deliveries are late, do review scores also drop?).

**What is used there:**  
- **Files:** `src/show_its_work/tools/falsify.py`, `src/show_its_work/agents/reasoning.py`
- **Libraries/Tech:** `pandas` dataframes for control group isolation and counterfactual mathematics.

---

## 4. The Honest Judge

**What it does:**  
Evaluates all hypotheses that survived the Skeptic's tests and issues a final, calibrated verdict.

**How it works:**  
The Judge uses a strict Boolean rubric rather than subjective LLM logic. It calculates `sum(crit)`, checking if the hypothesis passed temporal alignment, passed the control group test, has corroborating documentation, and explains >50% of the drop.
- If the score is perfect, it assigns `HIGH` confidence.
- If the data is diffuse (no single seller concentrated) or the evidence contradicts itself, the Judge outputs an `INSUFFICIENT` verdict. It is explicitly programmed to abstain and say *"I don't know yet"* rather than hand the user a plausible-sounding guess.

**What is used there:**  
- **Files:** `src/show_its_work/agents/reasoning.py`
- **Libraries/Tech:** Core Python logic, `Pydantic` models for strict state management (`HypothesisStatus`, `ConfidenceLevel`).

---

## 5. The Narrative Writer & Verifier (The only AI touchpoint)

**What it does:**  
Translates the hard, mathematical facts into a human-readable business memo, and rigidly verifies that the LLM didn't hallucinate.

**How it works:**  
1. The engine constructs a completely deterministic "Fact Pack" (a string template of the final numbers).
2. The LLM (Gemini) is prompted to rewrite this Fact Pack into a warm, persona-specific memo (e.g., tailoring the tone for an Ops Lead vs a CFO) while retaining all inline `[F###]` citations.
3. **The Verifier Guard:** After the LLM generates the text, a deterministic Regex scanner combs through the memo. It verifies that every single citation exists in the original Fact Pack. If the LLM invents a number or hallucinated a citation, it flags the memo (`clean=False`), ensuring strict provenance and absolute trust.

**What is used there:**  
- **Files:** `src/show_its_work/agents/narrative.py`, `src/show_its_work/llm/client.py`
- **Libraries/Tech:** 
  - `re` (Regex for citation verification).
  - `urllib.request` (for the LLM Client). 
  - **Automatic Fallback:** The LLM client automatically cascades through multiple Gemini models (from `gemini-3.6-flash` down to a 0-cost deterministic stub) if rate limits are hit, ensuring the engine never crashes.
