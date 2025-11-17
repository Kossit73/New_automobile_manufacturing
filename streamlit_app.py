"""Interactive Streamlit front-end for the automobile production model.

This app lets you configure an automobile design, assembly line, and
production plan, then visualize the implied capacity and component
requirements. It also links to the RAG feasibility service shipped in
``rag_app.py`` so deployments can expose both experiences from the same
repository.
"""

from __future__ import annotations

import json
from typing import Dict

import pandas as pd
import streamlit as st

from models.production import (
    AutomobileModel,
    AssemblyLine,
    ProductionPlan,
    STAGES,
    simulate_plan,
)

st.set_page_config(
    page_title="Automobile Manufacturing Planner",
    page_icon="🚗",
    layout="wide",
    menu_items={
        "About": "Plan automobile production throughput and explore the RAG feasibility service.",
    },
)


def _default_stage_minutes() -> Dict[str, int]:
    return {"chassis": 120, "paint": 90, "assembly": 200, "quality": 60}


def _default_stations() -> Dict[str, int]:
    return {"chassis": 3, "paint": 2, "assembly": 4, "quality": 2}


if "plan_inputs" not in st.session_state:
    st.session_state.plan_inputs = {
        "automobile_name": "EV-SUV",
        "stage_minutes": _default_stage_minutes(),
        "defect_rate": 0.03,
        "stations": _default_stations(),
        "hours_per_shift": 8,
        "shifts_per_day": 2,
        "target_units": 300,
        "scrap_allowance": 0.05,
    }

if "plan_result" not in st.session_state:
    st.session_state.plan_result = None

st.title("Automobile Manufacturing Planner")
st.caption(
    "Configure a vehicle model, assembly line, and production plan to estimate daily throughput."
)

st.sidebar.header("Deployment quick start")
st.sidebar.markdown(
    """
    **Run locally**
    ```bash
    pip install -r requirements.txt
    streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
    ```
    **RAG Feasibility API**
    ```bash
    uvicorn rag_app:app --host 0.0.0.0 --port 8000
    ```
    """
)

st.sidebar.info(
    "Use the sidebar commands when deploying to Streamlit Cloud or a container-based environment. "
    "Set OPENAI_API_KEY in the environment if you will also run the RAG service."
)

# Horizontal navigation tabs replace the single-column, vertical flow
plan_tab, results_tab, rag_tab = st.tabs([
    "Plan", "Results", "RAG Feasibility"
])

with plan_tab:
    st.markdown("### Configure the automobile and assembly line")
    with st.form("plan_form", border=True):
        cols = st.columns(3)
        with cols[0]:
            automobile_name = st.text_input(
                "Automobile name",
                value=st.session_state.plan_inputs["automobile_name"],
            )
            defect_rate = st.number_input(
                "Defect rate (0-1)",
                min_value=0.0,
                max_value=0.5,
                value=float(st.session_state.plan_inputs["defect_rate"]),
                step=0.01,
            )
            scrap_allowance = st.number_input(
                "Scrap allowance (0-1)",
                min_value=0.0,
                max_value=0.5,
                value=float(st.session_state.plan_inputs["scrap_allowance"]),
                step=0.01,
            )
            target_units = st.number_input(
                "Target units",
                min_value=1,
                value=int(st.session_state.plan_inputs["target_units"]),
                step=10,
            )
        with cols[1]:
            st.markdown("**Stage cycle time (minutes per unit)**")
            stage_minutes: Dict[str, int] = {}
            for stage in STAGES:
                stage_minutes[stage] = st.number_input(
                    f"{stage.title()} minutes",
                    min_value=1,
                    value=int(st.session_state.plan_inputs["stage_minutes"][stage]),
                    step=5,
                )
        with cols[2]:
            st.markdown("**Stations and shifts**")
            stations: Dict[str, int] = {}
            for stage in STAGES:
                stations[stage] = st.number_input(
                    f"{stage.title()} stations",
                    min_value=1,
                    value=int(st.session_state.plan_inputs["stations"][stage]),
                    step=1,
                )
            hours_per_shift = st.number_input(
                "Hours per shift",
                min_value=1,
                value=int(st.session_state.plan_inputs["hours_per_shift"]),
                step=1,
            )
            shifts_per_day = st.number_input(
                "Shifts per day",
                min_value=1,
                value=int(st.session_state.plan_inputs["shifts_per_day"]),
                step=1,
            )

        submitted = st.form_submit_button("Calculate capacity", use_container_width=True)

        if submitted:
            try:
                automobile = AutomobileModel(
                    name=automobile_name.strip() or "Automobile",
                    stage_minutes=stage_minutes,
                    defect_rate=defect_rate,
                )
                line = AssemblyLine(
                    name="Line A",
                    stations=stations,
                    hours_per_shift=hours_per_shift,
                    shifts_per_day=shifts_per_day,
                )
                plan = ProductionPlan(
                    line=line,
                    automobile=automobile,
                    target_units=target_units,
                    scrap_allowance=scrap_allowance,
                )
                st.session_state.plan_inputs = {
                    "automobile_name": automobile.name,
                    "stage_minutes": stage_minutes,
                    "defect_rate": defect_rate,
                    "stations": stations,
                    "hours_per_shift": hours_per_shift,
                    "shifts_per_day": shifts_per_day,
                    "target_units": target_units,
                    "scrap_allowance": scrap_allowance,
                }
                st.session_state.plan_result = {
                    "plan": plan,
                    "summary": plan.summary(),
                    "simulation": simulate_plan(plan),
                }
                st.success("Capacity calculated. View results in the Results tab.")
            except Exception as exc:  # pragma: no cover - UI feedback
                st.session_state.plan_result = None
                st.error(f"Unable to calculate capacity: {exc}")

