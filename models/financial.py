"""Lightweight financial projection model for EV products."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
import pandas as pd

PRODUCTS = ["EV Bus", "EV Scooter", "EV SUV", "EV Hatchback", "EV Nano Car"]


# -----------------------------
# 1. Assumption data classes
# -----------------------------


@dataclass
class GlobalAssumptions:
    start_year: int = 2026
    projection_years: int = 5

    tax_rate: float = 0.25
    discount_rate: float = 0.12
    terminal_growth: float = 0.03

    initial_capex: float = 31_800_000
    maintenance_capex_pct_revenue: float = 0.03

    depreciation_years: int = 10
    working_capital_pct_revenue: float = 0.15

    fixed_opex_base: float = 7_500_000
    fixed_opex_growth: float = 0.05


@dataclass
class ProductAssumptions:
    name: str
    base_units: int
    units_growth: float
    base_price: float
    price_growth: float
    unit_cogs: float
    cogs_inflation: float


# -------------------------------------------
# 2. Helpers to create default assumptions
# -------------------------------------------


def create_default_product_assumptions() -> Dict[str, ProductAssumptions]:
    """Return a default product portfolio aligned with the Excel model layout."""

    defaults = {
        "EV Bus": ProductAssumptions(
            name="EV Bus",
            base_units=200,
            units_growth=0.10,
            base_price=180_000,
            price_growth=0.02,
            unit_cogs=140_000,
            cogs_inflation=0.02,
        ),
        "EV Scooter": ProductAssumptions(
            name="EV Scooter",
            base_units=3_000,
            units_growth=0.15,
            base_price=1_500,
            price_growth=0.02,
            unit_cogs=1_000,
            cogs_inflation=0.02,
        ),
        "EV SUV": ProductAssumptions(
            name="EV SUV",
            base_units=800,
            units_growth=0.12,
            base_price=45_000,
            price_growth=0.02,
            unit_cogs=32_000,
            cogs_inflation=0.02,
        ),
        "EV Hatchback": ProductAssumptions(
            name="EV Hatchback",
            base_units=1_000,
            units_growth=0.12,
            base_price=25_000,
            price_growth=0.02,
            unit_cogs=18_000,
            cogs_inflation=0.02,
        ),
        "EV Nano Car": ProductAssumptions(
            name="EV Nano Car",
            base_units=1_500,
            units_growth=0.15,
            base_price=14_000,
            price_growth=0.02,
            unit_cogs=9_500,
            cogs_inflation=0.02,
        ),
    }
    return defaults


# -------------------------------------------
# 3. Production & sales projection
# -------------------------------------------


def project_production_and_sales(
    global_assump: GlobalAssumptions, products: Dict[str, ProductAssumptions]
) -> pd.DataFrame:
    """Project units, pricing, and gross profit per product per year."""

    rows: List[dict] = []
    years = [global_assump.start_year + i for i in range(global_assump.projection_years)]

    for i, year in enumerate(years):
        for p in products.values():
            units = p.base_units * ((1 + p.units_growth) ** i)
            price = p.base_price * ((1 + p.price_growth) ** i)
            unit_cogs = p.unit_cogs * ((1 + p.cogs_inflation) ** i)

            revenue = units * price
            cogs = units * unit_cogs
            gross_profit = revenue - cogs

            rows.append(
                {
                    "Year": year,
                    "Product": p.name,
                    "Units": units,
                    "Price": price,
                    "Revenue": revenue,
                    "Unit_COGS": unit_cogs,
                    "COGS": cogs,
                    "Gross_Profit": gross_profit,
                    "Gross_Margin_%": gross_profit / revenue if revenue else 0.0,
                }
            )

    return pd.DataFrame(rows)


# -------------------------------------------
# 4. Income statement
# -------------------------------------------


def build_income_statement(global_assump: GlobalAssumptions, sales_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sales into a simple income statement by year."""

    revenue_by_year = sales_df.groupby("Year")["Revenue"].sum()
    cogs_by_year = sales_df.groupby("Year")["COGS"].sum()

    years = revenue_by_year.index.tolist()
    rows = []

    annual_depr = global_assump.initial_capex / global_assump.depreciation_years
    fixed_opex = global_assump.fixed_opex_base

    for i, year in enumerate(years):
        revenue = revenue_by_year.loc[year]
        cogs = cogs_by_year.loc[year]
        gross_profit = revenue - cogs

        if i > 0:
            fixed_opex *= 1 + global_assump.fixed_opex_growth

        opex = fixed_opex

        ebitda = gross_profit - opex
        depreciation = annual_depr
        ebit = ebitda - depreciation

        interest = 0.0
        ebt = ebit - interest
        tax = max(0.0, ebt * global_assump.tax_rate)
        net_income = ebt - tax

        rows.append(
            {
                "Year": year,
                "Revenue": revenue,
                "COGS": cogs,
                "Gross_Profit": gross_profit,
                "Opex": opex,
                "EBITDA": ebitda,
                "Depreciation": depreciation,
                "EBIT": ebit,
                "Interest": interest,
                "EBT": ebt,
                "Tax": tax,
                "Net_Income": net_income,
                "EBITDA_Margin_%": ebitda / revenue if revenue else 0.0,
                "Net_Margin_%": net_income / revenue if revenue else 0.0,
            }
        )

    return pd.DataFrame(rows)


