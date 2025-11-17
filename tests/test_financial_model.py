import pandas as pd

from models.financial import (
    GlobalAssumptions,
    build_cash_flow_and_valuation,
    build_income_statement,
    create_default_product_assumptions,
    project_production_and_sales,
    run_model,
)


def test_default_run_model_shapes():
    results = run_model()

    sales_df = results["sales_by_product"]
    income_df = results["income_statement"]
    cash_flow_df = results["cash_flow"]
    valuation = results["valuation"]

    # 5-year horizon * 5 products
    assert len(sales_df) == 5 * len(create_default_product_assumptions())
    assert income_df.shape[0] == 5
    assert cash_flow_df.shape[0] == 5

    assert set(["Revenue", "EBITDA", "Net_Income"]).issubset(income_df.columns)
    assert set(["Free_Cash_Flow", "Operating_CF"]).issubset(cash_flow_df.columns)

    assert valuation["Enterprise_Value"] > 0
    assert valuation["Project_IRR"] > 0


def test_growth_and_margins_trend_positive():
    products = create_default_product_assumptions()
    global_assump = GlobalAssumptions()

    sales_df = project_production_and_sales(global_assump, products)
    income_df = build_income_statement(global_assump, sales_df)
    cash_flow_df, valuation = build_cash_flow_and_valuation(global_assump, income_df)

    # Revenue should grow over time because of units growth and price escalation.
    assert income_df.iloc[-1]["Revenue"] > income_df.iloc[0]["Revenue"]

    # Gross margins remain positive across products.
    assert (sales_df["Gross_Profit"] > 0).all()

    # Free cash flow should be positive after initial investment.
    assert (cash_flow_df["Free_Cash_Flow"] > 0).all()
    assert valuation["Enterprise_Value"] > valuation["NPV"]  # TV included


def test_overriding_assumptions_changes_outputs():
    products = create_default_product_assumptions()
    products["EV SUV"].price_growth = 0.10
    products["EV SUV"].units_growth = 0.20

    base_income_df = build_income_statement(GlobalAssumptions(), project_production_and_sales(GlobalAssumptions(), create_default_product_assumptions()))
    custom_income_df = build_income_statement(GlobalAssumptions(), project_production_and_sales(GlobalAssumptions(), products))

    assert custom_income_df.iloc[-1]["Revenue"] > base_income_df.iloc[-1]["Revenue"]
