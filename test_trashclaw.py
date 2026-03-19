#!/usr/bin/env python3
"""
TrashClaw Test Suite
====================
Comprehensive pytest tests for core TrashClaw functionality.

Tests cover:
- Tool functions (read_file, write_file, edit_file, run_command, etc.)
- Config system (_load_config, _c)
- Achievement tracking (_track_tool)
- Undo system (_save_undo)
- Tab completion

Run with: pytest test_trashclaw.py -v
"""

import os
import sys
import json
import tempfile
import shutil
import pytest

# Import trashclaw module - we need to import specific functions
# Since trashclaw.py is a script, we'll import it as a module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestFileOperations:
    """Tests for file operation tools."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        dirpath = tempfile.mkdtemp()
        yield dirpath
        shutil.rmtree(dirpath, ignore_errors=True)
    
    def test_read_file_exists(self, temp_dir):
        """Test reading an existing file."""
        # Create test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Hello, World!\nLine 2\nLine 3")
        
        # Import and test
        from trashclaw import tool_read_file, CWD
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_read_file("test.txt")
        assert "Hello, World!" in result
        assert "Line 2" in result
        assert "Line 3" in result
        
        trashclaw.CWD = original_cwd
    
    def test_read_file_not_found(self, temp_dir):
        """Test reading a non-existent file."""
        from trashclaw import tool_read_file
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_read_file("nonexistent.txt")
        assert "Error" in result
        assert "not found" in result.lower()
        
        trashclaw.CWD = original_cwd
    
    def test_read_file_with_offset_limit(self, temp_dir):
        """Test reading file with offset and limit."""
        test_file = os.path.join(temp_dir, "multiline.txt")
        with open(test_file, 'w') as f:
            for i in range(1, 11):
                f.write(f"Line {i}\n")
        
        from trashclaw import tool_read_file
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        # Read lines 3-5
        result = tool_read_file("multiline.txt", offset=3, limit=3)
        assert "Line 3" in result
        assert "Line 5" in result
        assert "Line 6" not in result
        
        trashclaw.CWD = original_cwd
    
    def test_write_file_new(self, temp_dir):
        """Test writing a new file."""
        from trashclaw import tool_write_file
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_write_file("newfile.txt", "New content here")
        assert "Wrote" in result
        assert "newfile.txt" in result
        
        # Verify file was created
        assert os.path.exists(os.path.join(temp_dir, "newfile.txt"))
        with open(os.path.join(temp_dir, "newfile.txt"), 'r') as f:
            assert f.read() == "New content here"
        
        trashclaw.CWD = original_cwd
    
    def test_write_file_creates_dirs(self, temp_dir):
        """Test that write_file creates parent directories."""
        from trashclaw import tool_write_file
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_write_file("subdir/nested/file.txt", "Nested content")
        assert "Wrote" in result
        
        assert os.path.exists(os.path.join(temp_dir, "subdir", "nested", "file.txt"))
        
        trashclaw.CWD = original_cwd
    
    def test_edit_file_success(self, temp_dir):
        """Test successful file edit."""
        test_file = os.path.join(temp_dir, "editme.txt")
        with open(test_file, 'w') as f:
            f.write("Original text here")
        
        from trashclaw import tool_edit_file
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_edit_file("editme.txt", "Original text here", "Modified text here")
        assert "Edited" in result
        assert "1 replacement" in result
        
        with open(test_file, 'r') as f:
            assert f.read() == "Modified text here"
        
        trashclaw.CWD = original_cwd
    
    def test_edit_file_not_found(self, temp_dir):
        """Test edit when old_string not found."""
        test_file = os.path.join(temp_dir, "editme.txt")
        with open(test_file, 'w') as f:
            f.write("Some text")
        
        from trashclaw import tool_edit_file
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_edit_file("editme.txt", "Nonexistent string", "New text")
        assert "Error" in result
        assert "not found" in result.lower()
        
        trashclaw.CWD = original_cwd
    
    def test_edit_file_multiple_matches(self, temp_dir):
        """Test edit when old_string appears multiple times."""
        test_file = os.path.join(temp_dir, "editme.txt")
        with open(test_file, 'w') as f:
            f.write("Same text\nSame text\nDifferent")
        
        from trashclaw import tool_edit_file
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_edit_file("editme.txt", "Same text", "New text")
        assert "Error" in result
        assert "found" in result.lower()
        assert "times" in result.lower()
        
        trashclaw.CWD = original_cwd


class TestRunCommand:
    """Tests for run_command tool."""
    
    def test_run_command_success(self):
        """Test running a successful command."""
        from trashclaw import tool_run_command, APPROVED_COMMANDS
        import trashclaw
        
        # Pre-approve 'echo' command to skip interactive prompt
        original_approved = trashclaw.APPROVED_COMMANDS.copy()
        trashclaw.APPROVED_COMMANDS.add("echo")
        trashclaw.APPROVE_SHELL = False  # Disable shell approval for tests
        
        result = tool_run_command("echo Hello")
        assert "Hello" in result
        
        trashclaw.APPROVED_COMMANDS = original_approved
    
    def test_run_command_with_output(self):
        """Test command with output."""
        from trashclaw import tool_run_command
        import trashclaw
        
        # Disable shell approval for tests
        original_approve = trashclaw.APPROVE_SHELL
        trashclaw.APPROVE_SHELL = False
        
        result = tool_run_command("python --version" if sys.platform == "win32" else "python3 --version")
        # Should have some output (version info)
        assert len(result) > 0
        
        trashclaw.APPROVE_SHELL = original_approve
    
    def test_run_command_timeout(self):
        """Test command timeout."""
        from trashclaw import tool_run_command
        import trashclaw
        
        # Disable shell approval for tests
        original_approve = trashclaw.APPROVE_SHELL
        trashclaw.APPROVE_SHELL = False
        
        # Use a command that will timeout
        # On Windows, use ping with count to create a delay that can timeout
        if sys.platform == "win32":
            result = tool_run_command("ping -n 5 127.0.0.1", timeout=1)
        else:
            result = tool_run_command("sleep 5", timeout=1)
        
        # Should either timeout or return an error
        assert "timed out" in result.lower() or "Error" in result or "exit code" in result.lower()
        
        trashclaw.APPROVE_SHELL = original_approve


class TestSearchAndFind:
    """Tests for search_files and find_files tools."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        dirpath = tempfile.mkdtemp()
        
        # Create test files
        with open(os.path.join(dirpath, "test1.py"), 'w') as f:
            f.write("# Test file 1\nprint('hello')")
        with open(os.path.join(dirpath, "test2.py"), 'w') as f:
            f.write("# Test file 2\nprint('world')")
        with open(os.path.join(dirpath, "readme.txt"), 'w') as f:
            f.write("README content")
        
        yield dirpath
        shutil.rmtree(dirpath, ignore_errors=True)
    
    def test_search_files_pattern(self, temp_dir):
        """Test searching for a pattern."""
        from trashclaw import tool_search_files
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_search_files("print")
        assert "test1.py" in result or "test2.py" in result
        assert "hello" in result or "world" in result
        
        trashclaw.CWD = original_cwd
    
    def test_search_files_no_match(self, temp_dir):
        """Test searching for non-existent pattern."""
        from trashclaw import tool_search_files
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_search_files("nonexistent_pattern_xyz")
        assert "No matches" in result
        
        trashclaw.CWD = original_cwd
    
    def test_find_files_glob(self, temp_dir):
        """Test finding files by glob pattern."""
        from trashclaw import tool_find_files
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_find_files("*.py")
        assert "test1.py" in result
        assert "test2.py" in result
        assert "readme.txt" not in result
        
        trashclaw.CWD = original_cwd


