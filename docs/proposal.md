# Business Proposal — Show Its Work
### A KPI intelligence-to-action engine you can trust
**AIC 2026 · PS3 BusinessIntelligence.ai · Team Mandalorians (IIT Patna)**

---

## 1. Problem framing

Every enterprise has dashboards that show **what** changed. Almost none can reliably explain
**why**, or say what to do about it. Today that gap is filled by an analyst doing days of
export → pivot → hypothesise → chase-a-Slack-thread, and by the time the answer lands the
damage is done. The first wave of "AI BI copilots" made this worse in a specific way: they let a
language model *narrate numbers it made up*, which is fine in a demo and dangerous in a boardroom.

The real job has three hard parts that a chatbot-over-CSV skips:
1. **Is the move even real?** Most KPI wiggles are noise; flagging them all trains people to ignore alerts.
2. **Is it causation or coincidence?** The obvious correlation is often a decoy.
3. **What if it's genuinely ambiguous?** A trustworthy system must be willing to say "I don't know — here's what I'd need."

## 2. Solution design

**Show Its Work** is a decision workspace where the LLM is *never* the source of a number.
A deterministic core computes every figure; a proposer/**skeptic**/judge loop turns "these moved
together" into "this survived four attempts to kill it"; and every sentence in the memo is
**click-through to the tool call and the source document** behind it. When the evidence isn't
there, it abstains with calibrated confidence instead of guessing.

Three design choices are the moat:
- **Provenance-bound compute.** Swap the model for a stub and the numbers are identical — the
  proof that the LLM only phrases, never computes. This makes the mandatory "LLM vs non-LLM"
  breakdown trivially, visibly true.
- **A skeptic that rejects decoys.** Our headline metric is **decoy-rejection rate** — the share
  of tempting-but-wrong explanations the system kills before a human sees them.
- **Governed and role-aware.** A semantic contract defines every metric; entitlements mean the
  same question returns a different, correctly-redacted answer per persona.

## 3. Target users

| Persona | Job to be done | What they get |
|---|---|---|
| **Revenue / Finance analyst** | Explain a movement to leadership, defensibly | Full waterfall + confidence + what's still unknown |
| **Fulfilment / Ops lead** | Catch a failing seller/carrier fast | Operational root cause, finance figures redacted |
| **Regional manager** | Own one region end-to-end | Region-scoped memo (row-level security) |
| **BI / data platform team** | Trust and govern the tool | Semantic contract, audit trail, cost telemetry |

## 4. Business case & impact

- **Time-to-root-cause: days → seconds.** The analyst hours spent per material movement collapse
  to a reviewed memo.
- **Alert fatigue down.** The statistical gate stops the bulk of runs before any LLM cost, so
  people trust the alerts that do fire.
- **Decisions get better, not just faster.** The skeptic removes confident-wrong conclusions —
  the expensive kind — and every claim is auditable, which is what unlocks adoption in regulated
  and finance functions.
- **LLM economics under control.** Gate-before-LLM + cached deterministic facts + a minimal LLM
  footprint (phrasing only) mean cost-per-insight is measured and low, and reproducible: the same
  question returns the same number twice.

## 5. Phased roadmap

- **Phase 0 — this prototype (done).** End-to-end mechanism on illustrative data: 4 connected
  KPIs, skeptic + decoy rejection, abstention, personas + entitlements, telemetry, causal memory.
- **Phase 1 — connect real sources.** Swap the synthetic layer for warehouse + ticketing/CRM
  connectors; formalise the semantic contract with the data team; embeddings-based retrieval.
- **Phase 2 — the decision loop.** Recommend → simulate expected impact → **grade its own
  prediction later**, so recommendations earn calibrated trust over time.
- **Phase 3 — scale & govern.** Multi-tenant entitlements, drift monitoring, feedback-driven
  causal-graph learning across teams, human-in-the-loop correction workflows.

## 6. Key risks & mitigations

| Risk | Mitigation |
|---|---|
| **LLM hallucinates a number** | Structurally impossible in the memo path — verifier strips any figure not in the fact pack; numbers come only from tools. |
| **Over-flagging / alert fatigue** | Statistical gate + governed business-materiality thresholds; most runs end before the LLM. |
| **Over-claiming causation** | Falsification battery (temporal, control, counterfactual, signature) + explicit abstention when it fails. |
| **Wrong metric definitions** | Governed semantic contract is the single source of truth; the engine cannot redefine a metric. |
| **Data / model drift** | Episodic store + causal-graph decay-on-contradiction + telemetry make drift observable and correctable. |
| **Security / entitlement leakage** | Row/column/domain entitlements enforced at the compute layer, not just the UI; redactions are explicit and audited. |

## 7. What to look at in the prototype
Run `python -m show_its_work.run eval` for the scorecard, then open the Streamlit app: the **Skeptic**
tab (watch it kill the competitor-sale decoy), the **Receipts** tab (provenance + freshness +
lineage), and the **Telemetry** tab ("the LLM computed 0 numbers").
