import pytest
from unittest.mock import MagicMock
import urllib.error
import urllib.request
import sys
import os

# Add parent directory to path so we can import trashclaw
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from trashclaw import tool_fetch_url

@pytest.fixture
def mock_urlopen(monkeypatch):
    """Fixture to mock urllib.request.urlopen"""
    mock = MagicMock()
    monkeypatch.setattr(urllib.request, "urlopen", mock)
    return mock

def test_fetch_url_happy_path_html(mock_urlopen):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.read.return_value = b"""
    <html>
        <head><title>Test Title</title></head>
        <body>
            <h1>Hello World</h1>
            <script>alert('hidden');</script>
            <style>body { color: red; }</style>
            <p>This is a &lt;test&gt; paragraph with &amp; some &quot;entities&quot;.</p>
        </body>
    </html>
    """
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    result = tool_fetch_url("https://example.com")
    
    # Verify script/style removal, tag stripping, and entity decoding
    assert "Test Title" in result
    assert "Hello World" in result
    assert "hidden" not in result
    assert "color: red" not in result
    assert "This is a <test> paragraph with & some \"entities\"." in result

def test_fetch_url_plain_text(mock_urlopen):
    mock_response = MagicMock()
    mock_response.read.return_value = b"Just some plain text content without HTML tags."
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    result = tool_fetch_url("https://example.com/text.txt")
    assert result == "Fetched https://example.com/text.txt:\n\nJust some plain text content without HTML tags."

def test_fetch_url_empty_readable_text(mock_urlopen):
    # Setup mock response with only scripts/styles and no real text
    mock_response = MagicMock()
    mock_response.read.return_value = b"<script>const a = 1;</script><style>.a {}</style>   "
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    result = tool_fetch_url("https://example.com/empty")
    assert result == "Fetched https://example.com/empty successfully, but found no readable text."

def test_fetch_url_http_error(mock_urlopen):
    # Simulate HTTP 404 error
    mock_urlopen.side_effect = urllib.error.HTTPError(
        "https://example.com", 404, "Not Found", {}, None)
    
    result = tool_fetch_url("https://example.com")
    assert result == "HTTP Error fetching https://example.com: 404 Not Found"

def test_fetch_url_timeout(mock_urlopen):
    # Simulate a timeout
    import socket
    mock_urlopen.side_effect = socket.timeout("timed out")
    
    result = tool_fetch_url("https://example.com/sleep")
    assert result == "Error fetching https://example.com/sleep: timed out"

def test_fetch_url_unknown_scheme():
    # Calling it with an invalid URL without mocking
    result = tool_fetch_url("not_a_url")
    assert "Error fetching not_a_url" in result or "URL Error" in result