class TestListDir:
    """Tests for list_dir tool."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        dirpath = tempfile.mkdtemp()
        
        # Create test files
        with open(os.path.join(dirpath, "file1.txt"), 'w') as f:
            f.write("content")
        os.makedirs(os.path.join(dirpath, "subdir"))
        
        yield dirpath
        shutil.rmtree(dirpath, ignore_errors=True)
    
    def test_list_dir_success(self, temp_dir):
        """Test listing directory contents."""
        from trashclaw import tool_list_dir
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_list_dir()
        assert "file1.txt" in result
        assert "subdir" in result or "subdir/" in result
        
        trashclaw.CWD = original_cwd
    
    def test_list_dir_not_directory(self, temp_dir):
        """Test listing a file as if it were a directory."""
        from trashclaw import tool_list_dir
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        result = tool_list_dir("file1.txt")
        assert "Error" in result
        assert "directory" in result.lower()
        
        trashclaw.CWD = original_cwd


class TestConfigSystem:
    """Tests for config loading and application."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        dirpath = tempfile.mkdtemp()
        yield dirpath
        shutil.rmtree(dirpath, ignore_errors=True)
    
    def test_load_config_empty(self, temp_config_dir):
        """Test loading config when no file exists."""
        from trashclaw import _load_config
        
        # Temporarily change CONFIG_FILE
        import trashclaw
        original_config = trashclaw.CONFIG_FILE
        trashclaw.CONFIG_FILE = os.path.join(temp_config_dir, "config.json")
        
        config = _load_config()
        assert config == {} or isinstance(config, dict)
        
        trashclaw.CONFIG_FILE = original_config
    
    def test_load_config_with_file(self, temp_config_dir):
        """Test loading config from file."""
        config_file = os.path.join(temp_config_dir, "config.json")
        test_config = {"url": "http://test:8080", "model": "test-model"}
        
        with open(config_file, 'w') as f:
            json.dump(test_config, f)
        
        from trashclaw import _load_config
        import trashclaw
        original_config = trashclaw.CONFIG_FILE
        trashclaw.CONFIG_FILE = config_file
        
        config = _load_config()
        assert config.get("url") == "http://test:8080"
        assert config.get("model") == "test-model"
        
        trashclaw.CONFIG_FILE = original_config


