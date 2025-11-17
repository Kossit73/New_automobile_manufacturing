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

## Financial projection quickstart

The repository now ships with a lightweight multi-product financial model in `models/financial.py`. Use the defaults to
generate sales, income statement, cash flow, and valuation outputs:

```python
from models.financial import run_model

results = run_model()
print(results["income_statement"].head())
print(results["cash_flow"].head())
print(results["valuation"])
```

Pass in custom `GlobalAssumptions` and per-product `ProductAssumptions` to mirror your Excel workbook inputs. The helper
returns Pandas DataFrames for sales, income statement, and cash flow along with a valuation dictionary containing
enterprise value, NPV, IRR, and terminal value.

### Streamlit planner

You can explore the same production model through an interactive Streamlit app:

```bash
python -m pip install -r requirements.txt
streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
```

The app lets you configure stage cycle times, station counts, shifts, and scrap/defect assumptions, then reviews stage-level
throughput and component requirements. Use the sidebar quickstart inside the app for deployment tips.

## RAG Feasibility Study Generator

The repository also includes a standalone FastAPI service (`rag_app.py`) that ingests project files, captures a financial snapshot from Excel, and drafts a grounded feasibility study using retrieval augmented generation (RAG).

### Endpoints

- `POST /collect`: Persist the financial snapshot and optional cell map extracted from your Excel workbook.
- `POST /ingest`: Stream upload PDFs, DOCX, PPTX, TXT, CSV, or XLSX files. The service chunks the content, builds a FAISS vector index, and backfills a financial snapshot when possible.
- `POST /generate`: Compose feasibility study sections using the vector index and financial snapshot, returning JSON/Markdown outputs and an optional NPV curve chart.

### Run locally

```bash
python -m pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
uvicorn rag_app:app --host 0.0.0.0 --port 8000
```

Store uploaded and parsed data under `./projects/<project_id>/` by default. The `LLM_MODEL`, `EMBED_MODEL`, and related settings can be adjusted through environment variables at launch.

## Development

Install the test dependencies and run the suite with `pytest`:

```bash
python -m pip install -r requirements.txt
python -m pytest
```

## Financial Model Overview

For a deeper description of the planned financial workflows—including labor, CAPEX, reporting schedules, and the end-to-end forecasting pipeline—see [docs/financial_model_overview.md](docs/financial_model_overview.md).
