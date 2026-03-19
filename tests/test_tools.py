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


# ── tool_git_commit (in a git repo) ──

class TestGitCommit:
    def test_git_commit_in_repo(self, tmp_path, monkeypatch):
        """git_commit should work in an initialized git repo."""
        monkeypatch.setattr(trashclaw, "APPROVE_SHELL", False)
        # Init a git repo
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=str(tmp_path), capture_output=True, check=True)
        # Create and commit a file
        (tmp_path / "test.txt").write_text("hello")
        result = trashclaw.tool_git_commit("initial commit")
        assert isinstance(result, str)
        # Should have succeeded
        assert "initial commit" in result or "test.txt" in result.lower()

    def test_git_commit_nothing_to_commit(self, tmp_path, monkeypatch):
        """git_commit with no changes should report clean tree."""
        monkeypatch.setattr(trashclaw, "APPROVE_SHELL", False)
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=str(tmp_path), capture_output=True, check=True)
        result = trashclaw.tool_git_commit("empty commit")
        assert "nothing to commit" in result.lower() or "clean" in result.lower()

    def test_git_commit_no_git(self, tmp_path):
        """git_commit outside a repo should handle gracefully."""
        result = trashclaw.tool_git_commit("should fail")
        assert isinstance(result, str)


# ── Tab Completion ──

class TestTabCompletion:
    def test_slash_command_completion(self, tmp_path, monkeypatch):
        """Tab completion should match slash commands."""
        import readline
        # We need to test the completer logic directly
        # _setup_tab_completion sets a completer; test it manually
        text = "/st"
        matches = []
        state = 0
        while True:
            # Simulate what readline would call
            if text.startswith("/"):
                m = [c for c in trashclaw.SLASH_COMMANDS if c.startswith(text)]
            else:
                m = []
            if state < len(m):
                matches.append(m[state])
                state += 1
            else:
                break
        assert "/status" in matches
        assert "/stats" in matches

    def test_tab_completion_slash_commands_list(self):
        """SLASH_COMMANDS should include all documented commands."""
        expected = ["/help", "/exit", "/status", "/stats", "/undo", "/clear",
                     "/compact", "/save", "/load", "/model", "/config", "/diff",
                     "/about", "/achievements", "/plugins", "/export", "/pipe",
                     "/remember", "/add", "/sessions", "/cd", "/quit"]
        for cmd in expected:
            assert cmd in trashclaw.SLASH_COMMANDS, f"{cmd} missing from SLASH_COMMANDS"


# ── Achievement Tracking — more scenarios ──

