"""Streamlit UI — the decision workspace.

Run:  streamlit run src/show_its_work/app.py
Shows the memo, the driver waterfall, the skeptic's debate (with the decoy it killed),
the receipts (provenance + freshness + lineage), and the runtime telemetry ledger
(LLM vs non-LLM). Every number on screen came from a tool, not the model.
"""
from __future__ import annotations

import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from show_its_work.config import GROUND_TRUTH, LLMConfig, RunConfig
from show_its_work.engine import investigate
from show_its_work.memory import CausalMemory
from show_its_work.metrics import kpi_series, load_orders
from show_its_work.semantics import load_personas, load_semantic_contract
from show_its_work.tools import decompose_drivers

st.set_page_config(page_title="Show Its Work", page_icon="🔎", layout="wide")

CONF_COLOR = {"HIGH": "#1a7f37", "MEDIUM": "#9a6700", "INSUFFICIENT": "#8250df"}
PRODUCER_COLOR = {"llm": "#8250df", "deterministic": "#0969da", "statistical": "#1a7f37",
                  "retrieval": "#bf3989", "rule": "#9a6700"}


@st.cache_data
def _gt():
    return json.loads(GROUND_TRUTH.read_text()) if GROUND_TRUTH.exists() else {}


def kpi_chart(kpi: str, window, region=None):
    s = kpi_series(kpi, region=region).dropna()
    w0, w1 = pd.Timestamp(window[0]), pd.Timestamp(window[1])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s.values, mode="lines", name=kpi,
                             line=dict(color="#0969da", width=2)))
    fig.add_vrect(x0=w0, x1=w1, fillcolor="#cf222e", opacity=0.12, line_width=0,
                  annotation_text="window", annotation_position="top left")
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10),
                      title=f"{kpi} — anomaly window shaded", showlegend=False)
    return fig


def waterfall(kpi, window, region=None):
    drivers = decompose_drivers(kpi if kpi == "net_revenue" else kpi, window, "seller_id", region=region)[:6]
    names = [d.group for d in drivers]
    vals = [d.contribution for d in drivers]
    colors = ["#cf222e" if v < 0 else "#1a7f37" for v in vals]
    fig = go.Figure(go.Bar(x=vals, y=names, orientation="h", marker_color=colors,
                           text=[f"{v:,.0f}" for v in vals], textposition="auto"))
    fig.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10),
                      title="Driver contribution to the move (by seller)")
    return fig


