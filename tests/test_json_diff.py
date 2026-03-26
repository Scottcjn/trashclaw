"""Tests for the json_diff plugin."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
from json_diff import run, _flatten


# ── _flatten helper ──

def test_flatten_simple():
    result = _flatten({"a": 1, "b": 2})
    assert result == {"a": 1, "b": 2}


def test_flatten_nested():
    result = _flatten({"a": {"b": {"c": 3}}})
    assert result == {"a.b.c": 3}


def test_flatten_list():
    result = _flatten({"items": [10, 20, 30]})
    assert result == {"items[0]": 10, "items[1]": 20, "items[2]": 30}


def test_flatten_mixed():
    result = _flatten({"a": 1, "b": {"c": [1, 2]}})
    assert result == {"a": 1, "b.c[0]": 1, "b.c[1]": 2}


# ── Inline JSON diffs ──

def test_identical():
    result = run(json_a='{"x": 1}', json_b='{"x": 1}')
    assert "identical" in result.lower() or "no differences" in result.lower()


def test_added_key():
    result = run(json_a='{"a": 1}', json_b='{"a": 1, "b": 2}')
    assert "ADDED" in result
    assert "b" in result


def test_removed_key():
    result = run(json_a='{"a": 1, "b": 2}', json_b='{"a": 1}')
    assert "REMOVED" in result
    assert "b" in result


def test_changed_value():
    result = run(json_a='{"a": 1}', json_b='{"a": 99}')
    assert "CHANGED" in result
    assert "1" in result
    assert "99" in result


def test_nested_diff():
    a = json.dumps({"config": {"debug": True, "port": 8080}})
    b = json.dumps({"config": {"debug": False, "port": 8080}})
    result = run(json_a=a, json_b=b)
    assert "CHANGED" in result
    assert "config.debug" in result


def test_summary_line():
    result = run(json_a='{"a": 1}', json_b='{"b": 2}')
    assert "Summary" in result
    assert "+1" in result
    assert "-1" in result


# ── File-based diffs ──

def test_file_diff(tmp_path):
    fa = tmp_path / "a.json"
    fb = tmp_path / "b.json"
    fa.write_text('{"name": "alice", "age": 30}')
    fb.write_text('{"name": "bob", "age": 30}')

    result = run(file_a=str(fa), file_b=str(fb))
    assert "CHANGED" in result
    assert "name" in result


def test_file_not_found():
    result = run(file_a="/tmp/nonexistent_trashclaw_a.json", json_b='{"a":1}')
    assert "Error" in result and "not found" in result


def test_invalid_json():
    result = run(json_a="not json", json_b='{"a":1}')
    assert "Error" in result and "invalid" in result.lower()


def test_no_input():
    result = run()
    assert "Error" in result
