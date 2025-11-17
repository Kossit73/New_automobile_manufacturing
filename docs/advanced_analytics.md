# Advanced Analytics Playbook

This guide summarizes the advanced analytics now available for sensitivity, stress testing,
forecasting, optimization, and machine-learning driven diagnostics. All helpers are exposed
from `models.analytics` via the top-level `models` package.

## Risk & Uncertainty
- **Sensitivity analysis:** `SensitivityAnalyzer.run(driver, deltas, apply_fn)` perturbs a single
  driver (e.g., milk price ±10%) and returns rNPV deltas for tornado/spider charts.
- **Scenario stress testing:** `StressTester.run([...Scenario(...)])` layers severe-but-plausible
  shocks such as drought, disease, or commodity spikes using the existing `ScenarioEngine`.
- **Monte Carlo simulation:** `simulate_valuation_distribution(portfolio, n_sims)` returns rNPV
  samples; summarize with `probabilistic_valuation` plus `value_at_risk` / `conditional_value_at_risk`.
- **Copulas & VaR:** `gaussian_copula_simulation` produces correlated shocks; `value_at_risk`
  and `conditional_value_at_risk` surface loss tails.

## Forecasting & Seasonality
- **Trend/seasonality decomposition:** `decompose_trend_seasonality(series)` uses statsmodels when
  available (falls back to rolling means) to isolate trend vs. seasonal patterns.
- **Time-series forecasting:** `forecast_time_series(engine, series, model="arima"|"prophet"|"lstm")`
  routes through the `ForecastEngine` for ARIMA, Prophet, or LSTM projections.

## Profitability Drivers
- **Segmentation:** `segment_margin_table(df, ["customer", "product"])` aggregates revenue, cost,
  and margins to spotlight high- or low-performing channels.
- **What-if analysis:** `what_if(base_portfolio, {"High feed cost": fn})` compares multiple
  adjustments against the base case.
- **Goal seek:** `goal_seek(func, target, low, high)` back-solves for the input needed to hit a
  liquidity or profitability threshold.
- **Real options:** `black_scholes_call` approximates the value of defer/expand/abandon options.

## Visual Inputs
- **Tornado & spider prep:** `tornado_chart_data(base_value, impacts)` and `spider_chart_data`
  shape data for visualizing which drivers matter most.

## Machine Learning & Optimization
- **Regression & classification:** `linear_regression`, `logistic_classification`, and
  `ml_multiples_regression` provide lightweight OLS, logistic, and ridge-style estimators for
  revenue/cost prediction, churn/credit scoring, or multiples benchmarking.
- **Portfolio & resource allocation:** `mean_variance_optimize` computes classic
  Markowitz weights; `linear_resource_allocation` offers a greedy knapsack for capacity or
  budget constraints.
- **Segmentation clustering:** `cluster_comparables` gives k-means style grouping for peer
  benchmarking.

## ESG, Macro, and Market Intelligence
- **Macro linking:** `apply_macro_link` injects inflation or GDP effects into consolidated
  revenue and cost views.
- **ESG costs:** `esg_cost_impact` adds carbon-price driven costs to EBIT.
- **Market intelligence blending:** `market_intelligence_blend` scales forecasts with sentiment
  or third-party industry outlooks.

## Usage snippet
```python
from models import (
    ModelConfig, ProductConfig, Product, Portfolio, ValuationEngine,
    SensitivityAnalyzer, StressTester, Scenario, simulate_valuation_distribution,
)

# build a basic portfolio
cfg = ModelConfig()
prod = Product(ProductConfig(name="Dairy", stage="Scale", success_prob=0.9, patent_revenue_target=5_000_000), cfg)
portfolio = Portfolio([prod], cfg)

# sensitivity to milk price +/- 20%
sa = SensitivityAnalyzer(portfolio)
result = sa.run("milk_price", [-0.2, 0.0, 0.2], apply_fn=lambda p, d: p)

# drought & disease stress test
stress = StressTester(portfolio)
scen_df = stress.run([
    Scenario(name="Drought", revenue_multiplier=0.8, cost_multiplier=1.1, discount_rate_shift=0.02),
    Scenario(name="Disease", revenue_multiplier=0.7, cost_multiplier=1.15, discount_rate_shift=0.03),
])

# Monte Carlo distribution
rnpv_sims = simulate_valuation_distribution(portfolio, n_sims=200)
```
