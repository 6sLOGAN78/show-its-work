# How It Works: System Architecture Q&A

The "Show Its Work" Business Intelligence engine operates on a strict pipeline designed to prevent AI hallucinations. By strictly separating deterministic mathematical computation from language generation, the system ensures that every metric and root cause is mathematically verifiable. 

Here is how the 5-step engine works, explained through the questions it answers.

---

### Q: How does the system know a metric drop is actually a real problem and not just normal seasonal noise?
**A: The Statistical Gate (`detect.py`)**

Before the LLM is ever invoked, the system runs a strict mathematical check to prevent alert fatigue.
1. It fetches the raw time-series data and strips out weekly seasonality (subtracting day-of-week means).
2. It establishes a local baseline using a **Median Absolute Deviation (MAD)** robust mean-shift Z-test (which is highly resistant to extreme outliers).
3. **The result:** If the Z-score is below a strict threshold (e.g., `< 3.0`), or if the total dollars lost isn't material, the system terminates early. It knows the drop is just noise.

### Q: Once a real drop is confirmed, how does the engine figure out who or what caused it?
**A: The Proposer (`decompose.py`)**

The engine mathematically breaks down the aggregate loss to find the specific segment (e.g., a specific seller, a product category, or a region) responsible for the shortfall. It executes a precise "waterfall attribution," calculating exactly how much revenue was lost by `seller_A` versus `seller_B`.

### Q: How does the engine avoid being tricked by "Simpson's Paradox" or mix-shifts?
**A: The Mix-Shift Guard (`decompose.py`)**

A massive risk in BI is blaming a drop on a driver when it is actually just a mix shift (e.g., a high-AOV category taking more volume). The engine explicitly splits the aggregate change into a *within-group effect* and a *mix effect*. If the mix effect heavily overrides the actual drop, the `simpson_risk` flag fires and halts blind attribution.

### Q: Just because a seller's deliveries failed at the same time revenue dropped doesn't mean one caused the other. How does the system prove correlation isn't just coincidence?
**A: The Skeptic (`falsify.py`)**

This is the core differentiator. The Skeptic acts as a prosecutor and runs four explicit, deterministic tests to falsify correlations:
1. **Temporal Alignment:** Locates the exact onset day (using a `mean - 1.5*std` bound) to verify the cause strictly preceded the effect.
2. **Control Group Test:** If the hypothesis claims a "market-wide competitor sale" caused the drop, the Skeptic checks the rest of the market. If the damage is concentrated in just one seller, the market-wide narrative is falsified.
3. **Counterfactual Estimate:** It mathematically removes the suspected culprit from the dataset. If the overall KPI drop disappears, the hypothesis is strengthened.
4. **Signature Match:** It checks if predicted secondary ripples actually manifest (e.g., if deliveries are late, do review scores also drop?).

### Q: What happens if the data is messy, diffuse, or the evidence contradicts itself?
**A: The Honest Judge (`reasoning.py`)**

The Judge uses a strict Boolean rubric rather than subjective LLM logic. It calculates a score based on temporal alignment, control group success, corroborating documentation, and the percentage of the drop explained. 

If the data is diffuse (no single seller concentrated) or contradictory, the Judge issues an `INSUFFICIENT` verdict. It is explicitly programmed to abstain and say *"I don't know yet"* rather than hand the user a plausible-sounding guess.

### Q: If the LLM never computes a number, how is the final report written without the AI hallucinating?
**A: The Narrative Writer & Verifier (`narrative.py` & `client.py`)**

1. **The Fact Pack:** The engine constructs a completely deterministic string template of the final, proven numbers.
2. **The LLM Writer:** Gemini is prompted to rewrite this Fact Pack into a warm, persona-specific memo (e.g., tailoring the tone for an Ops Lead vs. a CFO) while keeping all inline `[F###]` citations.
3. **The Verifier Guard:** After generation, a deterministic Regex scanner combs through the memo. It verifies that every single citation exists in the original Fact Pack. If the LLM invents a number, it flags the memo (`clean=False`), ensuring strict provenance and absolute trust. (The LLM client also features an automatic fallback, cascading down to a 0-cost deterministic stub if rate limits are hit).
