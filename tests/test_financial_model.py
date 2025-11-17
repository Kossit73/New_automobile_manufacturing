import pandas as pd

from models.financial import (
    ModelConfig,
    MonteCarloEngine,
    Portfolio,
    Product,
    ProductConfig,
    Scenario,
    ScenarioEngine,
    ValuationEngine,
)


def _build_simple_portfolio() -> Portfolio:
    model_cfg = ModelConfig(first_year=2024, n_years=6, discount_rate=0.1)
    product_cfg = ProductConfig(
        name="Vaccine_Moonshine",
        stage="Market",
        success_prob=1.0,
        include_in_consolidation=True,
        preexisting_market=True,
        time_to_market=-1,
        patent_years=15,
        patent_revenue_target=10_000_000.0,
        post_patent_revenue_target=8_000_000.0,
        market_growth_patent=0.02,
        market_growth_post=0.01,
        cogs_patent=0.35,
        cogs_post=0.45,
        sales_marketing_pct=0.12,
        gna_pct=0.09,
        royalty_pct=0.0,
        rd_remaining_pre_launch=0.0,
        rd_annual_post_launch=250_000.0,
        capex_remaining_pre_launch=0.0,
        capex_annual_post_launch=150_000.0,
    )
    return Portfolio([Product(product_cfg, model_cfg)], model_cfg)


def test_valuation_engine_returns_expected_shapes_and_positive_value():
    portfolio = _build_simple_portfolio()
    result = ValuationEngine(portfolio).run()

    assert "fcff_after_wc" in result.consolidated.columns
    assert result.consolidated.shape[0] == portfolio.model_config.n_years
    assert result.dcf_table.shape[0] == portfolio.model_config.n_years
    assert result.rnpv > 0


def test_scenario_engine_applies_multipliers():
    portfolio = _build_simple_portfolio()
    base_val = ValuationEngine(portfolio).run().rnpv

    scenarios = [Scenario(name="Growth", revenue_multiplier=1.2, cost_multiplier=0.95)]
    scen_df = ScenarioEngine(portfolio).run_scenarios(scenarios)

    base_row = scen_df[scen_df["scenario"] == "Base"].iloc[0]
    growth_row = scen_df[scen_df["scenario"] == "Growth"].iloc[0]

    assert base_row["rnpv"] == base_val
    assert growth_row["rnpv"] > base_row["rnpv"]
    assert growth_row["ebitda_value"] > base_row["ebitda_value"]


def test_monte_carlo_reproducible_with_seed():
    portfolio = _build_simple_portfolio()
    mc = MonteCarloEngine(portfolio)

    sims_one = mc.simulate(n_sims=25, revenue_sigma=0.05, cost_sigma=0.03, random_seed=42)
    sims_two = mc.simulate(n_sims=25, revenue_sigma=0.05, cost_sigma=0.03, random_seed=42)

    pd.testing.assert_series_equal(sims_one, sims_two)
    assert sims_one.name == "rnpv_sim"
