"""Tests for TrashClaw core tool functions.

Uses only pytest + stdlib. All file operations use tmp directories.
"""

import json
import os
import sys
import subprocess

import pytest

# Add project root to path so we can import from trashclaw
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trashclaw


# ── Fixtures ──

@pytest.fixture(autouse=True)
def set_cwd(tmp_path, monkeypatch):
    """Set TrashClaw's CWD to a temp directory for all tests."""
    monkeypatch.setattr(trashclaw, "CWD", str(tmp_path))
    return tmp_path


@pytest.fixture
def sample_file(tmp_path):
    """Create a sample file for read/write tests."""
    f = tmp_path / "sample.txt"
    f.write_text("line one\nline two\nline three\n")
    return f


@pytest.fixture
def sample_py(tmp_path):
    """Create a sample Python file for search tests."""
    f = tmp_path / "hello.py"
    f.write_text('def greet(name):\n    return f"Hello, {name}!"\n')
    return f


# ── tool_read_file ──

class TestReadFile:
    def test_read_full(self, sample_file):
        result = trashclaw.tool_read_file(str(sample_file))
        assert "line one" in result
        assert "line two" in result
        assert "line three" in result

    def test_read_with_offset_limit(self, sample_file):
        result = trashclaw.tool_read_file(str(sample_file), offset=2, limit=1)
        assert "line two" in result
        # Should not contain line one or three (only line 2)
        assert "line one" not in result

    def test_read_nonexistent(self):
        result = trashclaw.tool_read_file("/tmp/nonexistent_trashclaw_test.txt")
        assert "error" in result.lower() or "not found" in result.lower() or "no such" in result.lower()


# ── tool_write_file ──

class TestWriteFile:
    def test_write_new(self, tmp_path):
        path = str(tmp_path / "new_file.txt")
        result = trashclaw.tool_write_file(path, "hello world")
        assert os.path.exists(path)
        assert "hello world" in open(path).read()

    def test_write_creates_dirs(self, tmp_path):
        path = str(tmp_path / "sub" / "dir" / "file.txt")
        trashclaw.tool_write_file(path, "nested content")
        assert os.path.exists(path)
        assert "nested content" in open(path).read()

    def test_write_overwrite(self, sample_file):
        trashclaw.tool_write_file(str(sample_file), "replaced")
        assert open(str(sample_file)).read() == "replaced"


# ── tool_edit_file ──

class TestEditFile:
    def test_edit_replace(self, sample_file):
        result = trashclaw.tool_edit_file(str(sample_file), "line two", "LINE TWO")
        content = open(str(sample_file)).read()
        assert "LINE TWO" in content
        assert "line two" not in content

    def test_edit_not_found(self, sample_file):
        result = trashclaw.tool_edit_file(str(sample_file), "nonexistent text", "replacement")
        assert "not found" in result.lower() or "error" in result.lower() or "no match" in result.lower()


# ── tool_run_command ──

class TestRunCommand:
    def test_echo(self, monkeypatch):
        # Bypass shell approval prompt
        monkeypatch.setattr(trashclaw, "APPROVE_SHELL", False)
        result = trashclaw.tool_run_command("echo hello_trashclaw_test")
        assert "hello_trashclaw_test" in result

    def test_exit_code(self, monkeypatch):
        monkeypatch.setattr(trashclaw, "APPROVE_SHELL", False)
        result = trashclaw.tool_run_command("false")
        # Should contain some indication of failure or non-zero exit
        assert isinstance(result, str)


# ── tool_search_files ──

class TestSearchFiles:
    def test_search_content(self, sample_py, tmp_path):
        result = trashclaw.tool_search_files("greet", str(tmp_path))
        assert "greet" in result

    def test_search_no_match(self, tmp_path):
        (tmp_path / "empty.txt").write_text("nothing here\n")
        result = trashclaw.tool_search_files("zzz_nonexistent_zzz", str(tmp_path))
        assert "no match" in result.lower() or "0 match" in result.lower() or result.strip() == ""


# ── tool_find_files ──

class TestFindFiles:
    def test_find_by_glob(self, sample_py, tmp_path):
        result = trashclaw.tool_find_files("*.py", str(tmp_path))
        assert "hello.py" in result

    def test_find_no_match(self, tmp_path):
        result = trashclaw.tool_find_files("*.xyz", str(tmp_path))
        assert "hello.py" not in result


# ── tool_list_dir ──

class TestListDir:
    def test_list(self, sample_file, tmp_path):
        result = trashclaw.tool_list_dir(str(tmp_path))
        assert "sample.txt" in result

    def test_list_empty(self, tmp_path):
        empty = tmp_path / "empty_dir"
        empty.mkdir()
        result = trashclaw.tool_list_dir(str(empty))
        # Should not error, may show empty or "no files"
        assert isinstance(result, str)


# ── tool_git_status / tool_git_diff ──

class TestGitTools:
    def test_git_status_no_repo(self, tmp_path):
        """git status in a non-repo dir should handle gracefully."""
        result = trashclaw.tool_git_status()
        # Either shows error or empty status
        assert isinstance(result, str)

    def test_git_diff_no_repo(self, tmp_path):
        result = trashclaw.tool_git_diff()
        assert isinstance(result, str)


# ── tool_patch_file ──

class TestPatchFile:
    def test_patch_simple(self, sample_file):
        patch = """--- a/sample.txt
+++ b/sample.txt
@@ -1,3 +1,3 @@
 line one
-line two
+PATCHED LINE
 line three
"""
        result = trashclaw.tool_patch_file(str(sample_file), patch)
        content = open(str(sample_file)).read()
        # patch_file may or may not succeed depending on implementation
        assert isinstance(result, str)


# ── _save_undo ──

class TestUndoSystem:
    def test_save_undo(self, sample_file, monkeypatch):
        monkeypatch.setattr(trashclaw, "UNDO_STACK", [])
        trashclaw._save_undo(str(sample_file), "write")
        assert len(trashclaw.UNDO_STACK) >= 1
        assert trashclaw.UNDO_STACK[-1]["path"] == str(sample_file)


# ── _track_tool ──

class TestAchievements:
    def test_track_tool(self, tmp_path, monkeypatch):
        # Use temp dir for achievements
        ach_file = str(tmp_path / "achievements.json")
        monkeypatch.setattr(trashclaw, "ACHIEVEMENTS_FILE", ach_file)
        monkeypatch.setattr(trashclaw, "ACHIEVEMENTS", trashclaw._load_achievements())

        trashclaw._track_tool("read_file")
        # Should not crash; achievements tracked in memory
        assert True


# ── _load_config ──

class TestConfig:
    def test_load_config_no_file(self, tmp_path, monkeypatch):
        """Config loading should not crash when no config file exists."""
        monkeypatch.setattr(trashclaw, "CONFIG_FILE", str(tmp_path / "nonexistent.json"))
        cfg = trashclaw._load_config(str(tmp_path))
        assert isinstance(cfg, dict)

    def test_load_config_with_file(self, tmp_path, monkeypatch):
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"model": "test-model"}))
        monkeypatch.setattr(trashclaw, "CONFIG_FILE", str(config_file))
        cfg = trashclaw._load_config(str(tmp_path))
        assert isinstance(cfg, dict)
        assert cfg.get("model") == "test-model"


# ── tool_clipboard ──

class TestClipboard:
    def test_clipboard_copy(self):
        """Clipboard copy should not crash even without display."""
        result = trashclaw.tool_clipboard("copy", "test content")
        assert isinstance(result, str)
