"""Unit tests for the pure live-test simulation (no DB, no GCP)."""

from __future__ import annotations

from app.core import livetest


def test_provisioning_phase_has_no_cpu_yet():
    st = livetest.simulate(0.0)
    assert st.phase == "provisioning"
    assert st.node_status == "PROVISIONING"
    assert st.series == []
    assert st.cpu_now is None
    assert st.scaled is False and st.done is False
    assert st.forecast is None and st.recommendation is None
    assert st.spec == livetest.PRE


def test_running_then_load_climbs_past_threshold():
    running = livetest.simulate(4.0)
    assert running.node_status == "RUNNING"
    assert running.series and running.cpu_now is not None
    assert running.cpu_now < livetest.THRESHOLD  # idle baseline below the ceiling

    peak = livetest.simulate(livetest.T_SCALE - 0.1)  # just before scale-up
    assert peak.cpu_now > livetest.THRESHOLD          # load drove it over the ceiling
    assert peak.scaled is False


def test_forecast_predicts_a_breach_before_scaling():
    st = livetest.simulate(12.0)
    assert st.phase == "forecast"
    assert st.forecast is not None and st.forecast["predicted"] > 100.0
    assert st.recommendation is not None
    assert st.recommendation["recommended_vcpu"] == livetest.POST["vcpu"]
    assert st.scaled is False


def test_scaleup_switches_spec_and_status():
    st = livetest.simulate(livetest.T_SCALE + 0.2)
    assert st.scaled is True
    assert st.spec == livetest.POST
    assert st.node_status == "RESIZING"


def test_done_state_settles_under_threshold():
    st = livetest.simulate(livetest.T_DONE + 1.0)
    assert st.done is True and st.scaled is True
    assert st.node_status == "RUNNING"
    assert st.cpu_now is not None and st.cpu_now < livetest.THRESHOLD  # capacity doubled
    keys = {e["key"] for e in st.events}
    assert {"ev_running", "ev_load", "ev_forecast", "ev_scale"} <= keys