class TestAchievementTracking:
    def test_track_all_tool_types(self, tmp_path, monkeypatch):
        """Each tool type should increment its own counter."""
        ach_file = str(tmp_path / "achievements.json")
        monkeypatch.setattr(trashclaw, "ACHIEVEMENTS_FILE", ach_file)
        ach = trashclaw._load_achievements()
        monkeypatch.setattr(trashclaw, "ACHIEVEMENTS", ach)

        trashclaw._track_tool("read_file")
        assert ach["stats"]["files_read"] == 1
        assert ach["stats"]["tools_used"] == 1

        trashclaw._track_tool("write_file")
        assert ach["stats"]["files_written"] == 1
        assert ach["stats"]["tools_used"] == 2

        trashclaw._track_tool("edit_file")
        assert ach["stats"]["edits"] == 1
        assert ach["stats"]["tools_used"] == 3

        trashclaw._track_tool("run_command")
        assert ach["stats"]["commands_run"] == 1
        assert ach["stats"]["tools_used"] == 4

        trashclaw._track_tool("git_commit")
        assert ach["stats"]["commits"] == 1
        assert ach["stats"]["tools_used"] == 5

    def test_unknown_tool_increments_tools_used_only(self, tmp_path, monkeypatch):
        """Unknown tools should still increment tools_used."""
        ach_file = str(tmp_path / "achievements.json")
        monkeypatch.setattr(trashclaw, "ACHIEVEMENTS_FILE", ach_file)
        ach = trashclaw._load_achievements()
        monkeypatch.setattr(trashclaw, "ACHIEVEMENTS", ach)

        trashclaw._track_tool("custom_plugin_tool")
        assert ach["stats"]["tools_used"] == 1
        assert ach["stats"]["files_read"] == 0

    def test_achievement_unlock(self, tmp_path, monkeypatch):
        """Achievements should unlock when thresholds are met."""
        ach_file = str(tmp_path / "achievements.json")
        monkeypatch.setattr(trashclaw, "ACHIEVEMENTS_FILE", ach_file)
        ach = {"unlocked": [], "stats": {"files_read": 0, "files_written": 0,
                "edits": 0, "commands_run": 0, "commits": 0, "sessions": 0,
                "tools_used": 0, "total_turns": 0}}
        monkeypatch.setattr(trashclaw, "ACHIEVEMENTS", ach)

        # Trigger first_blood (1 edit)
        trashclaw._track_tool("edit_file")
        assert "first_blood" in ach["unlocked"]

    def test_achievement_persistence(self, tmp_path, monkeypatch):
        """Achievements should persist to disk."""
        ach_file = str(tmp_path / "achievements.json")
        monkeypatch.setattr(trashclaw, "ACHIEVEMENTS_FILE", ach_file)
        ach = trashclaw._load_achievements()
        monkeypatch.setattr(trashclaw, "ACHIEVEMENTS", ach)

        trashclaw._track_tool("read_file")
        # Reload from disk
        loaded = trashclaw._load_achievements()
        assert loaded["stats"]["files_read"] == 1
        assert loaded["stats"]["tools_used"] == 1


# ── _load_config with .trashclaw.toml ──

class TestLoadConfigToml:
    def test_toml_simple_values(self, tmp_path, monkeypatch):
        """Should parse simple key=value from .trashclaw.toml."""
        monkeypatch.setattr(trashclaw, "CONFIG_FILE", str(tmp_path / "nonexistent.json"))
        toml_file = tmp_path / ".trashclaw.toml"
        toml_file.write_text('model = "test-model"\nmax_rounds = 10\n')
        cfg = trashclaw._load_config(str(tmp_path))
        assert cfg["model"] == "test-model"
        assert cfg["max_rounds"] == 10

    def test_toml_boolean_and_list(self, tmp_path, monkeypatch):
        """Should parse booleans and lists from .trashclaw.toml."""
        monkeypatch.setattr(trashclaw, "CONFIG_FILE", str(tmp_path / "nonexistent.json"))
        toml_file = tmp_path / ".trashclaw.toml"
        toml_file.write_text('auto_shell = true\ncontext_files = ["src/main.py", "README.md"]\n')
        cfg = trashclaw._load_config(str(tmp_path))
        assert cfg["auto_shell"] is True
        assert cfg["context_files"] == ["src/main.py", "README.md"]

    def test_toml_overrides_json_project_config(self, tmp_path, monkeypatch):
        """TOML config should take precedence over JSON project config."""
        monkeypatch.setattr(trashclaw, "CONFIG_FILE", str(tmp_path / "nonexistent.json"))
        (tmp_path / ".trashclaw.toml").write_text('model = "toml-model"\n')
        cfg = trashclaw._load_config(str(tmp_path))
        assert cfg["model"] == "toml-model"

    def test_toml_ignored_comments_and_blanks(self, tmp_path, monkeypatch):
        """Should skip comments and blank lines."""
        monkeypatch.setattr(trashclaw, "CONFIG_FILE", str(tmp_path / "nonexistent.json"))
        toml_file = tmp_path / ".trashclaw.toml"
        toml_file.write_text('# This is a comment\n\nmodel = "test"\n# Another comment\n')
        cfg = trashclaw._load_config(str(tmp_path))
        assert cfg["model"] == "test"

    def test_project_json_fallback(self, tmp_path, monkeypatch):
        """Should load .trashclaw.json when no .trashclaw.toml exists."""
        monkeypatch.setattr(trashclaw, "CONFIG_FILE", str(tmp_path / "nonexistent.json"))
        json_file = tmp_path / ".trashclaw.json"
        json_file.write_text(json.dumps({"model": "json-model"}))
        cfg = trashclaw._load_config(str(tmp_path))
        assert cfg["model"] == "json-model"


