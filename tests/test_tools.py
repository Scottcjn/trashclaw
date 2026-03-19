"""
Test suite for TrashClaw core tool functions.
Uses only pytest (no external dependencies beyond pytest itself).
All file operations use tmp directories.
"""

import os
import sys
import json
import tempfile
import shutil

import pytest

# Add parent dir so we can import trashclaw internals
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# We need to set CWD before importing, and mock readline for CI
# trashclaw uses module-level globals, so we patch before import
os.environ.setdefault("TRASHCLAW_URL", "http://localhost:8080")

import trashclaw


@pytest.fixture(autouse=True)
def tmp_workspace(tmp_path):
    """Set CWD to a temp directory for every test."""
    old_cwd = trashclaw.CWD
    trashclaw.CWD = str(tmp_path)
    trashclaw.UNDO_STACK.clear()
    yield tmp_path
    trashclaw.CWD = old_cwd


# ── read_file ──

class TestReadFile:
    def test_read_existing_file(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("line1\nline2\nline3\n")
        result = trashclaw.tool_read_file(str(f))
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result

    def test_read_nonexistent_file(self, tmp_path):
        result = trashclaw.tool_read_file(str(tmp_path / "nope.txt"))
        assert "Error" in result
        assert "not found" in result.lower()

    def test_read_with_offset_and_limit(self, tmp_path):
        f = tmp_path / "nums.txt"
        f.write_text("\n".join(f"line{i}" for i in range(1, 21)))
        result = trashclaw.tool_read_file(str(f), offset=5, limit=3)
        assert "line5" in result
        assert "line7" in result
        # line8 should not be included (only 3 lines from offset 5)
        assert "line8" not in result

    def test_read_relative_path(self, tmp_path):
        f = tmp_path / "rel.txt"
        f.write_text("relative content")
        result = trashclaw.tool_read_file("rel.txt")
        assert "relative content" in result


# ── write_file ──

class TestWriteFile:
    def test_write_new_file(self, tmp_path):
        path = str(tmp_path / "new.txt")
        result = trashclaw.tool_write_file(path, "hello world")
        assert "Wrote" in result
        assert os.path.exists(path)
        with open(path) as f:
            assert f.read() == "hello world"

    def test_write_creates_directories(self, tmp_path):
        path = str(tmp_path / "sub" / "dir" / "file.txt")
        result = trashclaw.tool_write_file(path, "nested")
        assert "Wrote" in result
        assert os.path.exists(path)

    def test_write_overwrites_existing(self, tmp_path):
        path = str(tmp_path / "exist.txt")
        with open(path, "w") as f:
            f.write("old content")
        trashclaw.tool_write_file(path, "new content")
        with open(path) as f:
            assert f.read() == "new content"

    def test_write_populates_undo_stack(self, tmp_path):
        path = str(tmp_path / "undo_test.txt")
        with open(path, "w") as f:
            f.write("before")
        trashclaw.tool_write_file(path, "after")
        assert len(trashclaw.UNDO_STACK) == 1
        assert trashclaw.UNDO_STACK[0]["content"] == "before"


# ── edit_file ──

class TestEditFile:
    def test_edit_replaces_string(self, tmp_path):
        f = tmp_path / "edit.txt"
        f.write_text("hello world\nfoo bar\n")
        result = trashclaw.tool_edit_file(str(f), "foo bar", "baz qux")
        assert "Edited" in result
        assert f.read_text() == "hello world\nbaz qux\n"

    def test_edit_nonexistent_file(self, tmp_path):
        result = trashclaw.tool_edit_file(str(tmp_path / "nope.txt"), "a", "b")
        assert "Error" in result

    def test_edit_string_not_found(self, tmp_path):
        f = tmp_path / "edit2.txt"
        f.write_text("hello world\n")
        result = trashclaw.tool_edit_file(str(f), "nonexistent string", "replacement")
        assert "not found" in result.lower()

    def test_edit_ambiguous_match(self, tmp_path):
        f = tmp_path / "dup.txt"
        f.write_text("aaa\naaa\n")
        result = trashclaw.tool_edit_file(str(f), "aaa", "bbb")
        assert "2 times" in result or "found 2" in result.lower()

    def test_edit_populates_undo_stack(self, tmp_path):
        f = tmp_path / "undo_edit.txt"
        f.write_text("original text here")
        trashclaw.tool_edit_file(str(f), "original", "modified")
        assert len(trashclaw.UNDO_STACK) == 1
        assert trashclaw.UNDO_STACK[0]["content"] == "original text here"


# ── run_command ──

class TestRunCommand:
    def test_run_simple_command(self, tmp_path):
        # Disable shell approval for tests
        old_approve = trashclaw.APPROVE_SHELL
        trashclaw.APPROVE_SHELL = False
        try:
            result = trashclaw.tool_run_command("echo hello_from_test")
            assert "hello_from_test" in result
        finally:
            trashclaw.APPROVE_SHELL = old_approve

    def test_run_cd_command(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        old_approve = trashclaw.APPROVE_SHELL
        trashclaw.APPROVE_SHELL = False
        try:
            result = trashclaw.tool_run_command(f"cd {sub}")
            assert "Changed directory" in result
            assert trashclaw.CWD == str(sub)
        finally:
            trashclaw.APPROVE_SHELL = old_approve

    def test_run_cd_nonexistent(self, tmp_path):
        old_approve = trashclaw.APPROVE_SHELL
        trashclaw.APPROVE_SHELL = False
        try:
            result = trashclaw.tool_run_command("cd /nonexistent_dir_12345")
            assert "Error" in result or "not found" in result.lower()
        finally:
            trashclaw.APPROVE_SHELL = old_approve


# ── search_files ──

class TestSearchFiles:
    def test_search_finds_pattern(self, tmp_path):
        f = tmp_path / "searchable.py"
        f.write_text("def hello():\n    return 'world'\n\ndef goodbye():\n    pass\n")
        result = trashclaw.tool_search_files("hello", str(tmp_path))
        assert "hello" in result

    def test_search_no_matches(self, tmp_path):
        f = tmp_path / "empty_search.txt"
        f.write_text("nothing here\n")
        result = trashclaw.tool_search_files("zzzznonexistent", str(tmp_path))
        assert "no matches" in result.lower() or result.strip() == ""

    def test_search_with_glob_filter(self, tmp_path):
        (tmp_path / "a.py").write_text("target\n")
        (tmp_path / "b.txt").write_text("target\n")
        result = trashclaw.tool_search_files("target", str(tmp_path), "*.py")
        assert "a.py" in result


# ── find_files ──

class TestFindFiles:
    def test_find_by_glob(self, tmp_path):
        (tmp_path / "foo.py").write_text("")
        (tmp_path / "bar.py").write_text("")
        (tmp_path / "baz.txt").write_text("")
        result = trashclaw.tool_find_files("*.py", str(tmp_path))
        assert "foo.py" in result
        assert "bar.py" in result
        assert "baz.txt" not in result

    def test_find_no_matches(self, tmp_path):
        result = trashclaw.tool_find_files("*.xyz", str(tmp_path))
        assert "no files" in result.lower() or result.strip() == ""


# ── list_dir ──

class TestListDir:
    def test_list_dir_contents(self, tmp_path):
        (tmp_path / "file1.txt").write_text("")
        (tmp_path / "file2.py").write_text("")
        sub = tmp_path / "subdir"
        sub.mkdir()
        result = trashclaw.tool_list_dir(str(tmp_path))
        assert "file1.txt" in result
        assert "file2.py" in result
        assert "subdir" in result

    def test_list_dir_default_cwd(self, tmp_path):
        (tmp_path / "cwd_file.txt").write_text("")
        result = trashclaw.tool_list_dir()
        assert "cwd_file.txt" in result


# ── git operations ──

class TestGitOps:
    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a temporary git repo."""
        old_cwd = trashclaw.CWD
        trashclaw.CWD = str(tmp_path)
        os.system(f"cd {tmp_path} && git init -q && git config user.email test@test.com && git config user.name Test")
        # Initial commit so we have a branch
        (tmp_path / "init.txt").write_text("init")
        os.system(f"cd {tmp_path} && git add . && git commit -q -m 'init'")
        yield tmp_path
        trashclaw.CWD = old_cwd

    def test_git_status(self, git_repo):
        (git_repo / "new_file.txt").write_text("new")
        result = trashclaw.tool_git_status()
        assert "new_file.txt" in result

    def test_git_diff(self, git_repo):
        tracked = git_repo / "init.txt"
        tracked.write_text("modified content")
        result = trashclaw.tool_git_diff()
        assert "modified content" in result or "init" in result

    def test_git_commit(self, git_repo):
        (git_repo / "commit_test.txt").write_text("commit me")
        result = trashclaw.tool_git_commit("test commit message")
        assert "commit" in result.lower() or "test commit message" in result


# ── config system ──

class TestConfig:
    def test_load_config_default(self, tmp_path):
        cfg = trashclaw._load_config(str(tmp_path))
        assert isinstance(cfg, dict)

    def test_load_config_from_toml(self, tmp_path):
        toml_file = tmp_path / ".trashclaw.toml"
        toml_file.write_text('url = "http://test:1234"\nmax_rounds = 5\n')
        cfg = trashclaw._load_config(str(tmp_path))
        assert cfg.get("url") == "http://test:1234"
        assert cfg.get("max_rounds") == 5

    def test_config_bool_parsing(self, tmp_path):
        toml_file = tmp_path / ".trashclaw.toml"
        toml_file.write_text('auto_shell = true\n')
        cfg = trashclaw._load_config(str(tmp_path))
        assert cfg.get("auto_shell") is True


# ── achievement tracking ──

class TestAchievements:
    def test_track_tool_increments(self, tmp_path):
        # Reset achievement stats with all required keys to avoid KeyError
        trashclaw.ACHIEVEMENTS["stats"] = {
            "tools_used": 0, "files_read": 0, "files_written": 0,
            "edits": 0, "commands_run": 0, "commits": 0,
            "total_turns": 0, "sessions": 0,
        }
        trashclaw.ACHIEVEMENTS["unlocked"] = []
        trashclaw._track_tool("read_file")
        assert trashclaw.ACHIEVEMENTS["stats"]["files_read"] == 1
        assert trashclaw.ACHIEVEMENTS["stats"]["tools_used"] == 1
        trashclaw._track_tool("read_file")
        assert trashclaw.ACHIEVEMENTS["stats"]["files_read"] == 2
        assert trashclaw.ACHIEVEMENTS["stats"]["tools_used"] == 2


# ── undo system ──

class TestUndo:
    def test_save_undo_existing_file(self, tmp_path):
        f = tmp_path / "undo.txt"
        f.write_text("original")
        trashclaw.UNDO_STACK.clear()
        trashclaw._save_undo(str(f), "write")
        assert len(trashclaw.UNDO_STACK) == 1
        assert trashclaw.UNDO_STACK[0]["content"] == "original"
        assert trashclaw.UNDO_STACK[0]["action"] == "write"

    def test_save_undo_new_file(self, tmp_path):
        trashclaw.UNDO_STACK.clear()
        trashclaw._save_undo(str(tmp_path / "new.txt"), "write")
        assert len(trashclaw.UNDO_STACK) == 1
        assert trashclaw.UNDO_STACK[0]["content"] is None

    def test_undo_stack_bounded(self, tmp_path):
        trashclaw.UNDO_STACK.clear()
        for i in range(60):
            f = tmp_path / f"file_{i}.txt"
            f.write_text(f"content_{i}")
            trashclaw._save_undo(str(f), "write")
        assert len(trashclaw.UNDO_STACK) <= 50


# ── tab completion ──

class TestTabCompletion:
    def test_slash_command_completion(self):
        """Verify slash commands list is populated."""
        assert "/help" in trashclaw.SLASH_COMMANDS
        assert "/exit" in trashclaw.SLASH_COMMANDS
        assert "/save" in trashclaw.SLASH_COMMANDS
        assert "/pipe" in trashclaw.SLASH_COMMANDS


# ── patch_file ──

class TestPatchFile:
    def test_patch_applies_unified_diff(self, tmp_path):
        f = tmp_path / "patch_target.txt"
        f.write_text("line1\nline2\nline3\n")
        patch = """--- a/patch_target.txt
+++ b/patch_target.txt
@@ -1,3 +1,3 @@
 line1
-line2
+line2_modified
 line3
"""
        result = trashclaw.tool_patch_file(str(f), patch)
        content = f.read_text()
        assert "line2_modified" in content
        assert "Patched" in result or "Applied" in result or "line2_modified" in result


# ── clipboard ──

class TestClipboard:
    def test_clipboard_paste_no_crash(self):
        """Clipboard may not be available in CI, but shouldn't crash."""
        result = trashclaw.tool_clipboard("paste")
        # Either returns content or an error message — both are fine
        assert isinstance(result, str)


# ── think tool ──

class TestThink:
    def test_think_returns_thought(self):
        result = trashclaw.tool_think("I need to consider the architecture")
        assert isinstance(result, str)


# ── detect_project_context ──

class TestDetectProjectContext:
    def test_detects_python(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("")
        result = trashclaw.detect_project_context()
        assert "Python" in result

    def test_detects_node(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        result = trashclaw.detect_project_context()
        assert "Node" in result

    def test_detects_rust(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text("")
        result = trashclaw.detect_project_context()
        assert "Rust" in result

    def test_detects_ruby(self, tmp_path):
        (tmp_path / "Gemfile").write_text("")
        result = trashclaw.detect_project_context()
        assert "Ruby" in result

    def test_unknown_project(self, tmp_path):
        result = trashclaw.detect_project_context()
        assert "Unknown" in result or "Generic" in result


# ── resolve_path ──

class TestResolvePath:
    def test_absolute_path(self, tmp_path):
        result = trashclaw._resolve_path("/absolute/path")
        assert result == os.path.normpath("/absolute/path")

    def test_relative_path(self, tmp_path):
        result = trashclaw._resolve_path("relative/file.txt")
        expected = os.path.normpath(os.path.join(str(tmp_path), "relative/file.txt"))
        assert result == expected

    def test_home_expansion(self):
        result = trashclaw._resolve_path("~/test.txt")
        assert "~" not in result


# ── estimate_tokens ──

class TestEstimateTokens:
    def test_estimate_returns_int(self):
        messages = [{"content": "hello world this is a test"}]
        result = trashclaw._estimate_tokens(messages)
        assert isinstance(result, int)
        assert result > 0

    def test_empty_messages(self):
        result = trashclaw._estimate_tokens([])
        assert result == 0
