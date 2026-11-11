from __future__ import annotations

import math

PERIODS_PER_YEAR = {"D1": 252, "H4": 1512, "H1": 6048, "M15": 24192}


def _sma(values: list[float], period: int) -> list[float | None]:
    output: list[float | None] = [None] * len(values)
    rolling = 0.0
    for index, value in enumerate(values):
        rolling += value
        if index >= period:
            rolling -= values[index - period]
        if index >= period - 1:
            output[index] = rolling / period
    return output


def _summarize(returns: list[float], periods_per_year: int) -> dict:
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    gains = losses = 0.0
    positive_periods = 0
    variance_values = []
    for result in returns:
        equity *= 1 + result
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak - equity) / peak if peak else 0)
        if result > 0:
            gains += result
            positive_periods += 1
        elif result < 0:
            losses += -result
        variance_values.append(result)
    mean = sum(variance_values) / len(variance_values) if variance_values else 0
    variance = sum((value - mean) ** 2 for value in variance_values) / max(1, len(variance_values) - 1)
    volatility = math.sqrt(variance)
    return {
        "total_return_pct": round((equity - 1) * 100, 3),
        "max_drawdown_pct": round(max_drawdown * 100, 3),
        "annualized_sharpe": round(mean / volatility * math.sqrt(periods_per_year), 3) if volatility else None,
        "positive_period_pct": round(positive_periods / len(returns) * 100, 2) if returns else None,
        "profit_factor": round(gains / losses, 3) if losses else (None if gains == 0 else "inf"),
        "observations": len(returns),
    }


def run_moving_average_backtest(bars: list[dict], pip_size: float, timeframe: str,
                                fast_period: int = 10, slow_period: int = 30,
                                spread_pips: float = 1.0) -> dict:
    """Fixed-rule SMA crossover, next-bar returns, one-way spread cost, chronological OOS split."""
    if fast_period < 2 or slow_period <= fast_period:
        raise ValueError("slow_period must be greater than fast_period >= 2")
    if not math.isfinite(spread_pips) or spread_pips < 0 or spread_pips > 50:
        raise ValueError("spread_pips must be between 0 and 50")
    closes = [float(bar["close"]) for bar in bars]
    if len(closes) <= slow_period + 5 or any(not math.isfinite(value) or value <= 0 for value in closes):
        raise ValueError("insufficient or invalid close prices")

    fast = _sma(closes, fast_period)
    slow = _sma(closes, slow_period)
    signals = [0] * len(closes)
    position = 0
    for index in range(len(closes)):
        if fast[index] is not None and slow[index] is not None:
            position = 1 if fast[index] > slow[index] else -1 if fast[index] < slow[index] else position
        signals[index] = position

    split = max(slow_period, int(len(closes) * 0.7))
    strategy_returns: list[float] = []
    benchmark_returns: list[float] = []
    held_position = 0
    trades = 0
    for index in range(split, len(closes) - 1):
        next_position = signals[index]
        turnover = abs(next_position - held_position)
        trades += 1 if turnover else 0
        gross_return = (closes[index + 1] / closes[index] - 1) * next_position
        cost = turnover * spread_pips * pip_size / closes[index]
        strategy_returns.append(gross_return - cost)
        benchmark_returns.append((closes[index + 1] / closes[index] - 1) - (spread_pips * pip_size / closes[index] if index == split else 0))
        held_position = next_position

    periods = PERIODS_PER_YEAR.get(timeframe, 252)
    return {
        "strategy": "SMA crossover · long/short · fixed 10/30 by default",
        "timeframe": timeframe,
        "fast_period": fast_period,
        "slow_period": slow_period,
        "spread_assumption_pips": spread_pips,
        "split": {"method": "chronological 70/30 holdout", "train_bars": split,
                  "test_bars": len(closes) - split - 1},
        "out_of_sample": _summarize(strategy_returns, periods),
        "buy_and_hold_baseline": _summarize(benchmark_returns, periods),
        "trades": trades,
        "caveats": ["Signal calculated at bar close and applied to the next bar; no look-ahead in returns.",
                    "Spread is a fixed user-supplied assumption; slippage, financing, gaps and broker execution are omitted.",
                    "Short-history Yahoo bars are indicative; this backtest is not evidence of future profitability."],
    }
