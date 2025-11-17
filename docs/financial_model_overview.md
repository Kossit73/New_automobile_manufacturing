# Financial Model Overview

This document outlines the expected behaviors, schedules, and data flows for the financial model that powers the automobile manufacturing platform. It captures the reporting requirements across modules and provides a concise walkthrough of the end-to-end computation pipeline.

## Module Outputs

### Labor Management
- **Labor Position Summary**: Tabular overview of every configured role with salary, benefit, and classification details, rendered directly on the Labor Management tab.
- **5-Year Labor Cost Schedule**: Projection of direct/indirect headcount and labor costs across the configured horizon; always displayed even if no positions exist yet.

### CAPEX Management
- **CAPEX Project Register**: Listing of all capital projects, showing configured attributes such as amount, start year, and salvage value once projects are added.
- **CAPEX Spend Schedule**: Year-by-year capital outlay based on each project’s spend curve across the projection window.
- **Depreciation Schedule**: Straight-line depreciation detail derived from project inputs, aligned with the model horizon.

### Financial Model → Results
- **Income Statement Schedule**: Revenue, gross profit, operating income, and net profit projections for every modeled year.
- **Cash Flow Schedule**: Operating, investing, and financing cash movements summarized annually.
- **Balance Sheet Schedule**: Assets, liabilities, and equity balances synthesized from the working-capital and CAPEX drivers.
- **Debt Amortization Schedule**: Aggregated draws, interest, and principal repayments for all configured debt instruments.
- **Labor Cost Schedule**: Financial-model view of labor expenses that mirrors the management tab output.

### Reports
- **Financial Forecast Schedule**: Consolidated revenue, cost, profit, and cash projections intended for export/shareable reporting.
- **Labor Cost Schedule**: Reporting duplicate of the labor schedule to maintain parity across deliverables.
- **CAPEX Spend Schedule**: Reporting copy of annual CAPEX outlays for downstream consumers.
- **Debt Amortization Schedule**: Reporting copy of the debt table for financial packages.

## How the Model Works

1. **Configuration and Input Normalization**  
   A `CompanyConfig` dataclass centralizes assumptions like the projection horizon, production capacity, marketing plan, financing structure, and working-capital drivers. It normalizes supplied inputs (capacity curve, product portfolio, marketing plan, and debt instruments), falling back to defaults and enforcing guardrails where needed. Capacity utilization gaps are filled by `_normalize_capacity_utilization`, which carries forward the most recent value and clamps utilization between 0 % and 100 %. Marketing campaigns are normalized and expanded into an annual budget so changes persist across the whole forecast window. Debt inputs are converted into `DebtInstrument` objects with cleaned draw schedules, ensuring the amortization profile reflects interest-only periods and multi-tranche funding.

2. **Production, Pricing, and Revenue**  
   `calculate_production_forecast` turns normalized capacity utilization into total units, allocates output across the configured product mix, applies price escalation, and produces per-product revenue for each projection year. This generates the core revenue stream consumed by later statements.

3. **Cost Structure and Operating Expenses**  
   `calculate_cogs` splits cost of goods sold into variable and fixed components by product. Variable costs escalate with inflation and scale with utilization, while fixed manufacturing overhead adjusts using a utilization-sensitivity factor via `_fixed_production_cost`. Operating expenses come from either baseline payroll and marketing assumptions or the live labor manager; when a labor schedule is present, `calculate_opex_with_labor_manager` replaces payroll with aggregated labor costs and also exposes detailed headcount metrics for reporting.

4. **Working Capital and Operating Cash Flow**  
   `calculate_working_capital_positions` derives receivables, inventory, payables, and accrued expenses from revenue, COGS, and operating expenses using turnover-day drivers. It tracks both absolute balances and year-over-year changes, feeding into operating cash flow calculations and the balance sheet. The operating cash flow (`cfo`) adds back depreciation and subtracts working-capital changes to translate earnings into cash.

5. **Financing, CAPEX, and Cash Movement**  
   `build_debt_schedule` aggregates multiple instruments’ draws, interest, principal, and ending balances, respecting draw schedules and interest-only periods before amortization begins. Investment cash flow (`cfi`) pulls year-by-year spend from the CAPEX manager when available (or defaults to lump-sum legacy behavior), while financing cash flow (`cff`) incorporates equity injections, new debt draws, and scheduled debt service. `calculate_cash_flow` then rolls these components into a cumulative cash balance across the horizon.

6. **Financial Statements and Valuation**  
   `calculate_income_statement` produces EBITDA, EBIT, taxes, and net profit by combining revenue, COGS, operating expenses, and depreciation sourced from the CAPEX manager or fallback assumptions. `calculate_dcf` converts EBIT into free cash flow, discounts each year, and computes a terminal value to arrive at enterprise value. `calculate_balance_sheet` builds assets, liabilities, and equity using cash balances, working-capital accounts, CAPEX-derived fixed assets, and outstanding debt, returning a complete balance sheet with a balance check.

7. **End-to-End Orchestration and Outputs**  
   `run_financial_model` orchestrates every module: it computes production, costs, profitability, cash flows, capital structure, and balance sheet results, returning an expansive dictionary that downstream views (dashboards, reports, exports) consume. Helper functions package these dictionaries into income statement, cash flow, and balance sheet tables for presentation layers.

These notes should help onboard contributors and clarify how upstream configuration drives downstream schedules and reports.
