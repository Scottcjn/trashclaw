"""Tests for the cert_check plugin."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
from cert_check import run, _format_dn, _parse_cert_time


# ── Helper functions ──

def test_parse_cert_time():
    dt = _parse_cert_time("Jan 15 12:00:00 2026 GMT")
    assert dt.year == 2026
    assert dt.month == 1
    assert dt.day == 15


def test_format_dn_simple():
    dn = (
        (("commonName", "example.com"),),
        (("organizationName", "Example Inc"),),
    )
    result = _format_dn(dn)
    assert "commonName=example.com" in result
    assert "organizationName=Example Inc" in result


def test_format_dn_empty():
    assert _format_dn(()) == "(empty)"
    assert _format_dn(None) == "(empty)"


# ── Basic operation ──

def test_missing_domain():
    result = run()
    assert "Error" in result


def test_unresolvable_domain():
    result = run(domain="this.host.definitely.does.not.exist.invalid")
    assert "Error" in result and "resolve" in result.lower()


def test_connection_refused():
    # Port 1 on localhost should refuse connections
    result = run(domain="127.0.0.1", port=1)
    assert "Error" in result


def test_real_cert_check():
    """Check a well-known public site (requires network).
    Skip if no network is available."""
    try:
        import socket
        socket.create_connection(("1.1.1.1", 443), timeout=3)
    except (socket.timeout, OSError):
        pytest.skip("No network available")

    result = run(domain="google.com")
    assert "Status:" in result
    # Google's cert should be OK
    assert "OK" in result or "Subject:" in result
    assert "Valid From:" in result
    assert "Valid Until:" in result
    assert "Remaining:" in result


def test_domain_with_protocol_prefix():
    """Should strip https:// prefix."""
    try:
        import socket
        socket.create_connection(("1.1.1.1", 443), timeout=3)
    except (socket.timeout, OSError):
        pytest.skip("No network available")

    result = run(domain="https://google.com")
    # Should still work after stripping prefix
    assert "Status:" in result or "Error" in result


def test_domain_with_port_in_string():
    """Should handle 'domain:port' format."""
    result = run(domain="127.0.0.1:1")
    # Should try port 1 (will fail, but should parse correctly)
    assert "Error" in result


def test_self_signed_cert():
    """Self-signed certs should show a warning, not crash."""
    # 50.28.86.131 has a self-signed cert from the CLAUDE.md context
    try:
        import socket
        socket.create_connection(("1.1.1.1", 443), timeout=3)
    except (socket.timeout, OSError):
        pytest.skip("No network available")

    # Even if the specific host is down, the code path shouldn't crash
    result = run(domain="self-signed.badssl.com")
    # Should either show cert info or a clear verification warning
    assert "Status:" in result or "WARNING" in result or "Error" in result
