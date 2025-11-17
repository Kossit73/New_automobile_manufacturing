from models.production import AutomobileModel, AssemblyLine, ProductionPlan, simulate_plan, STAGES
import pytest


def test_production_plan_capacity_and_adjustments():
    automobile = AutomobileModel(
        name="EV-SUV",
        stage_minutes={
            "chassis": 120,
            "paint": 90,
            "assembly": 200,
            "quality": 60,
        },
        defect_rate=0.03,
    )
    line = AssemblyLine(
        name="Line A",
        stations={
            "chassis": 3,
            "paint": 2,
            "assembly": 4,
            "quality": 2,
        },
        hours_per_shift=8,
        shifts_per_day=2,
    )

    plan = ProductionPlan(line=line, automobile=automobile, target_units=300, scrap_allowance=0.05)

    assert plan.stage_capacity("assembly") == 19
    assert plan.theoretical_output() == 19
    assert plan.adjusted_output() == 17

    requirements = plan.component_requirements()
    assert requirements["paint"] == 315

    summary = plan.summary()
    assert "EV-SUV" in summary
    assert "Adjusted daily output: 17" in summary

    results = simulate_plan(plan)
    assert results["target_units"] == 300
    assert results["theoretical_daily_output"] == 19
    assert results["adjusted_daily_output"] == 17
    assert results["component_requirements"]["chassis"] == 315


def test_missing_stage_definition():
    with pytest.raises(ValueError):
        AutomobileModel(name="Hatchback", stage_minutes={"chassis": 120, "paint": 90, "assembly": 200})

    with pytest.raises(ValueError):
        AssemblyLine(name="Line B", stations={"chassis": 2, "paint": 2, "assembly": 2})

    automobile = AutomobileModel(
        name="Sedan",
        stage_minutes={stage: 100 for stage in STAGES},
    )
    line = AssemblyLine(name="Line C", stations={stage: 1 for stage in STAGES})
    plan = ProductionPlan(line=line, automobile=automobile, target_units=10)

    with pytest.raises(KeyError):
        plan.stage_capacity("invalid")
