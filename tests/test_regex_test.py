"""Tests for the regex_test plugin."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
from regex_test import run


def test_basic_match():
    result = run(pattern=r"\d+", text="abc 123 def 456")
    assert "Matches: 2" in result
    assert '"123"' in result
    assert '"456"' in result


def test_no_match():
    result = run(pattern=r"\d+", text="no numbers here")
    assert "No matches" in result


def test_groups():
    result = run(pattern=r"(\w+)@(\w+)", text="user@host")
    assert '$1="user"' in result
    assert '$2="host"' in result


def test_flags_ignore_case():
    result = run(pattern="hello", text="HELLO world", flags="i")
    assert "Matches: 1" in result


def test_invalid_pattern():
    result = run(pattern="[unclosed", text="test")
    assert "error" in result.lower()


def test_missing_args():
    result = run()
    assert "Error" in result
