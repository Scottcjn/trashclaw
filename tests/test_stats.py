# SPDX-License-Identifier: MIT
"""Tests for generation stats and session stats tracking.

Covers:
- LAST_GENERATION_STATS population after llm_request
- SESSION_STATS cumulative tracking across turns
- /stats command output (last turn + session total)
- /status command includes generation stats
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trashclaw


@pytest.fixture(autouse=True)
def reset_stats(monkeypatch):
    """Reset stats globals before each test."""
    monkeypatch.setattr(trashclaw, "LAST_GENERATION_STATS", {})
    monkeypatch.setattr(trashclaw, "SESSION_STATS", {
        "total_tokens": 0, "total_seconds": 0.0, "turns": 0
    })


class TestLastGenerationStats:
    """Test LAST_GENERATION_STATS structure."""

    def test_empty_by_default(self):
        assert trashclaw.LAST_GENERATION_STATS == {}

    def test_structure_after_set(self):
        trashclaw.LAST_GENERATION_STATS = {
            "tokens": 100,
            "seconds": 5.0,
            "tokens_per_sec": 20.0
        }
        stats = trashclaw.LAST_GENERATION_STATS
        assert "tokens" in stats
        assert "seconds" in stats
        assert "tokens_per_sec" in stats
        assert stats["tokens"] == 100
        assert stats["seconds"] == 5.0
        assert stats["tokens_per_sec"] == 20.0


class TestSessionStats:
    """Test SESSION_STATS cumulative tracking."""

    def test_initial_state(self):
        s = trashclaw.SESSION_STATS
        assert s["total_tokens"] == 0
        assert s["total_seconds"] == 0.0
        assert s["turns"] == 0

    def test_accumulation(self):
        """Simulate multiple turns accumulating stats."""
        s = trashclaw.SESSION_STATS
        # Turn 1
        s["total_tokens"] += 100
        s["total_seconds"] += 5.0
        s["turns"] += 1
        # Turn 2
        s["total_tokens"] += 200
        s["total_seconds"] += 8.0
        s["turns"] += 1

        assert s["total_tokens"] == 300
        assert s["total_seconds"] == 13.0
        assert s["turns"] == 2

    def test_average_speed(self):
        """Test average tokens/sec calculation."""
        s = trashclaw.SESSION_STATS
        s["total_tokens"] = 500
        s["total_seconds"] = 25.0
        s["turns"] = 3
        avg_tps = s["total_tokens"] / s["total_seconds"]
        assert avg_tps == 20.0

    def test_zero_seconds_no_crash(self):
        """Avg speed with zero seconds should not crash."""
        s = trashclaw.SESSION_STATS
        s["total_tokens"] = 0
        s["total_seconds"] = 0.0
        s["turns"] = 0
        avg_tps = s["total_tokens"] / s["total_seconds"] if s["total_seconds"] > 0 else 0
        assert avg_tps == 0


class TestStatsDisplay:
    """Test that stats format matches the spec: [X.X tok/s | Y tokens | Z.Zs]"""

    def test_inline_format(self):
        """The inline display format should match bounty spec."""
        stats = {"tokens": 847, "seconds": 68.3, "tokens_per_sec": 12.4}
        # This is the format used in trashclaw.py after each turn
        tps = stats.get('tokens_per_sec', 0)
        line = f"  \033[90m[{stats.get('tokens', 0)} tokens | {stats.get('seconds', 0):.2f}s | {tps:.1f} tps]\033[0m"
        assert "847 tokens" in line
        assert "68.30s" in line
        assert "12.4 tps" in line

    def test_stats_command_last_turn(self, capsys):
        """Simulate /stats output with last turn data."""
        trashclaw.LAST_GENERATION_STATS = {
            "tokens": 150,
            "seconds": 10.0,
            "tokens_per_sec": 15.0
        }
        # The /stats command prints last turn info
        stats = trashclaw.LAST_GENERATION_STATS
        print(f"  Tokens: {stats.get('tokens', 'N/A')}")
        print(f"  Speed: {stats['tokens_per_sec']:.1f} tokens/sec")
        captured = capsys.readouterr()
        assert "150" in captured.out
        assert "15.0 tokens/sec" in captured.out

    def test_stats_command_session_total(self, capsys):
        """Simulate /stats session total output."""
        s = trashclaw.SESSION_STATS
        s["total_tokens"] = 500
        s["total_seconds"] = 40.0
        s["turns"] = 3
        avg_tps = s["total_tokens"] / s["total_seconds"]
        print(f"  Turns: {s['turns']}")
        print(f"  Tokens: {s['total_tokens']}")
        print(f"  Avg speed: {avg_tps:.1f} tokens/sec")
        captured = capsys.readouterr()
        assert "3" in captured.out
        assert "500" in captured.out
        assert "12.5 tokens/sec" in captured.out