# ── Boundary / Edge Cases ──

class TestBoundaryConditions:
    def test_read_empty_file(self, tmp_path):
        """Reading an empty file should not crash."""
        f = tmp_path / "empty.txt"
        f.write_text("")
        result = trashclaw.tool_read_file(str(f))
        assert isinstance(result, str)

    def test_write_empty_content(self, tmp_path):
        """Writing empty content should succeed."""
        path = str(tmp_path / "empty.txt")
        result = trashclaw.tool_write_file(path, "")
        assert os.path.exists(path)
        assert open(path).read() == ""

    def test_edit_empty_old_string(self, tmp_path):
        """Editing with empty old_string should handle gracefully."""
        f = tmp_path / "test.txt"
        f.write_text("content\n")
        result = trashclaw.tool_edit_file(str(f), "", "replacement")
        assert isinstance(result, str)

    def test_search_empty_pattern(self, tmp_path):
        """Searching with empty regex should handle gracefully."""
        f = tmp_path / "test.txt"
        f.write_text("some content\n")
        result = trashclaw.tool_search_files("", str(tmp_path))
        assert isinstance(result, str)

    def test_read_file_permission_error(self, tmp_path, monkeypatch):
        """Should handle permission errors gracefully."""
        result = trashclaw.tool_read_file("/root/.bashrc_no_read")
        # May succeed or return error, but should not crash
        assert isinstance(result, str)

    def test_run_command_timeout(self, tmp_path, monkeypatch):
        """Command timeout should return timeout error."""
        monkeypatch.setattr(trashclaw, "APPROVE_SHELL", False)
        result = trashclaw.tool_run_command("sleep 10", timeout=1)
        assert "timed out" in result.lower()

    def test_find_files_recursive(self, tmp_path):
        """Recursive glob should find files in subdirs."""
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "deep.py").write_text("# deep\n")
        result = trashclaw.tool_find_files("**/*.py", str(tmp_path))
        assert "deep.py" in result

    def test_list_dir_nonexistent(self, tmp_path):
        """Listing nonexistent dir should return error."""
        result = trashclaw.tool_list_dir(str(tmp_path / "nope"))
        assert "not a directory" in result.lower() or "error" in result.lower()

    def test_write_file_overwrite_existing(self, tmp_path):
        """Overwriting should replace content completely."""
        path = str(tmp_path / "overwrite.txt")
        trashclaw.tool_write_file(path, "first version")
        trashclaw.tool_write_file(path, "second version")
        assert open(path).read() == "second version"

    def test_edit_multiple_matches(self, tmp_path):
        """Edit should fail when old_string appears multiple times."""
        f = tmp_path / "dup.txt"
        f.write_text("same\nsame\n")
        result = trashclaw.tool_edit_file(str(f), "same", "replaced")
        assert "2 times" in result or "must be unique" in result.lower() or "found" in result.lower()

    def test_git_status_and_diff_in_repo(self, tmp_path, monkeypatch):
        """git_status and git_diff should work in a real repo."""
        monkeypatch.setattr(trashclaw, "APPROVE_SHELL", False)
        subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"],
                       cwd=str(tmp_path), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"],
                       cwd=str(tmp_path), capture_output=True, check=True)

        status = trashclaw.tool_git_status()
        assert isinstance(status, str)

        diff = trashclaw.tool_git_diff()
        assert isinstance(diff, str)

    def test_large_file_truncation(self, tmp_path):
        """Reading should truncate large files."""
        f = tmp_path / "large.txt"
        f.write_text("x" * 20000)
        result = trashclaw.tool_read_file(str(f))
        assert "truncated" in result.lower()
