"""Advanced analytics helpers for sensitivity, stress testing, forecasting, and optimization.

This module layers analytical tooling on top of the portfolio valuation engine to support
stress testing, sensitivity analysis, risk metrics, optimization, and machine-learning
driven diagnostics. All functions are designed to be dependency-light and degrade
gracefully when optional libraries are missing.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from .financial import (
    ForecastEngine,
    MonteCarloEngine,
    Portfolio,
    Scenario,
    ScenarioEngine,
    ValuationEngine,
)


# ==============================
# Sensitivity & scenario helpers
# ==============================


@dataclass
class SensitivityResult:
    driver: str
    deltas: Sequence[float]
    valuations: pd.DataFrame


class SensitivityAnalyzer:
    """Run univariate sensitivities by perturbing a driver and re-valuing the portfolio."""

    def __init__(self, base_portfolio: Portfolio):
        self.base_portfolio = base_portfolio
        self.base_valuation = ValuationEngine(base_portfolio).run()

    def run(
        self,
        driver: str,
        deltas: Iterable[float],
        apply_fn: Callable[[Portfolio, float], Portfolio],
    ) -> SensitivityResult:
        rows: List[Dict[str, float]] = []
        for delta in deltas:
            port = apply_fn(self.base_portfolio, delta)
            val = ValuationEngine(port).run()
            rows.append(
                {
                    "delta": delta,
                    "rnpv": val.rnpv,
                    "change": val.rnpv - self.base_valuation.rnpv,
                    "pct_change": (val.rnpv - self.base_valuation.rnpv) / self.base_valuation.rnpv
                    if self.base_valuation.rnpv
                    else np.nan,
                }
            )
        df = pd.DataFrame(rows)
        return SensitivityResult(driver=driver, deltas=list(deltas), valuations=df)


class StressTester:
    """Apply severe but plausible shocks using the ScenarioEngine."""

    def __init__(self, base_portfolio: Portfolio):
        self.base_portfolio = base_portfolio

    def run(self, scenarios: List[Scenario], ebitda_year_offset: int = 0) -> pd.DataFrame:
        engine = ScenarioEngine(self.base_portfolio)
        return engine.run_scenarios(scenarios, ebitda_year_offset=ebitda_year_offset)


# =======================================
# Time series decomposition & forecasting
# =======================================


def decompose_trend_seasonality(series: pd.Series, period: Optional[int] = None) -> Dict[str, pd.Series]:
    """Return trend/seasonal/residual decomposition with a lightweight fallback."""
    try:
        from statsmodels.tsa.seasonal import seasonal_decompose  # type: ignore

        result = seasonal_decompose(series, model="additive", period=period or max(2, int(len(series) / 4)))
        return {"trend": result.trend, "seasonal": result.seasonal, "resid": result.resid}
    except Exception:
        window = period or max(2, int(len(series) / 4))
        trend = series.rolling(window=window, min_periods=1, center=True).mean()
        seasonal = series - trend
        resid = seasonal - seasonal.mean()
        return {"trend": trend, "seasonal": seasonal, "resid": resid}


def forecast_time_series(
    forecast_engine: ForecastEngine,
    series: pd.Series,
    model: str = "arima",
    steps: Optional[int] = None,
) -> pd.Series:
    """Forecast using ARIMA/Prophet/LSTM based on the model string."""
    model_lower = model.lower()
    if steps is None:
        steps = forecast_engine.model_config.n_years

    if model_lower == "arima":
        return forecast_engine.forecast_arima(series, steps=steps)
    if model_lower == "prophet":
        df = pd.DataFrame({"ds": series.index, "y": series.values})
        forecast = forecast_engine.forecast_prophet(df, periods=steps)
        return forecast.set_index("ds")["yhat"]
    if model_lower == "lstm":
        preds = forecast_engine.forecast_lstm(series, steps_ahead=steps)
        idx = pd.RangeIndex(start=0, stop=steps, step=1)
        return pd.Series(preds, index=idx, name="lstm_forecast")
    raise ValueError("model must be arima, prophet, or lstm")


# ==================================
# Segmentation & margin diagnostics
# ==================================


def segment_margin_table(data: pd.DataFrame, segment_cols: Sequence[str]) -> pd.DataFrame:
    """Aggregate revenue/cost/margin by customer or product segment."""
    required = {"revenue", "cost"}
    if not required.issubset(data.columns):
        raise ValueError("DataFrame must include revenue and cost columns")
    grouped = data.groupby(list(segment_cols)).agg({"revenue": "sum", "cost": "sum"}).reset_index()
    grouped["gross_profit"] = grouped["revenue"] - grouped["cost"]
    grouped["gross_margin_pct"] = grouped["gross_profit"] / grouped["revenue"]
    return grouped.sort_values(by="gross_margin_pct", ascending=False)


# ======================
# Monte Carlo & what-if
# ======================


def simulate_valuation_distribution(portfolio: Portfolio, n_sims: int = 500) -> pd.Series:
    """Wrapper around MonteCarloEngine that returns rNPV distribution."""
    mc = MonteCarloEngine(portfolio)
    return mc.simulate(n_sims=n_sims)


def what_if(
    base_portfolio: Portfolio,
    adjustments: Dict[str, Callable[[Portfolio], Portfolio]],
) -> pd.DataFrame:
    """Evaluate multiple what-if cases defined by adjustment callables."""
    base_val = ValuationEngine(base_portfolio).run()
    rows = [{"case": "Base", "rnpv": base_val.rnpv}]
    for name, fn in adjustments.items():
        port = fn(base_portfolio)
        val = ValuationEngine(port).run()
        rows.append({"case": name, "rnpv": val.rnpv, "delta": val.rnpv - base_val.rnpv})
    return pd.DataFrame(rows)


# ==================
# Goal seek routines
# ==================


def goal_seek(
    func: Callable[[float], float],
    target: float,
    low: float,
    high: float,
    tol: float = 1e-4,
    max_iter: int = 100,
) -> float:
    """Solve for input x such that func(x) ~= target using bisection."""
    lo, hi = low, high
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        val = func(mid)
        if abs(val - target) <= tol:
            return mid
        if val < target:
            lo = mid
        else:
            hi = mid
    return mid


# ==============================
# Tornado & spider chart inputs
# ==============================


def tornado_chart_data(base_value: float, impacts: Dict[str, Tuple[float, float]]) -> pd.DataFrame:
    """Return low/high impact ranges for tornado plotting."""
    rows = []
    for driver, (low, high) in impacts.items():
        rows.append(
            {
                "driver": driver,
                "low": low,
                "high": high,
                "impact_low": low - base_value,
                "impact_high": high - base_value,
            }
        )
    df = pd.DataFrame(rows)
    return df.sort_values(by=["impact_high"], ascending=False)


def spider_chart_data(categories: Sequence[str], values: Sequence[float]) -> pd.DataFrame:
    """Package data for spider/radar charts."""
    return pd.DataFrame({"category": list(categories), "value": list(values)})


# =====================
# Regression utilities
# =====================


def linear_regression(X: pd.DataFrame, y: pd.Series) -> Tuple[np.ndarray, float]:
    """Ordinary least squares via normal equation; returns coefficients and R^2."""
    X_ = np.column_stack([np.ones(len(X)), X.values])
    beta, *_ = np.linalg.lstsq(X_, y.values, rcond=None)
    y_hat = X_ @ beta
    ss_tot = np.sum((y.values - y.mean()) ** 2)
    ss_res = np.sum((y.values - y_hat) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot else np.nan
    return beta, r2


def logistic_classification(X: pd.DataFrame, y: pd.Series, lr: float = 0.1, epochs: int = 200) -> np.ndarray:
    """Simple logistic regression classifier using gradient descent."""
    X_ = np.column_stack([np.ones(len(X)), X.values])
    y_arr = y.values.reshape(-1, 1)
    w = np.zeros((X_.shape[1], 1))

    def sigmoid(z):
        return 1 / (1 + np.exp(-z))

    for _ in range(epochs):
        z = X_ @ w
        preds = sigmoid(z)
        grad = X_.T @ (preds - y_arr) / len(X_)
        w -= lr * grad
    return w.flatten()


# ===========================
# Optimization & allocation
# ===========================


def mean_variance_optimize(returns: pd.DataFrame, target_return: Optional[float] = None) -> pd.Series:
    """Closed-form mean-variance optimizer (no short constraints)."""
    mu = returns.mean()
    cov = returns.cov()
    ones = np.ones(len(mu))
    inv_cov = np.linalg.pinv(cov.values)
    A = ones @ inv_cov @ ones
    B = ones @ inv_cov @ mu.values
    C = mu.values @ inv_cov @ mu.values

    if target_return is None:
        weights = (inv_cov @ ones) / A
    else:
        lam = (C - target_return * B) / (A * C - B**2)
        gamma = (target_return * A - B) / (A * C - B**2)
        weights = lam * (inv_cov @ mu.values) + gamma * (inv_cov @ ones)
    return pd.Series(weights, index=mu.index)


def linear_resource_allocation(costs: np.ndarray, capacity: float, values: np.ndarray) -> np.ndarray:
    """Greedy knapsack-style allocation to maximize value under a capacity constraint."""
    ratio = values / costs
    order = np.argsort(ratio)[::-1]
    remaining = capacity
    alloc = np.zeros_like(costs)
    for idx in order:
        take = min(remaining, costs[idx])
        alloc[idx] = take
        remaining -= take
        if remaining <= 0:
            break
    return alloc


# ==================
# Real options & VaR
# ==================


def black_scholes_call(spot: float, strike: float, vol: float, time: float, rate: float) -> float:
    """Black–Scholes call option value for real-options style analysis."""
    if spot <= 0 or strike <= 0 or vol <= 0 or time <= 0:
        return 0.0
    d1 = (math.log(spot / strike) + (rate + 0.5 * vol**2) * time) / (vol * math.sqrt(time))
    d2 = d1 - vol * math.sqrt(time)
    from math import erf

    def norm_cdf(x: float) -> float:
        return 0.5 * (1 + erf(x / math.sqrt(2)))

    return spot * norm_cdf(d1) - strike * math.exp(-rate * time) * norm_cdf(d2)


def value_at_risk(data: pd.Series, alpha: float = 0.95) -> float:
    return float(data.quantile(1 - alpha))


def conditional_value_at_risk(data: pd.Series, alpha: float = 0.95) -> float:
    var = value_at_risk(data, alpha=alpha)
    tail = data[data <= var]
    return float(tail.mean()) if len(tail) else var


# ===================
# Copulas & shocks
# ===================


def gaussian_copula_simulation(corr: np.ndarray, marginals: List[Callable[[np.ndarray], np.ndarray]], n: int) -> np.ndarray:
    """Generate correlated samples using a Gaussian copula."""
    z = np.random.multivariate_normal(mean=np.zeros(len(corr)), cov=corr, size=n)
    from math import erf

    u = 0.5 * (1 + erf(z / math.sqrt(2)))  # convert to uniform via normal CDF
    samples = [m(u[:, i]) for i, m in enumerate(marginals)]
    return np.column_stack(samples)


def apply_macro_link(cons_df: pd.DataFrame, inflation: float = 0.02, gdp_growth: float = 0.0) -> pd.DataFrame:
    """Link macro factors into consolidated revenue and costs."""
    adj = cons_df.copy()
    adj["revenue"] *= (1 + inflation + gdp_growth)
    adj["cogs"] *= (1 + inflation)
    adj["sales_marketing"] *= (1 + gdp_growth)
    return adj


def esg_cost_impact(cons_df: pd.DataFrame, carbon_price: float, emission_factor: float) -> pd.DataFrame:
    """Apply ESG costs via carbon pricing and emission factors."""
    adj = cons_df.copy()
    adj["esg_cost"] = carbon_price * emission_factor
    adj["ebit"] = adj.get("ebit", 0) - adj["esg_cost"]
    return adj


def market_intelligence_blend(base_forecast: pd.Series, sentiment_score: float, industry_growth: float) -> pd.Series:
    """Blend sentiment and industry outlook into a revenue forecast path."""
    sentiment_factor = 1 + 0.1 * sentiment_score
    growth_factor = 1 + industry_growth
    return base_forecast * sentiment_factor * growth_factor


def probabilistic_valuation(mc_distribution: pd.Series) -> Dict[str, float]:
    """Summarize valuation distribution into percentiles."""
    return {
        "p05": float(mc_distribution.quantile(0.05)),
        "p50": float(mc_distribution.quantile(0.50)),
        "p95": float(mc_distribution.quantile(0.95)),
        "mean": float(mc_distribution.mean()),
    }


def cluster_comparables(features: pd.DataFrame, k: int = 3, max_iter: int = 50) -> Tuple[np.ndarray, np.ndarray]:
    """Lightweight k-means for comparative valuation benchmarking."""
    rng = np.random.default_rng(42)
    centroids = features.sample(n=k, random_state=42).values
    labels = np.zeros(len(features), dtype=int)
    for _ in range(max_iter):
        for i, row in enumerate(features.values):
            dists = np.linalg.norm(row - centroids, axis=1)
            labels[i] = int(np.argmin(dists))
        new_centroids = np.array([
            features.values[labels == j].mean(axis=0) if np.any(labels == j) else centroids[j]
            for j in range(k)
        ])
        if np.allclose(new_centroids, centroids):
            break
        centroids = new_centroids
    return labels, centroids


def ml_multiples_regression(features: pd.DataFrame, multiples: pd.Series, l2: float = 0.0) -> Tuple[np.ndarray, float]:
    """Predict trading/transaction multiples via ridge regression closed-form."""
    X_ = np.column_stack([np.ones(len(features)), features.values])
    y = multiples.values.reshape(-1, 1)
    reg = l2 * np.eye(X_.shape[1])
    beta = np.linalg.pinv(X_.T @ X_ + reg) @ X_.T @ y
    preds = (X_ @ beta).flatten()
    ss_tot = np.sum((multiples - multiples.mean()) ** 2)
    ss_res = np.sum((multiples - preds) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot else np.nan
    return beta.flatten(), float(r2)


__all__ = [
    "SensitivityAnalyzer",
    "SensitivityResult",
    "StressTester",
    "decompose_trend_seasonality",
    "forecast_time_series",
    "segment_margin_table",
    "simulate_valuation_distribution",
    "what_if",
    "goal_seek",
    "tornado_chart_data",
    "spider_chart_data",
    "linear_regression",
    "logistic_classification",
    "mean_variance_optimize",
    "linear_resource_allocation",
    "black_scholes_call",
    "value_at_risk",
    "conditional_value_at_risk",
    "gaussian_copula_simulation",
    "apply_macro_link",
    "esg_cost_impact",
    "market_intelligence_blend",
    "probabilistic_valuation",
    "cluster_comparables",
    "ml_multiples_regression",
]
