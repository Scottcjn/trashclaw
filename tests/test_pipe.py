import os
import sys
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trashclaw


@pytest.fixture(autouse=True)
def reset_pipe_state(monkeypatch, tmp_path):
    monkeypatch.setattr(trashclaw, "LAST_ASSISTANT_RESPONSE", "hello from trashclaw")
    monkeypatch.setattr(trashclaw, "CWD", str(tmp_path))


def test_pipe_without_filename_saves_in_cwd(capsys, tmp_path):
    trashclaw.handle_slash("/pipe")
    captured = capsys.readouterr().out

    files = list(tmp_path.iterdir())
    assert len(files) == 1
    saved = files[0]
    assert saved.name.startswith("response_")
    assert saved.suffix == ".md"
    assert saved.read_text(encoding="utf-8") == "hello from trashclaw"
    assert str(saved) in captured
    assert saved.name in captured


def test_pipe_with_relative_filename_uses_cwd(capsys, tmp_path):
    trashclaw.handle_slash("/pipe notes/output.md")
    captured = capsys.readouterr().out

    saved = tmp_path / "notes" / "output.md"
    assert saved.exists()
    assert saved.read_text(encoding="utf-8") == "hello from trashclaw"
    assert str(saved) in captured
    assert "notes/output.md" in captured.replace("\\", "/")


def test_pipe_without_response_prints_error(capsys, monkeypatch):
    monkeypatch.setattr(trashclaw, "LAST_ASSISTANT_RESPONSE", "")
    trashclaw.handle_slash("/pipe")
    captured = capsys.readouterr().out
    assert "No assistant message found" in captured
