import json
import unittest
from pathlib import Path

import main


class ChatEvalContractTests(unittest.TestCase):
    def test_quality_suite_matches_the_active_prompt_version(self):
        root = Path(__file__).resolve().parents[1]
        suite = json.loads((root / "evals" / "forex_chat_cases.json").read_text(encoding="utf-8"))
        self.assertEqual(suite["prompt_version"], main.PROMPT_VERSION)
        self.assertGreaterEqual(len(suite["cases"]), 3)
        self.assertTrue(all(case["must_include_any"] and case["must_not_include"] for case in suite["cases"]))


if __name__ == "__main__":
    unittest.main()