# -------------------------------------------
# 5. Cash flow & DCF valuation
# -------------------------------------------


def build_cash_flow_and_valuation(
    global_assump: GlobalAssumptions, income_df: pd.DataFrame
) -> tuple[pd.DataFrame, dict]:
    """Calculate simplified free cash flow series and DCF valuation."""

    years = income_df["Year"].tolist()
    rows = []

    prev_wc = 0.0
    cash_flows = [-global_assump.initial_capex]

    for i, year in enumerate(years):
        revenue = income_df.loc[i, "Revenue"]
        ebit = income_df.loc[i, "EBIT"]

        nopat = ebit * (1 - global_assump.tax_rate)
        depreciation = income_df.loc[i, "Depreciation"]

        wc = global_assump.working_capital_pct_revenue * revenue
        change_wc = wc - prev_wc
        prev_wc = wc

        maintenance_capex = global_assump.maintenance_capex_pct_revenue * revenue

        operating_cf = nopat + depreciation - change_wc
        fcf = operating_cf - maintenance_capex

        cash_flows.append(fcf)

        rows.append(
            {
                "Year": year,
                "Revenue": revenue,
                "NOPAT": nopat,
                "Depreciation": depreciation,
                "Change_in_WC": change_wc,
                "Maintenance_CAPEX": maintenance_capex,
                "Operating_CF": operating_cf,
                "Free_Cash_Flow": fcf,
            }
        )

    cf_df = pd.DataFrame(rows)

    r = global_assump.discount_rate
    g = global_assump.terminal_growth
    n = len(years)

    discounted_fcfs = [cf_df.loc[i, "Free_Cash_Flow"] / ((1 + r) ** (i + 1)) for i in range(n)]

    last_fcf = cf_df.loc[n - 1, "Free_Cash_Flow"]
    terminal_value = last_fcf * (1 + g) / (r - g)
    pv_terminal = terminal_value / ((1 + r) ** n)

    enterprise_value = sum(discounted_fcfs) + pv_terminal

    npv = enterprise_value - global_assump.initial_capex
    irr = float(np.irr(cash_flows))

    valuation = {
        "Enterprise_Value": enterprise_value,
        "NPV": npv,
        "Project_IRR": irr,
        "Terminal_Value": terminal_value,
    }

    return cf_df, valuation


# -------------------------------------------
# 6. Convenience runner
# -------------------------------------------


def run_model(
    global_assump: GlobalAssumptions | None = None,
    products: Dict[str, ProductAssumptions] | None = None,
) -> Dict[str, object]:
    """High-level helper to run projections and return key tables."""

    if global_assump is None:
        global_assump = GlobalAssumptions()
    if products is None:
        products = create_default_product_assumptions()

    sales_df = project_production_and_sales(global_assump, products)
    income_df = build_income_statement(global_assump, sales_df)
    cashflow_df, valuation = build_cash_flow_and_valuation(global_assump, income_df)

    return {
        "sales_by_product": sales_df,
        "income_statement": income_df,
        "cash_flow": cashflow_df,
        "valuation": valuation,
    }


# -------------------------------------------
# 7. Simple CLI demo
# -------------------------------------------


if __name__ == "__main__":  # pragma: no cover - manual demo
    results = run_model()

    print("\n--- SALES BY PRODUCT (first 10 rows) ---")
    print(results["sales_by_product"].head(10).round(2))

    print("\n--- INCOME STATEMENT ---")
    print(results["income_statement"].round(2))

    print("\n--- CASH FLOW ---")
    print(results["cash_flow"].round(2))

    print("\n--- VALUATION ---")
    for k, v in results["valuation"].items():
        print(f"{k}: {v:,.2f}")