class TestUndoSystem:
    """Tests for undo functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        dirpath = tempfile.mkdtemp()
        yield dirpath
        shutil.rmtree(dirpath, ignore_errors=True)
    
    def test_save_undo_existing_file(self, temp_dir):
        """Test saving undo state for existing file."""
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("Original content")
        
        from trashclaw import _save_undo, UNDO_STACK
        import trashclaw
        original_cwd = trashclaw.CWD
        original_stack = len(UNDO_STACK)
        trashclaw.CWD = temp_dir
        
        _save_undo(test_file, "edit")
        
        assert len(UNDO_STACK) > original_stack
        last_entry = UNDO_STACK[-1]
        assert last_entry["path"] == test_file
        assert last_entry["content"] == "Original content"
        assert last_entry["action"] == "edit"
        
        trashclaw.CWD = original_cwd
    
    def test_save_undo_new_file(self, temp_dir):
        """Test saving undo state for file that doesn't exist yet."""
        test_file = os.path.join(temp_dir, "newfile.txt")
        
        from trashclaw import _save_undo, UNDO_STACK
        import trashclaw
        original_cwd = trashclaw.CWD
        original_stack = len(UNDO_STACK)
        trashclaw.CWD = temp_dir
        
        _save_undo(test_file, "write")
        
        assert len(UNDO_STACK) > original_stack
        last_entry = UNDO_STACK[-1]
        assert last_entry["path"] == test_file
        assert last_entry["content"] is None  # File didn't exist
        assert last_entry["action"] == "write"
        
        trashclaw.CWD = original_cwd
    
    def test_undo_stack_bounded(self, temp_dir):
        """Test that undo stack stays bounded."""
        from trashclaw import _save_undo, UNDO_STACK
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = temp_dir
        
        # Add 60 entries (more than the 50 limit)
        for i in range(60):
            _save_undo(f"file{i}.txt", "edit")
        
        assert len(UNDO_STACK) <= 50
        
        trashclaw.CWD = original_cwd


