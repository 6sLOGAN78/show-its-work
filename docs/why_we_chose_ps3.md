# Why We Chose PS3: Strategic Q&A

When the Accenture Innovation Challenge released the four problem statements, they represented a wide spectrum of critical enterprise challenges. After careful evaluation, Team Mandalorians unanimously chose **PS3: BusinessIntelligence.ai**. 

Here is a detailed Q&A breaking down our strategic and technical rationale for selecting PS3 over the other options.

---

### Q: Out of the four Accenture Innovation Challenge problem statements, why did Team Mandalorians choose PS3?
**A:** We chose PS3 because it operated in the **Foundational Trust Layer** of Enterprise AI, rather than the "Application Layer." While other problem statements might allow for "fuzzy" AI (where slightly different chatbot phrasing is perfectly acceptable), Business Intelligence requires absolute, mathematical precision. We wanted to tackle the hardest unsolved problem in Enterprise AI today: **How do you build a generative system where a CEO can trust every single number?**

### Q: Why is building AI for Business Intelligence harder than building a standard customer service chatbot?
**A:** The "Hallucination Barrier." If an AI hallucinates an adjective in a customer email, it is usually fine. If a CFO asks why revenue dropped by $100,000, and the AI hallucinates a single digit or blames the wrong department, the business could make catastrophic financial decisions. We chose PS3 to prove that by forcing the LLM to *never compute a number*, we could solve the hallucination barrier entirely.

### Q: Did you just build an AI wrapper over a dataset?
**A:** No. A common approach to AI hackathons is to simply pass a CSV to an LLM, write a clever prompt, and ask it to "find insights." We knew this approach fails in the real world. 

We chose PS3 because it demanded deep, algorithmic computer science. It gave us the canvas to build a **Deterministic Core**:
- Writing strict Python algorithms to calculate **Median Absolute Deviations (MAD)**.
- Building explicit guards against **Simpson's Paradox** (mix-shift effects).
- Developing a **Skeptic Agent** that uses control groups and counterfactual mathematics to actively falsify correlations.

### Q: What is the real-world business value (ROI) of solving PS3?
**A:** Dashboards are excellent at telling executives *what* happened (e.g., "Revenue is down 10%"). However, human analysts currently spend days or weeks performing "Slack archaeology" and exporting spreadsheets to figure out *why* it happened and *what* to do about it.

By solving PS3, we are compressing a week-long diagnostic slog into a 45-second automated investigation. The Return on Investment (ROI) of an engine that can instantly trace a revenue drop to a specific supplier's SLA failure—without hallucinating—is astronomically high for any Fortune 500 company. It is a highly commercializable, enterprise-ready solution.

### Q: How does this project demonstrate the future of Generative AI?
**A:** We chose PS3 to prove that the era of the simple "chat window" is over. 

While other problem statements might be solved with a standard RAG (Retrieval-Augmented Generation) chatbot, PS3 required a true **Multi-Agent Orchestration Architecture**. We built an autonomous system (The Proposer, The Skeptic, and The Judge) that debates itself, interrogates its own hypotheses, and—most importantly—has the programmed honesty to output an `INSUFFICIENT` verdict and say *"I don't know"* when the evidence is messy or contradictory. 

PS3 allowed us to move past AI hype and build a mathematically defensible product.
