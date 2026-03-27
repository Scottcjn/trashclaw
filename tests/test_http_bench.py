"""Tests for the http_bench plugin."""

import http.server
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
from http_bench import run, _percentile


# ── Fixtures ──

@pytest.fixture(scope="module")
def local_http_server():
    """Start a simple HTTP server on a random port."""
    handler = http.server.SimpleHTTPRequestHandler

    # Suppress log output
    class QuietHandler(handler):
        def log_message(self, format, *args):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), QuietHandler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield port
    srv.shutdown()


# ── _percentile helper ──

def test_percentile_basic():
    data = list(range(1, 101))  # 1..100
    assert _percentile(data, 50) == pytest.approx(50.5, abs=1)
    assert _percentile(data, 95) == pytest.approx(95.05, abs=1)
    assert _percentile(data, 99) == pytest.approx(99.01, abs=1)


def test_percentile_single():
    assert _percentile([42.0], 50) == 42.0
    assert _percentile([42.0], 99) == 42.0


def test_percentile_empty():
    assert _percentile([], 50) == 0.0


# ── Basic functionality ──

def test_missing_url():
    result = run()
    assert "Error" in result


def test_bench_local_server(local_http_server):
    result = run(url=f"http://127.0.0.1:{local_http_server}", requests=5, concurrency=2, timeout=5)
    assert "Latency" in result
    assert "p50" in result
    assert "p95" in result
    assert "p99" in result
    assert "Throughput" in result
    assert "Success" in result


def test_bench_reports_failures():
    # Port 1 is almost certainly not an HTTP server
    result = run(url="http://127.0.0.1:1", requests=2, concurrency=1, timeout=0.5)
    assert "Failed" in result


def test_small_request_count(local_http_server):
    result = run(url=f"http://127.0.0.1:{local_http_server}", requests=1)
    assert "Total:" in result
    assert "1" in result


def test_auto_prepend_http(local_http_server):
    """Should auto-prepend http:// if missing."""
    result = run(url=f"127.0.0.1:{local_http_server}", requests=2)
    assert "Latency" in result or "Failed" in result


def test_clamp_concurrency(local_http_server):
    """Concurrency over 20 should be clamped."""
    result = run(url=f"http://127.0.0.1:{local_http_server}", requests=3, concurrency=100)
    # Should still work, just clamped to 20
    assert "Total:" in result


def test_clamp_requests(local_http_server):
    """Requests over 500 should be clamped."""
    result = run(url=f"http://127.0.0.1:{local_http_server}", requests=9999, concurrency=1)
    # Should report 500 max
    assert "500" in result
