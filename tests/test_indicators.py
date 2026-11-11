import json
import math
import unittest

import main


class IndicatorQualityTests(unittest.TestCase):
    def synthetic_bars(self, count=240):
        bars = []
        for index in range(count):
            base = 1.08 + index * 0.00002 + math.sin(index / 5) * 0.001
            bars.append({
                "time": 1_700_000_000 + index * 3600,
                "open": base,
                "high": base + 0.0007,
                "low": base - 0.0006,
                "close": base + math.cos(index / 4) * 0.0002,
                "volume": float(index * 100),
            })
        return bars

    def test_fx_indicator_snapshot_is_json_serializable_and_finite(self):
        output = main.indicators(self.synthetic_bars(), "EURUSD=X")
        json.dumps(output, allow_nan=False)
        numeric = [value for value in output.values() if isinstance(value, (int, float))]
        self.assertTrue(numeric)
        self.assertTrue(all(math.isfinite(value) for value in numeric))
        self.assertGreaterEqual(output["rsi14"], 0)
        self.assertLessEqual(output["rsi14"], 100)
        self.assertGreater(output["atr_pips"], 0)

    def test_invalid_market_symbol_fails_before_network_access(self):
        with self.assertRaises(main.HTTPException) as error:
            import asyncio
            asyncio.run(main.market_snapshot("NOT-A-PAIR", "H1"))
        self.assertEqual(error.exception.status_code, 422)


if __name__ == "__main__":
    unittest.main()
