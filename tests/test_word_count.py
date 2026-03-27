"""Tests for the word_count plugin."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
from word_count import run


def test_basic_text():
    result = run(text="Hello world. This is a test.")
    assert "Words: 6" in result
    assert "Sentences: 2" in result


def test_multiline():
    result = run(text="Line one\nLine two\nLine three")
    assert "Lines: 3" in result
    assert "Words: 6" in result


def test_file_input():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("One two three\nFour five")
        f.flush()
        result = run(file=f.name)
    os.unlink(f.name)
    assert "Words: 5" in result
    assert "Lines: 2" in result


def test_empty_input():
    result = run()
    assert "Error" in result


def test_missing_file():
    result = run(file="/nonexistent/path.txt")
    assert "Error" in result
