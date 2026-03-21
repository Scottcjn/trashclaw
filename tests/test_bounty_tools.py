import pytest
from plugins import word_count, timestamp, regex_test

def test_word_count():
    result = word_count.run("Hello world\nThis is a test.")
    assert "Lines: 2" in result
    assert "Words: 6" in result
    assert "Characters: 27" in result

    result_empty = word_count.run("")
    assert "Lines: 0" in result_empty

def test_timestamp_unix():
    result = timestamp.run("1609459200")
    assert "ISO Date: 2021-01-01T00:00:00+00:00" in result

def test_timestamp_iso():
    result = timestamp.run("2021-01-01T00:00:00+00:00")
    assert "Timestamp: 1609459200.0" in result

def test_regex_test():
    result = regex_test.run("^[0-9]+", "123abc456")
    assert "Match '123' at span (0, 3)" in result
    
    result2 = regex_test.run("a", "b")
    assert "No matches found." in result2
