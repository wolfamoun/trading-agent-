import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ChatFrontendContractTests(unittest.TestCase):
    def test_accessible_chat_and_theme_controls_exist(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="theme-toggle"', html)
        self.assertIn('id="chat-reset"', html)
        self.assertIn('id="chat-status"', html)
        self.assertIn('role="log"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn('for="chat-input"', html)

    def test_chat_state_is_bounded_persisted_and_retryable(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('sessionStorage.setItem(CHAT_STORAGE_KEY', script)
        self.assertIn("CHAT_HISTORY_LIMIT = 40", script)
        self.assertIn('className = "retry-message"', script)
        self.assertIn("fetchWithTimeout(\"/api/chat\"", script)
        self.assertIn("typing.remove()", script)
        self.assertIn('setAttribute("aria-busy", "false")', script)
        self.assertIn('fetchWithTimeout("/api/backtest"', script)
        self.assertIn('id="agent-reports"', html)
        self.assertIn('id="backtest-result"', html)
        self.assertIn('className = "message-sources"', script)

    def test_tradingview_chart_uses_supported_overlays_and_local_adx(self):
        script = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('studies: ["STD;RSI", "STD;MACD"]', script)
        self.assertIn("ADX is calculated locally", script)


if __name__ == "__main__":
    unittest.main()