def run_panel(r):
    inv = r.investigation
    v = inv.verdict
    c = load_semantic_contract()

    # --- headline + verdict badge ---
    color = CONF_COLOR.get(v.level.value, "#57606a")
    st.markdown(f"### Answer &nbsp; <span style='background:{color};color:#fff;padding:3px 10px;"
                f"border-radius:12px;font-size:0.7em'>{v.level.value} confidence</span>",
                unsafe_allow_html=True)
    for red in inv.redactions:
        st.warning("🔒 " + red)

    tabs = st.tabs(["📝 Memo", "📊 Waterfall", "🔬 The Skeptic", "🧾 Receipts",
                    "⚙️ Telemetry", "🧠 Memory"])

    with tabs[0]:
        st.markdown(inv.memo)

    with tabs[1]:
        col1, col2 = st.columns(2)
        col1.plotly_chart(kpi_chart(inv.kpi, inv.period), use_container_width=True)
        if inv.kpi == "net_revenue":
            col2.plotly_chart(waterfall(inv.kpi, inv.period), use_container_width=True)
        else:
            col2.plotly_chart(kpi_chart("net_revenue", inv.period), use_container_width=True)

    with tabs[2]:
        st.caption("Every hypothesis faces falsification tools. A **killed** row is the skeptic "
                   "doing its job — usually the tempting-but-wrong story.")
        for h in inv.hypotheses:
            killed = h.status.value == "killed"
            icon = "❌ KILLED" if killed else ("✅ SURVIVED" if h.status.value == "survived" else "•")
            with st.expander(f"{icon} — {h.claim}", expanded=killed):
                st.write(f"**Mechanism:** {h.mechanism}")
                if h.explained_share:
                    st.write(f"**Explains:** {h.explained_share:.0%} of the delta")
                for a in h.attacks:
                    mark = "✓" if a.passed else "✗"
                    st.write(f"- `{a.test}` {mark} — {a.detail}")

    with tabs[3]:
        st.caption("Every figure traces to a tool call. Source freshness + lineage from the contract.")
        st.markdown("**Facts** (provenance-bound)")
        st.dataframe(pd.DataFrame([{
            "id": f.id, "statement": f.statement, "producer": f.provenance.producer.value,
            "tool": f.provenance.tool} for f in inv.facts]), use_container_width=True, hide_index=True)
        try:
            fr = c.source_freshness(inv.kpi)
            st.markdown(f"**Source freshness** — `{fr['source']}` · grain **{fr['grain']}** · "
                        f"refresh **{fr['refresh']}** · SLA {fr['freshness_sla_hours']}h · {fr['governance']}")
            st.markdown(f"**Lineage** — {' → '.join(c.kpi(inv.kpi).lineage)}")
        except Exception:
            pass
        st.markdown("**Evidence** (unstructured trail)")
        st.dataframe(pd.DataFrame([{
            "id": e.id, "source": e.source, "text": e.text, "score": e.score}
            for e in inv.evidence]), use_container_width=True, hide_index=True)
        st.success(f"Citation check: {r.verification['citations_valid']}/"
                   f"{r.verification['citations_found']} resolve · clean={r.verification['clean']}")

    with tabs[4]:
        t = r.telemetry
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total latency", f"{t['total_latency_ms']:.0f} ms")
        c2.metric("LLM calls", t["llm_calls"])
        c3.metric("Tokens", t["input_tokens"] + t["output_tokens"])
        c4.metric("Est. cost", f"${t['estimated_cost_usd']:.5f}")
        st.info(f"**LLM computed {0} numbers.** The model {'wrote the memo' if t['llm_calls'] else 'was not called (stub) — the deterministic core did everything'}. "
                f"{t['non_llm_calls']} non-LLM steps produced every figure.")
        led = pd.DataFrame(r.telemetry_events or [])
        if not led.empty:
            led = led[["step", "kind", "latency_ms", "model", "input_tokens", "output_tokens", "cost_usd"]]
            st.dataframe(led, use_container_width=True, hide_index=True)
        # LLM vs non-LLM bar
        by = t["work_by_producer"]
        fig = go.Figure(go.Bar(x=list(by.values()), y=list(by.keys()), orientation="h",
                               marker_color=[PRODUCER_COLOR.get(k, "#888") for k in by]))
        fig.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10), title="Work by producer")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[5]:
        st.caption("Confirmed cause→effect links persist and strengthen — the engine learns.")
        cm = CausalMemory()
        st.dataframe(pd.DataFrame(cm.edges()), use_container_width=True, hide_index=True)
        for n in inv.notes:
            st.write("•", n)


def main():
    st.title("🔎 Show Its Work")
    st.caption("A KPI intelligence-to-action engine · the LLM never computes a number · "
               "AIC 2026 · PS3 · Team Mandalorians")

    personas = load_personas()
    gt = _gt()
    default_window = gt.get("window", ["2024-05-08", "2024-05-23"])

    with st.sidebar:
        st.header("Ask")
        persona = st.selectbox("Persona", list(personas), index=list(personas).index("revenue_analyst"), format_func=lambda k: personas[k].label)
        question = st.text_input("Question", "Why did our net revenue drop last week?")
        st.caption("Try the Ops Lead persona to see role-based redaction.")
        with st.expander("Scenario windows"):
            st.write("Flagship:", default_window)
            st.write("Ambiguous (abstain):", gt.get("ambiguous_case", {}).get("window"))
            st.write("Sparse: 2024-01-02 → 2024-01-12")
            st.write("Noise: 2024-02-05 → 2024-02-20")
        wstart = st.text_input("Window start", default_window[0])
        wend = st.text_input("Window end", default_window[1])
        provider = st.selectbox("LLM provider", ["stub", "ollama", "api"],
                                help="stub = no LLM; the deterministic core runs the whole thing")
        go_btn = st.button("Investigate", type="primary", use_container_width=True)

    if go_btn or "last" not in st.session_state:
        cfg = RunConfig(llm=LLMConfig(provider=provider))
        st.session_state["last"] = investigate(question, persona, window=(wstart, wend), cfg=cfg)
    run_panel(st.session_state["last"])


main()
