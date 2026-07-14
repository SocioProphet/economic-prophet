import math

from open_ep_framework.vdt import summarize_vdt
from open_ep_framework.vdt_multiperiod import summarize_vdt_multiperiod


def _profile(horizon=3, discount=0.0):
    return {
        "run_id": "vdt-mp-test-001",
        "scenario": "mp-test",
        "as_of": "2026-07-14T00:00:00Z",
        "framework_version": "0.1.0",
        "industry": "TEST",
        "enterprise_value_baseline": 1000.0,
        "horizon_years": horizon,
        "discount_rate": discount,
        "drivers": ["RevenueGrowth", "CostEfficiency"],
        "domains": ["CustomerInterface", "SupplyDelivery"],
        "weights": [
            {"driver": "RevenueGrowth", "domain": "CustomerInterface", "weight": 0.5},
            {"driver": "CostEfficiency", "domain": "SupplyDelivery", "weight": 0.5},
        ],
        "kpis": [
            {"driver": "RevenueGrowth", "domain": "CustomerInterface", "kpi": "sss",
             "delta_pct": 10.0, "polarity": "higher_better", "accumulation": "compounding"},
            {"driver": "CostEfficiency", "domain": "SupplyDelivery", "kpi": "cogs",
             "delta_pct": -10.0, "polarity": "lower_better", "accumulation": "step"},
        ],
        "measurement_boundary": {"mode": "audit_only", "non_goals": ["investment_advice"]},
    }


def test_year1_matches_single_period():
    prof = _profile(horizon=5)
    mp = summarize_vdt_multiperiod(prof)
    sp = summarize_vdt(prof)
    y1 = mp["periods"][0]
    assert math.isclose(y1["total_value_uplift"], sp["computed_total_value_uplift"], rel_tol=1e-9)
    assert math.isclose(y1["projected_enterprise_value"], sp["projected_enterprise_value"], rel_tol=1e-9)


def test_compounding_grows_step_flat():
    mp = summarize_vdt_multiperiod(_profile(horizon=3))
    # compounding sss: cumulative fraction (1.1^t - 1) * weight * ev
    ev, w = 1000.0, 0.5
    for i, t in enumerate((1, 2, 3)):
        sss = next(k for k in mp["periods"][i]["per_kpi_contribution"] if k["kpi"] == "sss")
        cogs = next(k for k in mp["periods"][i]["per_kpi_contribution"] if k["kpi"] == "cogs")
        assert math.isclose(sss["value_contribution"], ((1.1 ** t) - 1) * w * ev, rel_tol=1e-9)
        assert math.isclose(cogs["value_contribution"], 0.10 * w * ev, rel_tol=1e-9)  # step held flat


def test_present_value_discounts_stream():
    undiscounted = summarize_vdt_multiperiod(_profile(horizon=4, discount=0.0))
    discounted = summarize_vdt_multiperiod(_profile(horizon=4, discount=0.10))
    assert discounted["present_value_of_uplift"] < undiscounted["present_value_of_uplift"]
    # undiscounted PV of the incremental stream == terminal cumulative uplift
    assert math.isclose(undiscounted["present_value_of_uplift"],
                        undiscounted["terminal_total_value_uplift"], rel_tol=1e-9)


def test_non_goals_preserved():
    mp = summarize_vdt_multiperiod(_profile())
    assert "investment_advice" in mp["required_non_goals_present"]


def test_horizon_must_be_positive():
    prof = _profile(horizon=0)
    try:
        summarize_vdt_multiperiod(prof)
    except ValueError:
        return
    raise AssertionError("expected ValueError for horizon_years < 1")
