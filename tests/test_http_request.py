import pytest
from unittest.mock import patch, MagicMock
import urllib.error
import json

from plugins.http_request import run

def test_http_request_get():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.read.return_value = b'{"hello": "world"}'
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        
        result = run("http://example.com")
        
        assert "HTTP GET http://example.com" in result
        assert "Status: 200" in result
        assert "hello" in result
        assert "world" in result

def test_http_request_post():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 201
        mock_resp.headers = {}
        mock_resp.read.return_value = b'Created'
        mock_urlopen.return_value.__enter__.return_value = mock_resp
        
        result = run("http://example.com", method="POST", body='{"foo":"bar"}')
        
        assert "HTTP POST http://example.com" in result
        assert "Status: 201" in result
        assert "Created" in result
        
        # Verify request parameters
        req_arg = mock_urlopen.call_args[0][0]
        assert req_arg.get_method() == "POST"
        assert req_arg.data == b'{"foo":"bar"}'

def test_http_request_http_error():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://example.com", 404, "Not Found", None, None
        )
        
        result = run("http://example.com")
        
        assert "HTTP Error 404: Not Found" in result

def test_http_request_url_error():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        
        result = run("http://invalid.url")
        
        assert "URL Error: Connection refused" in result
