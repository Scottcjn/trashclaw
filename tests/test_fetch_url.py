"""
Tests for tool_fetch_url and tool_think.

Covers:
- Happy path: HTML fetching, tag stripping, entity decoding, whitespace collapse
- Error handling: HTTPError (404/500), URLError (no host), generic exceptions
- Edge cases: empty response body, output truncation at MAX_OUTPUT_CHARS
- tool_think: always returns a string with no side effects
"""

import os
import sys
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path so we can import trashclaw
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trashclaw


# ── Helpers ──

def _make_mock_response(html: str):
    """Create a mock urllib response that returns the given HTML bytes."""
    mock = MagicMock()
    mock.read.return_value = html.encode("utf-8")
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


# ── tool_fetch_url: happy path ──

class TestFetchUrlHappyPath:
    """Test normal successful fetches."""

    def test_returns_fetched_prefix(self):
        """Successful fetch should include 'Fetched <url>:' in the result."""
        html = "<html><body><p>Hello world</p></body></html>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert "Fetched http://example.com" in result
        assert "Hello world" in result

    def test_strips_html_tags(self):
        """HTML tags should be stripped from the response body."""
        html = "<html><body><b>bold</b> and <i>italic</i></body></html>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert "<b>" not in result
        assert "<i>" not in result
        assert "bold" in result
        assert "italic" in result

    def test_strips_script_blocks(self):
        """<script> blocks and their content should be entirely removed."""
        html = "<html><body><p>visible</p><script>alert('xss');</script></body></html>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert "alert" not in result
        assert "visible" in result

    def test_strips_style_blocks(self):
        """<style> blocks and their content should be entirely removed."""
        html = "<html><head><style>body { color: red; }</style></head><body>text</body></html>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert "color: red" not in result
        assert "text" in result

    def test_decodes_html_entity_amp(self):
        """&amp; should be decoded to &."""
        html = "<p>Tom &amp; Jerry</p>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert "Tom & Jerry" in result

    def test_decodes_html_entity_lt_gt(self):
        """&lt; and &gt; should be decoded to < and >."""
        html = "<p>&lt;tag&gt;</p>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert "<tag>" in result

    def test_decodes_html_entity_nbsp(self):
        """&nbsp; should be decoded to a space."""
        html = "<p>hello&nbsp;world</p>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert "hello" in result
        assert "world" in result

    def test_collapses_whitespace(self):
        """Multiple consecutive spaces/newlines should be collapsed to single spaces."""
        html = "<p>word1   \n\n  word2</p>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        # Should not have multiple spaces between the words
        assert "word1  " not in result
        assert "word1" in result
        assert "word2" in result

    def test_returns_string(self):
        """Return value should always be a string."""
        html = "<html><body>content</body></html>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert isinstance(result, str)


# ── tool_fetch_url: error handling ──

class TestFetchUrlErrors:
    """Test that network errors are handled gracefully and return informative strings."""

    def test_http_error_404(self):
        """HTTPError (404 Not Found) should return a readable HTTP Error message."""
        err = urllib.error.HTTPError(
            url="http://example.com/missing",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=err):
            result = trashclaw.tool_fetch_url("http://example.com/missing")
        assert "HTTP Error" in result
        assert "404" in result

    def test_http_error_500(self):
        """HTTPError (500 Internal Server Error) should return a readable message."""
        err = urllib.error.HTTPError(
            url="http://example.com",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )
        with patch("urllib.request.urlopen", side_effect=err):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert "HTTP Error" in result
        assert "500" in result

    def test_url_error_no_host(self):
        """URLError (e.g. no network / bad hostname) should return a URL Error message."""
        err = urllib.error.URLError(reason="Name or service not known")
        with patch("urllib.request.urlopen", side_effect=err):
            result = trashclaw.tool_fetch_url("http://this-host-does-not-exist.invalid")
        assert "URL Error" in result

    def test_generic_exception(self):
        """Any unexpected exception should be caught and returned as a string."""
        with patch("urllib.request.urlopen", side_effect=RuntimeError("something broke")):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert "Error" in result
        assert isinstance(result, str)


# ── tool_fetch_url: edge cases ──

class TestFetchUrlEdgeCases:
    """Test boundary conditions."""

    def test_empty_response_body(self):
        """If the page has no readable text after stripping, return a sensible message."""
        html = "<html><body>   <script>var x=1;</script>  </body></html>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        # Should not crash; either returns fetched text or a no-text notice
        assert isinstance(result, str)
        assert "http://example.com" in result

    def test_output_truncated_when_too_large(self, monkeypatch):
        """Responses larger than MAX_OUTPUT_CHARS should be truncated."""
        # Generate a response larger than the limit
        big_text = "A" * (trashclaw.MAX_OUTPUT_CHARS + 500)
        html = f"<html><body>{big_text}</body></html>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert "truncated" in result.lower()
        # The result itself should not exceed the limit by more than a small margin
        assert len(result) < trashclaw.MAX_OUTPUT_CHARS + 200

    def test_url_is_included_in_result(self):
        """The original URL should always appear somewhere in the result."""
        url = "http://my-custom-url.example.org/path"
        html = "<p>content</p>"
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url(url)
        assert url in result

    def test_multiline_script_stripped(self):
        """Multi-line script blocks should be fully removed."""
        html = (
            "<body>"
            "<script type='text/javascript'>\n"
            "  var secret = 'password';\n"
            "  doSomething();\n"
            "</script>"
            "<p>public content</p>"
            "</body>"
        )
        with patch("urllib.request.urlopen", return_value=_make_mock_response(html)):
            result = trashclaw.tool_fetch_url("http://example.com")
        assert "secret" not in result
        assert "public content" in result


# ── tool_think ──

class TestThinkTool:
    """Test tool_think — the scratchpad/reasoning tool."""

    def test_returns_string(self):
        """tool_think should always return a string."""
        result = trashclaw.tool_think("I should check the file first.")
        assert isinstance(result, str)

    def test_no_side_effects_on_history(self):
        """tool_think should not modify HISTORY."""
        original_len = len(trashclaw.HISTORY)
        trashclaw.tool_think("thinking about stuff")
        assert len(trashclaw.HISTORY) == original_len

    def test_empty_thought(self):
        """tool_think with an empty string should not crash."""
        result = trashclaw.tool_think("")
        assert isinstance(result, str)

    def test_long_thought(self):
        """tool_think with a very long string should not crash."""
        result = trashclaw.tool_think("think " * 1000)
        assert isinstance(result, str)

    def test_thought_content_ignored(self):
        """The return value should be the same regardless of thought content."""
        result_a = trashclaw.tool_think("plan A")
        result_b = trashclaw.tool_think("plan B")
        assert result_a == result_b
