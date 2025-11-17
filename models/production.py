"""Production modeling utilities for automobile manufacturing lines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Tuple


STAGES = ("chassis", "paint", "assembly", "quality")


def _validate_stage_keys(mapping: Dict[str, int]) -> Dict[str, int]:
    """Ensure all expected stage keys are present in the mapping."""

    missing = [stage for stage in STAGES if stage not in mapping]
    if missing:
        raise ValueError(f"Missing capacity definitions for stages: {', '.join(missing)}")
    return mapping


@dataclass(frozen=True)
class AutomobileModel:
    """Represents the time and risk profile for a specific automobile design."""

    name: str
    stage_minutes: Dict[str, int]
    defect_rate: float = 0.02

    def __post_init__(self) -> None:
        _validate_stage_keys(self.stage_minutes)
        if not 0 <= self.defect_rate < 1:
            raise ValueError("defect_rate must be between 0 and 1")

    @property
    def cycle_minutes(self) -> int:
        """Total minutes required for one unit to move through all stages."""

        return sum(self.stage_minutes[stage] for stage in STAGES)


@dataclass(frozen=True)
class AssemblyLine:
    """Represents capacity and shifts for an assembly line."""

    name: str
    stations: Dict[str, int]
    hours_per_shift: int = 8
    shifts_per_day: int = 2

    def __post_init__(self) -> None:
        _validate_stage_keys(self.stations)
        if self.hours_per_shift <= 0:
            raise ValueError("hours_per_shift must be positive")
        if self.shifts_per_day <= 0:
            raise ValueError("shifts_per_day must be positive")
        for stage, count in self.stations.items():
            if count <= 0:
                raise ValueError(f"Station count for {stage} must be positive")

    @property
    def available_minutes(self) -> Dict[str, int]:
        """Calculate available minutes per stage across all stations per day."""

        minutes_per_station = self.hours_per_shift * self.shifts_per_day * 60
        return {
            stage: count * minutes_per_station for stage, count in self.stations.items()
        }


@dataclass
class ProductionPlan:
    """Links a model with an assembly line and a target volume."""

    line: AssemblyLine
    automobile: AutomobileModel
    target_units: int
    scrap_allowance: float = 0.05
    notes: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.target_units <= 0:
            raise ValueError("target_units must be positive")
        if not 0 <= self.scrap_allowance < 1:
            raise ValueError("scrap_allowance must be between 0 and 1")

    def stage_capacity(self, stage: str) -> int:
        """Maximum units per day that the stage can support."""

        if stage not in STAGES:
            raise KeyError(f"Unknown stage '{stage}'")
        available = self.line.available_minutes[stage]
        required = self.automobile.stage_minutes[stage]
        return available // required

    def theoretical_output(self) -> int:
        """Units per day before considering scrap or defects."""

        return min(self.stage_capacity(stage) for stage in STAGES)

    def adjusted_output(self) -> int:
        """Units per day after accounting for both scrap and defect rate."""

        throughput = self.theoretical_output()
        loss_factor = (1 - self.scrap_allowance) * (1 - self.automobile.defect_rate)
        return int(throughput * loss_factor)

    def component_requirements(self) -> Dict[str, int]:
        """Break down the number of units needed per stage for the target volume."""

        return {
            stage: int(self.target_units / (1 - self.scrap_allowance))
            for stage in STAGES
        }

    def summary(self) -> str:
        """Human-readable overview of the plan assumptions."""

        lines = [
            f"Production plan for {self.automobile.name} on {self.line.name}",
            f"Target units: {self.target_units}",
            f"Theoretical daily output: {self.theoretical_output()}",
            f"Adjusted daily output: {self.adjusted_output()}",
        ]
        if self.notes:
            lines.append("Notes:")
            lines.extend(f"- {note}" for note in self.notes)
        return "\n".join(lines)


def simulate_plan(plan: ProductionPlan) -> Dict[str, int]:
    """Run a simple simulation summarizing a production plan's capacity."""

    return {
        "target_units": plan.target_units,
        "theoretical_daily_output": plan.theoretical_output(),
        "adjusted_daily_output": plan.adjusted_output(),
        "component_requirements": plan.component_requirements(),
    }


__all__ = [
    "AutomobileModel",
    "AssemblyLine",
    "ProductionPlan",
    "simulate_plan",
]
