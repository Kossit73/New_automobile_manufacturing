# New_automobile_manufacturing

This repository contains a lightweight simulation model for planning automobile manufacturing throughput. It focuses on four key stages (chassis, paint, assembly, and quality) and helps estimate daily capacity while accounting for scrap and defect rates.

## Usage

The production utilities live in `models/production.py` and expose dataclasses for describing your plant and vehicle assumptions. The snippet below shows a basic configuration and how to retrieve a capacity summary.

```python
from models.production import AutomobileModel, AssemblyLine, ProductionPlan, simulate_plan

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
print(plan.summary())
print(simulate_plan(plan))
```

Running the above produces a concise summary of the expected daily throughput and material requirements per stage.

## Development

Install the test dependencies and run the suite with `pytest`:

```bash
python -m pip install -r requirements.txt
python -m pytest
```
