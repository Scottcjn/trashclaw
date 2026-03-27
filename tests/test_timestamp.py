"""Tests for the timestamp plugin."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
from timestamp import run


def test_now():
    result = run(now=True)
    assert "Unix:" in result
    assert "UTC:" in result


def test_unix_to_date():
    result = run(unix=0)
    assert "1970" in result


def test_date_to_unix():
    result = run(date="2026-03-25T12:00:00")
    assert "Unix:" in result
    assert "2026-03-25" in result


def test_invalid_date():
    result = run(date="not-a-date")
    assert "Error" in result or "could not parse" in result


def test_default_shows_now():
    result = run()
    assert "Current Time" in result
