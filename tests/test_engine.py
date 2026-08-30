"""Smoke + behaviour tests. Rebuilds data, then asserts the engine recovers the answer
key and behaves correctly across the mandatory scenarios. Run: pytest -q"""
import pytest

from show_its_work.data.build import build
from show_its_work.engine import investigate
from show_its_work.eval import run_eval


@pytest.fixture(scope="module", autouse=True)
def _data():
    build()   # deterministic (seeded); creates data/synthetic/*


def test_flagship_crowns_planted_cause_and_kills_decoy():
    r = run_eval()
    assert r["root_cause_top1"] is True
    assert r["primary_confidence"] == "HIGH"
    assert r["decoy_rejected"] is True
    assert r["citation_clean"] is True


def test_abstains_on_ambiguous_and_sparse():
    r = run_eval()
    assert all(r["abstained_when_it_should"].values())


def test_no_false_alerts_on_quiet_windows():
    assert run_eval()["false_alert_rate"].startswith("0/")


def test_entitlement_redaction_and_pivot():
    ops = investigate("Why did net revenue drop last week?", "ops_lead")
    assert ops.investigation.kpi != "net_revenue"          # pivoted to a visible KPI
    assert len(ops.investigation.redactions) == 1          # revenue withheld


def test_llm_never_computes_a_number_in_stub():
    r = investigate("Why did net revenue drop last week?", "revenue_analyst")
    assert r.telemetry["llm_calls"] == 0                   # stub default
    assert r.telemetry["non_llm_calls"] > 0                # tools did the work
    assert r.verification["clean"] is True
