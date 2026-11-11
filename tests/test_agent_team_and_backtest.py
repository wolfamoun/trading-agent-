import math
import unittest

from agents.team import run
from research.backtest import run_moving_average_backtest


def market_snapshot():
    return {
        "ticker": "EURUSD=X", "pair": "EUR / USD", "timeframe": "D1", "price": 1.12,
        "change_pips": 8.0,
        "indicators": {
            "ema21": 1.11, "ema50": 1.10, "rsi14": 61.0,
            "macd_histogram": 0.0002, "adx14": 29.0, "atr14": 0.006,
            "atr_pips": 60.0,
        },
    }


class AgentTeamTests(unittest.TestCase):
    def test_specialists_report_computed_evidence_and_missing_sources(self):
        team = run(market_snapshot())
        self.assertEqual(team["technical"]["bias"], "bullish")
        self.assertGreaterEqual(len(team["technical"]["evidence"]), 4)
        self.assertEqual(team["risk"]["agent"], "risk_manager")
        self.assertIsNone(team["risk"]["position_size"])
        self.assertEqual(team["sentiment"]["status"], "unavailable")
        self.assertEqual(team["macro"]["status"], "unavailable")


class BacktestTests(unittest.TestCase):
    def setUp(self):
        self.bars = []
        price = 1.1
        for index in range(240):
            price += 0.00018 if index < 130 else -0.00011
            close = price + math.sin(index / 5) * 0.0004
            self.bars.append({"close": close})

    def test_holdout_backtest_reports_risk_metrics_and_assumptions(self):
        result = run_moving_average_backtest(self.bars, 0.0001, "D1", 10, 30, 1.0)
        self.assertEqual(result["split"]["method"], "chronological 70/30 holdout")
        self.assertGreater(result["out_of_sample"]["observations"], 0)
        self.assertIn("max_drawdown_pct", result["out_of_sample"])
        self.assertIn("annualized_sharpe", result["out_of_sample"])
        self.assertGreaterEqual(result["trades"], 1)
        self.assertTrue(any("next bar" in note for note in result["caveats"]))

    def test_backtest_rejects_invalid_periods_and_nonfinite_data(self):
        with self.assertRaises(ValueError):
            run_moving_average_backtest(self.bars, 0.0001, "D1", 30, 10)
        broken = [*self.bars]
        broken[40] = {"close": float("nan")}
        with self.assertRaises(ValueError):
            run_moving_average_backtest(broken, 0.0001, "D1")


if __name__ == "__main__":
    unittest.main()
