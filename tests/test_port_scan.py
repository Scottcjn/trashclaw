"""Tests for the port_scan plugin."""

import os
import sys
import socket
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
from port_scan import run, _check_port


@pytest.fixture
def local_server():
    """Start a TCP server on a random port for testing."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]

    def accept_loop():
        try:
            while True:
                conn, _ = srv.accept()
                conn.close()
        except OSError:
            pass

    t = threading.Thread(target=accept_loop, daemon=True)
    t.start()
    yield port
    srv.close()


def test_missing_host():
    result = run()
    assert "Error" in result


def test_bad_hostname():
    result = run(host="this.host.definitely.does.not.exist.invalid")
    assert "Error" in result and "resolve" in result.lower()


def test_scan_open_port(local_server):
    result = run(host="127.0.0.1", ports=str(local_server), timeout=2)
    assert "OPEN" in result
    assert str(local_server) in result


def test_scan_closed_port():
    # Port 1 is almost certainly closed on localhost
    result = run(host="127.0.0.1", ports="1", timeout=0.5)
    assert "closed" in result


def test_scan_multiple_ports(local_server):
    result = run(host="127.0.0.1", ports=f"1,{local_server}", timeout=1)
    assert "OPEN" in result
    assert "closed" in result
    assert "Summary" in result


def test_bad_port_format():
    result = run(host="127.0.0.1", ports="abc,def")
    assert "Error" in result


def test_too_many_ports():
    ports = ",".join(str(i) for i in range(101))
    result = run(host="127.0.0.1", ports=ports)
    assert "Error" in result and "100" in result


def test_check_port_helper(local_server):
    assert _check_port("127.0.0.1", local_server, 2.0) is True
    assert _check_port("127.0.0.1", 1, 0.5) is False


def test_default_ports_used():
    """When no ports specified, defaults are used and output has summary."""
    result = run(host="127.0.0.1", timeout=0.3)
    assert "Summary" in result
    # Should see at least some of the default ports mentioned
    assert "closed" in result or "OPEN" in result
