import os
import pytest
import trashclaw
from trashclaw import _save_undo, tool_write_file, UNDO_STACK

@pytest.fixture(autouse=True)
def clean_undo_stack():
    """Clear the undo stack before each test."""
    trashclaw.UNDO_STACK.clear()
    yield
    trashclaw.UNDO_STACK.clear()

def test_save_undo_write(tmp_path):
    path = tmp_path / "undo_test.txt"
    # No file yet
    _save_undo(str(path), "write")
    
    assert len(trashclaw.UNDO_STACK) == 1
    assert trashclaw.UNDO_STACK[0]["path"] == str(path)
    assert trashclaw.UNDO_STACK[0]["content"] is None
    assert trashclaw.UNDO_STACK[0]["action"] == "write"

def test_save_undo_edit(tmp_path):
    path = tmp_path / "edit_test.txt"
    content = "Original Content"
    with open(path, "w") as f:
        f.write(content)
        
    _save_undo(str(path), "edit")
    
    assert len(trashclaw.UNDO_STACK) == 1
    assert trashclaw.UNDO_STACK[0]["content"] == content
    assert trashclaw.UNDO_STACK[0]["action"] == "edit"

def test_tool_write_triggers_undo(tmp_path):
    path = str(tmp_path / "auto_undo.txt")
    tool_write_file(path, "new content")
    
    assert len(trashclaw.UNDO_STACK) == 1
    assert trashclaw.UNDO_STACK[0]["path"] == path
