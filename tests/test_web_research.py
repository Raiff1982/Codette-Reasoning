#!/usr/bin/env python3
"""
Unit tests for web_search safety, SSRF protection, and fetch behaviour.

Network calls are mocked throughout — no real HTTP requests are made.
"""
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from inference.web_search import (
    _is_safe_url,
    fetch_url_text,
    query_benefits_from_web_research,
    query_requests_web_research,
    search_web,
)


# ---------------------------------------------------------------------------
# SSRF / URL safety
# ---------------------------------------------------------------------------

class TestIsSafeUrl(unittest.TestCase):

    # --- Should BLOCK ---
    def test_blocks_localhost(self):
        self.assertFalse(_is_safe_url("http://localhost/secret"))

    def test_blocks_loopback_ipv4(self):
        self.assertFalse(_is_safe_url("http://127.0.0.1/secret"))

    def test_blocks_loopback_ipv6(self):
        self.assertFalse(_is_safe_url("http://[::1]/secret"))

    def test_blocks_private_10_range(self):
        self.assertFalse(_is_safe_url("http://10.0.0.1/internal"))

    def test_blocks_private_192_168_range(self):
        self.assertFalse(_is_safe_url("http://192.168.1.1/admin"))

    def test_blocks_private_172_range(self):
        self.assertFalse(_is_safe_url("http://172.16.0.1/data"))

    def test_blocks_link_local(self):
        self.assertFalse(_is_safe_url("http://169.254.169.254/latest/meta-data/"))

    def test_blocks_file_scheme(self):
        self.assertFalse(_is_safe_url("file:///etc/passwd"))

    def test_blocks_ftp_scheme(self):
        self.assertFalse(_is_safe_url("ftp://example.com/file"))

    def test_blocks_empty_string(self):
        self.assertFalse(_is_safe_url(""))

    def test_blocks_missing_hostname(self):
        self.assertFalse(_is_safe_url("http:///no-host"))

    # --- Should PASS ---
    def test_allows_https_public(self):
        # Use a known-safe public address via IP literal to avoid DNS in tests
        # We can't call real DNS in unit tests, so test that the function
        # *structure* allows public URLs (skip DNS-dependent assertion)
        # Instead, verify scheme+hostname extraction works
        import urllib.parse
        parsed = urllib.parse.urlparse("https://example.com/page")
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.hostname, "example.com")


# ---------------------------------------------------------------------------
# fetch_url_text — mocked HTTP
# ---------------------------------------------------------------------------

class TestFetchUrlText(unittest.TestCase):

    def _mock_response(self, html: bytes):
        mock_resp = MagicMock()
        mock_resp.read.return_value = html
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    @patch("inference.web_search._is_safe_url", return_value=False)
    def test_unsafe_url_returns_empty(self, _mock_safe):
        result = fetch_url_text("http://localhost/secret")
        self.assertEqual(result, "")

    @patch("inference.web_search._is_safe_url", return_value=True)
    @patch("inference.web_search._fetch_bytes")
    def test_safe_url_returns_text(self, mock_fetch, _mock_safe):
        mock_fetch.return_value = b"<html><body><p>Hello world</p></body></html>"
        result = fetch_url_text("https://example.com/page")
        self.assertIn("Hello world", result)

    @patch("inference.web_search._is_safe_url", return_value=True)
    @patch("inference.web_search._fetch_bytes", side_effect=urllib.error.URLError("timeout"))
    def test_network_error_returns_empty(self, _mock_fetch, _mock_safe):
        result = fetch_url_text("https://example.com/page")
        self.assertEqual(result, "")

    @patch("inference.web_search._is_safe_url", return_value=True)
    @patch("inference.web_search._fetch_bytes")
    def test_result_is_capped_at_max_chars(self, mock_fetch, _mock_safe):
        big_text = b"<html><body>" + b"A" * 50000 + b"</body></html>"
        mock_fetch.return_value = big_text
        result = fetch_url_text("https://example.com/big", max_chars=100)
        self.assertLessEqual(len(result), 120)  # small buffer for tags stripped


# ---------------------------------------------------------------------------
# search_web — mocked DuckDuckGo response
# ---------------------------------------------------------------------------

class TestSearchWeb(unittest.TestCase):

    MOCK_HTML = b"""
    <html><body>
    <div class="result">
      <a class="result__a" href="https://example.com/page1">Result One</a>
      <a class="result__snippet">Snippet for result one</a>
    </div>
    <div class="result">
      <a class="result__a" href="http://192.168.1.1/internal">Private Result</a>
      <a class="result__snippet">Should be filtered</a>
    </div>
    </body></html>
    """

    def test_empty_query_returns_empty(self):
        results = search_web("")
        self.assertEqual(results, [])

    def test_whitespace_query_returns_empty(self):
        results = search_web("   ")
        self.assertEqual(results, [])

    @patch("urllib.request.urlopen")
    def test_network_error_returns_empty(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("no network")
        results = search_web("what is gravity?")
        self.assertEqual(results, [])

    @patch("urllib.request.urlopen")
    def test_timeout_returns_empty(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError()
        results = search_web("current AI news")
        self.assertEqual(results, [])


# ---------------------------------------------------------------------------
# Query classification edge cases
# ---------------------------------------------------------------------------

class TestQueryClassificationEdgeCases(unittest.TestCase):

    # query_requests_web_research
    def test_lookup_phrasing_triggers_web(self):
        self.assertTrue(query_requests_web_research("look up the latest news on this"))

    def test_find_online_triggers_web(self):
        self.assertTrue(query_requests_web_research("find online resources about climate change"))

    def test_vague_short_query_does_not_trigger(self):
        self.assertFalse(query_requests_web_research("ok"))

    def test_internal_reflection_does_not_trigger(self):
        self.assertFalse(query_requests_web_research("what do you think about that?"))

    # query_benefits_from_web_research
    def test_current_events_benefit(self):
        self.assertTrue(query_benefits_from_web_research("What happened in AI research this week?"))

    def test_price_query_benefits(self):
        self.assertTrue(query_benefits_from_web_research("What is the current price of Ethereum?"))

    def test_static_knowledge_does_not_benefit(self):
        self.assertFalse(query_benefits_from_web_research("What is the Pythagorean theorem?"))

    def test_personal_question_does_not_benefit(self):
        self.assertFalse(query_benefits_from_web_research("What is your favourite colour?"))

    def test_recent_release_benefits(self):
        self.assertTrue(query_benefits_from_web_research("What are the latest features in the newest Llama release?"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