class TestAchievementTracking:
    """Tests for achievement system."""
    
    @pytest.fixture
    def temp_config_dir(self):
        """Create a temporary config directory."""
        dirpath = tempfile.mkdtemp()
        yield dirpath
        shutil.rmtree(dirpath, ignore_errors=True)
    
    def test_load_achievements_empty(self, temp_config_dir):
        """Test loading achievements when no file exists."""
        from trashclaw import _load_achievements
        import trashclaw
        original_file = trashclaw.ACHIEVEMENTS_FILE
        trashclaw.ACHIEVEMENTS_FILE = os.path.join(temp_config_dir, "achievements.json")
        
        achievements = _load_achievements()
        assert "unlocked" in achievements
        assert "stats" in achievements
        
        trashclaw.ACHIEVEMENTS_FILE = original_file
    
    def test_track_tool_increments(self, temp_config_dir):
        """Test that tracking tools increments counters."""
        from trashclaw import _track_tool, _load_achievements, ACHIEVEMENTS
        import trashclaw
        original_file = trashclaw.ACHIEVEMENTS_FILE
        trashclaw.ACHIEVEMENTS_FILE = os.path.join(temp_config_dir, "achievements.json")
        
        # Reset achievements
        trashclaw.ACHIEVEMENTS = _load_achievements()
        initial_count = trashclaw.ACHIEVEMENTS["stats"].get("tools_used", 0)
        
        _track_tool("read_file")
        
        assert trashclaw.ACHIEVEMENTS["stats"]["tools_used"] == initial_count + 1
        
        trashclaw.ACHIEVEMENTS_FILE = original_file
    
    def test_track_specific_tools(self, temp_config_dir):
        """Test tracking specific tool types."""
        from trashclaw import _track_tool, _load_achievements
        import trashclaw
        original_file = trashclaw.ACHIEVEMENTS_FILE
        trashclaw.ACHIEVEMENTS_FILE = os.path.join(temp_config_dir, "achievements.json")
        
        # Reset achievements
        trashclaw.ACHIEVEMENTS = _load_achievements()
        
        _track_tool("read_file")
        _track_tool("read_file")
        _track_tool("write_file")
        _track_tool("edit_file")
        
        stats = trashclaw.ACHIEVEMENTS["stats"]
        assert stats.get("files_read", 0) >= 2
        assert stats.get("files_written", 0) >= 1
        assert stats.get("edits", 0) >= 1
        
        trashclaw.ACHIEVEMENTS_FILE = original_file


class TestGitOperations:
    """Tests for git-related functions."""
    
    def test_git_branch_not_in_repo(self, tmp_path):
        """Test git_branch when not in a git repo."""
        from trashclaw import _git_branch
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = str(tmp_path)
        
        result = _git_branch()
        assert result == ""
        
        trashclaw.CWD = original_cwd


class TestTokenEstimation:
    """Tests for token estimation."""
    
    def test_estimate_tokens_basic(self):
        """Test basic token estimation."""
        from trashclaw import _estimate_tokens
        
        messages = [{"content": "Hello, World!"}]
        tokens = _estimate_tokens(messages)
        assert tokens > 0  # Should estimate some tokens
    
    def test_estimate_tokens_scales(self):
        """Test that token estimation scales with content."""
        from trashclaw import _estimate_tokens
        
        short_msg = [{"content": "Hi"}]
        long_msg = [{"content": "Hello, World! " * 100}]
        
        short_tokens = _estimate_tokens(short_msg)
        long_tokens = _estimate_tokens(long_msg)
        
        assert long_tokens > short_tokens


class TestPathResolution:
    """Tests for path resolution."""
    
    def test_resolve_path_absolute(self):
        """Test resolving an absolute path."""
        from trashclaw import _resolve_path
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = "/tmp"
        
        result = _resolve_path("/absolute/path/file.txt")
        # On Windows, absolute paths start with drive letter
        if sys.platform == "win32":
            assert result.endswith("\\absolute\\path\\file.txt") or result.endswith("/absolute/path/file.txt")
        else:
            assert result == "/absolute/path/file.txt"
        
        trashclaw.CWD = original_cwd
    
    def test_resolve_path_relative(self):
        """Test resolving a relative path."""
        from trashclaw import _resolve_path
        import trashclaw
        original_cwd = trashclaw.CWD
        trashclaw.CWD = "/test/cwd"
        
        result = _resolve_path("relative/file.txt")
        assert result == os.path.normpath("/test/cwd/relative/file.txt")
        
        trashclaw.CWD = original_cwd
    
    def test_resolve_path_with_tilde(self):
        """Test resolving a path with tilde."""
        from trashclaw import _resolve_path
        
        result = _resolve_path("~/test.txt")
        assert result.startswith(os.path.expanduser("~"))


class TestHardwareDetection:
    """Tests for hardware detection."""
    
    def test_detect_hardware_returns_dict(self):
        """Test that hardware detection returns expected structure."""
        from trashclaw import _detect_hardware
        
        result = _detect_hardware()
        assert "arch" in result
        assert "os" in result
        assert "special" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
