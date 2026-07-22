# SPDX-License-Identifier: MIT
"""Tests that command-line flags survive the config reload done by --cwd.

Uses only pytest + stdlib. No LLM server is contacted: agent_turn is stubbed
and only records the global state main() ended up with.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trashclaw


@pytest.fixture
def run_main(tmp_path, monkeypatch):
    """Run main() with the given argv and report the resulting settings."""
    # Isolate from the developer's own config/env so defaults are the real ones.
    monkeypatch.setattr(trashclaw, "CONFIG_FILE", str(tmp_path / "no-such-config.json"))
    for var in ("TRASHCLAW_READONLY", "TRASHCLAW_AUTO_SHELL", "TRASHCLAW_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(trashclaw, "READ_ONLY_MODE", False)
    monkeypatch.setattr(trashclaw, "APPROVE_SHELL", True)
    monkeypatch.setattr(trashclaw, "LLAMA_URL", "http://localhost:8080")

    project = tmp_path / "project"
    project.mkdir()

    def _run(*flags):
        seen = {}
        monkeypatch.setattr(
            trashclaw,
            "agent_turn",
            lambda msg: seen.update(
                read_only=trashclaw.READ_ONLY_MODE,
                approve_shell=trashclaw.APPROVE_SHELL,
                url=trashclaw.LLAMA_URL,
                blocks_write=trashclaw._read_only_blocked("write_file", {}),
                tool_names={
                    t["function"]["name"] for t in trashclaw._available_tools()
                },
            ),
        )
        argv = ["trashclaw.py"]
        for flag in flags:
            argv.extend(flag.replace("{cwd}", str(project)).split(" "))
        argv.extend(["-e", "audit this repo"])
        monkeypatch.setattr(sys, "argv", argv)
        trashclaw.main()
        return seen

    _run.project = project
    return _run


def test_read_only_survives_later_cwd(run_main):
    """--read-only before --cwd must still block writes (order must not matter)."""
    for flags in (
        ("--read-only",),
        ("--read-only", "--cwd {cwd}"),
        ("--cwd {cwd}", "--read-only"),
        ("--read-only", "--cwd={cwd}"),
    ):
        seen = run_main(*flags)
        assert seen["read_only"] is True, flags
        assert seen["blocks_write"] is True, flags
        for blocked in trashclaw.READ_ONLY_BLOCKED_TOOLS:
            assert blocked not in seen["tool_names"], (flags, blocked)


def test_url_and_auto_shell_survive_later_cwd(run_main):
    seen = run_main("--url http://box:9999", "--cwd {cwd}")
    assert seen["url"] == "http://box:9999"

    seen = run_main("--auto-shell", "--cwd {cwd}")
    assert seen["approve_shell"] is False


def test_project_config_still_applies_when_no_flag_overrides_it(run_main):
    """--cwd must keep loading the project config for settings not set on the CLI."""
    (run_main.project / ".trashclaw.json").write_text('{"read_only": true}')
    seen = run_main("--cwd {cwd}")
    assert seen["read_only"] is True
    assert seen["blocks_write"] is True
