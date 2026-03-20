import os
import pytest
import json
import trashclaw
from trashclaw import _track_tool, _save_achievements, ACHIEVEMENTS, ACHIEVEMENT_DEFS

@pytest.fixture(autouse=True)
def mock_achievements(tmp_path, monkeypatch):
    """Ensure achievements are saved to a temporary directory."""
    temp_config = tmp_path / ".trashclaw"
    temp_config.mkdir()
    temp_file = temp_config / "achievements.json"
    
    # Mock global variables
    monkeypatch.setattr(trashclaw, "CONFIG_DIR", str(temp_config))
    monkeypatch.setattr(trashclaw, "ACHIEVEMENTS_FILE", str(temp_file))
    
    # Reset ACHIEVEMENTS for each test
    initial = {
        "unlocked": [],
        "stats": {
            "files_read": 0, "files_written": 0, "edits": 0,
            "commands_run": 0, "commits": 0, "sessions": 0,
            "tools_used": 0, "total_turns": 0
        }
    }
    monkeypatch.setitem(trashclaw.ACHIEVEMENTS, "unlocked", initial["unlocked"])
    monkeypatch.setitem(trashclaw.ACHIEVEMENTS, "stats", initial["stats"])
    return temp_file

def test_track_tool_increments_stats():
    # Record stats before
    before = trashclaw.ACHIEVEMENTS["stats"]["files_read"]
    
    _track_tool("read_file")
    
    assert trashclaw.ACHIEVEMENTS["stats"]["files_read"] == before + 1
    assert trashclaw.ACHIEVEMENTS["stats"]["tools_used"] >= 1

def test_unlock_achievement():
    # Manual stat injection to trigger unlock
    # 'first_blood' needs 1 edit
    _track_tool("edit_file")
    
    assert "first_blood" in trashclaw.ACHIEVEMENTS["unlocked"]

def test_persistence(mock_achievements):
    _track_tool("read_file")
    _save_achievements(trashclaw.ACHIEVEMENTS)
    
    assert os.path.exists(str(mock_achievements))
    with open(str(mock_achievements), 'r') as f:
        data = json.load(f)
    assert data["stats"]["files_read"] >= 1
