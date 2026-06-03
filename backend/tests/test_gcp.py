"""Unit tests for the GCP cost guard and machine-type helpers (no live GCP)."""

from app.integrations import gcp


def test_machine_basename():
    assert gcp.machine_basename(
        "https://www.googleapis.com/compute/v1/projects/p/zones/z/machineTypes/e2-small"
    ) == "e2-small"
    assert gcp.machine_basename("zones/z/machineTypes/e2-medium") == "e2-medium"


def test_specs_lookup():
    vcpu, mem, usd = gcp.specs_for("e2-small")
    assert vcpu == 2 and mem == 2048 and usd > 0
    assert gcp.specs_for("does-not-exist") == (0, 0, 0.0)


def test_within_budget_allows_cheap_type():
    # e2-standard-2 (~$49/mo ~= 67k KRW) is within a 300k KRW ceiling.
    assert gcp.within_budget("e2-standard-2", 300_000, 1360.0) is True


def test_within_budget_rejects_expensive_type():
    # e2-standard-8 (~$196/mo ~= 266k KRW) ... still under; standard-8*... ensure
    # something over the ceiling is rejected via a tiny budget.
    assert gcp.within_budget("e2-standard-8", 100_000, 1360.0) is False


def test_within_budget_rejects_unknown_type():
    # Unknown (unpriced) machine types must not silently pass the guard.
    assert gcp.within_budget("z3-megamem-999", 300_000, 1360.0) is False


def test_monthly_cost_scales_with_fx():
    low = gcp.monthly_cost_krw("e2-small", 1000.0)
    high = gcp.monthly_cost_krw("e2-small", 1360.0)
    assert high > low > 0