with results_tab:
    st.markdown("### Capacity and component requirements")
    if not st.session_state.plan_result:
        st.info("Submit the form in the Plan tab to see throughput and requirements.")
    else:
        plan: ProductionPlan = st.session_state.plan_result["plan"]
        simulation = st.session_state.plan_result["simulation"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Theoretical capacity", f"{simulation['theoretical_daily_output']} units/day")
        col2.metric("Adjusted capacity", f"{simulation['adjusted_daily_output']} units/day")
        col3.metric("Target volume", f"{simulation['target_units']} units")
        loss_pct = 100 * (1 - (simulation["adjusted_daily_output"] / simulation["theoretical_daily_output"]))
        col4.metric("Loss factor", f"{loss_pct:.1f}%", help="Scrap and defect impact")

        st.markdown("#### Stage-level throughput")
        cap_rows = []
        for stage in STAGES:
            cap_rows.append(
                {
                    "Stage": stage.title(),
                    "Stations": plan.line.stations[stage],
                    "Minutes per unit": plan.automobile.stage_minutes[stage],
                    "Available minutes": plan.line.available_minutes[stage],
                    "Units/day": plan.stage_capacity(stage),
                }
            )
        cap_df = pd.DataFrame(cap_rows)
        st.dataframe(cap_df, use_container_width=True, hide_index=True)

        st.markdown("#### Component requirements")
        req_df = pd.DataFrame(
            [
                {"Stage": stage.title(), "Units required": simulation["component_requirements"][stage]}
                for stage in STAGES
            ]
        )
        st.dataframe(req_df, use_container_width=True, hide_index=True)

        st.markdown("#### Plan summary")
        st.code(st.session_state.plan_result["summary"], language="text")

        st.download_button(
            "Download simulation JSON",
            data=json.dumps(simulation, indent=2),
            file_name="production_simulation.json",
            mime="application/json",
            use_container_width=True,
        )

with rag_tab:
    st.markdown("### RAG feasibility service")
    st.write(
        "The repository also ships a FastAPI service (`rag_app.py`) that ingests supporting documents, "
        "captures a financial snapshot from Excel, and generates grounded feasibility study sections. "
        "Run it alongside this app if you need AI-generated reports with citations."
    )

    with st.expander("RAG service quickstart", expanded=False):
        st.markdown(
            """
            1. Install dependencies: `pip install -r requirements.txt`
            2. Export your API key: `export OPENAI_API_KEY=...`
            3. Start the API: `uvicorn rag_app:app --host 0.0.0.0 --port 8000`
            4. Call `/collect`, `/ingest`, then `/generate` to build a feasibility study.
            """
        )

st.caption("Automobile Manufacturing Platform — Streamlit front-end")
