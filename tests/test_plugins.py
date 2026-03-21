"""Tests for new TrashClaw plugins: markdown_table, text_diff, timer."""
import sys
import os
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMarkdownTable:
    """Tests for the markdown_table plugin."""

    def setup_method(self):
        from plugins.markdown_table import run
        self.run = run

    def test_basic_csv(self):
        result = self.run(data="Name,Age,City\nAlice,30,NYC\nBob,25,LA")
        assert "| Name" in result
        assert "| Alice" in result
        assert "---" in result

    def test_tab_separated(self):
        result = self.run(data="Col1\tCol2\nA\tB")
        assert "| Col1" in result
        assert "| A" in result

    def test_custom_delimiter(self):
        result = self.run(data="a;b;c\n1;2;3", delimiter=";")
        assert "| a" in result

    def test_right_align(self):
        result = self.run(data="X,Y\n1,2", align="right")
        assert "-:" in result

    def test_center_align(self):
        result = self.run(data="X,Y\n1,2", align="center")
        assert ":-" in result and "-:" in result

    def test_empty_data(self):
        result = self.run(data="")
        assert "Error" in result

    def test_single_row(self):
        result = self.run(data="Header1,Header2")
        assert "| Header1" in result

    def test_uneven_columns(self):
        result = self.run(data="A,B,C\n1,2\n3,4,5")
        assert "| A" in result


class TestTextDiff:
    """Tests for the text_diff plugin."""

    def setup_method(self):
        from plugins.text_diff import run
        self.run = run

    def test_identical_texts(self):
        result = self.run(text_a="hello", text_b="hello")
        assert "identical" in result.lower()

    def test_single_line_change(self):
        result = self.run(text_a="hello world", text_b="hello earth")
        assert "-hello world" in result
        assert "+hello earth" in result

    def test_multiline_diff(self):
        a = "line1\nline2\nline3"
        b = "line1\nchanged\nline3"
        result = self.run(text_a=a, text_b=b)
        assert "-line2" in result
        assert "+changed" in result

    def test_added_lines(self):
        a = "line1\nline2"
        b = "line1\nline2\nline3"
        result = self.run(text_a=a, text_b=b)
        assert "+line3" in result

    def test_empty_to_content(self):
        result = self.run(text_a="", text_b="new content")
        assert "+new content" in result

    def test_custom_context(self):
        a = "1\n2\n3\n4\n5\n6\n7\n8\n9\n10"
        b = "1\n2\n3\n4\nX\n6\n7\n8\n9\n10"
        result = self.run(text_a=a, text_b=b, context_lines=1)
        assert "@@" in result


class TestTimer:
    """Tests for the timer plugin."""

    def setup_method(self):
        from plugins.timer import run, _timers
        self.run = run
        _timers.clear()

    def test_start(self):
        result = self.run(action="start", name="test1")
        assert "started" in result.lower()

    def test_check(self):
        self.run(action="start", name="test1")
        result = self.run(action="check", name="test1")
        assert "elapsed" in result.lower()

    def test_stop(self):
        self.run(action="start", name="test1")
        result = self.run(action="stop", name="test1")
        assert "stopped" in result.lower()

    def test_check_nonexistent(self):
        result = self.run(action="check", name="nope")
        assert "not found" in result.lower()

    def test_stop_nonexistent(self):
        result = self.run(action="stop", name="nope")
        assert "not found" in result.lower()

    def test_list_empty(self):
        result = self.run(action="list")
        assert "no active" in result.lower()

    def test_list_active(self):
        self.run(action="start", name="t1")
        self.run(action="start", name="t2")
        result = self.run(action="list")
        assert "t1" in result
        assert "t2" in result

    def test_unknown_action(self):
        result = self.run(action="invalid")
        assert "unknown" in result.lower()
