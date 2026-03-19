import os
import sys
import tempfile
import shutil
import json
from unittest.mock import patch, MagicMock, mock_open
import pytest

# Add the parent directory to sys.path to import trashclaw
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import trashclaw


class TestFileOperations:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
    def teardown_method(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
        
    def test_read_file_existing(self):
        test_content = "Hello, world!\nThis is a test file."
        test_file = os.path.join(self.temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write(test_content)
            
        result = trashclaw.read_file("test.txt")
        assert result == test_content
        
    def test_read_file_nonexistent(self):
        result = trashclaw.read_file("nonexistent.txt")
        assert "Error reading file" in result
        
    def test_write_file_new(self):
        content = "New file content\nSecond line"
        result = trashclaw.write_file("new_file.txt", content)
        
        assert "File 'new_file.txt' written successfully" in result
        with open("new_file.txt", "r") as f:
            assert f.read() == content
            
    def test_write_file_overwrite(self):
        # Create initial file
        with open("existing.txt", "w") as f:
            f.write("original content")
            
        new_content = "overwritten content"
        result = trashclaw.write_file("existing.txt", new_content)
        
        assert "File 'existing.txt' written successfully" in result
        with open("existing.txt", "r") as f:
            assert f.read() == new_content
            
    def test_edit_file_existing(self):
        original = "Line 1\nLine 2\nLine 3"
        with open("edit_test.txt", "w") as f:
            f.write(original)
            
        # Test replacing a line
        result = trashclaw.edit_file("edit_test.txt", "Line 2", "Modified Line 2")
        
        assert "File 'edit_test.txt' edited successfully" in result
        with open("edit_test.txt", "r") as f:
            content = f.read()
            assert "Modified Line 2" in content
            assert "Line 2" not in content
            
    def test_edit_file_pattern_not_found(self):
        with open("edit_test.txt", "w") as f:
            f.write("Some content")
            
        result = trashclaw.edit_file("edit_test.txt", "nonexistent", "replacement")
        assert "Pattern 'nonexistent' not found" in result
        
    def test_list_dir_current(self):
        # Create some test files and directories
        os.makedirs("subdir")
        with open("file1.txt", "w") as f:
            f.write("test")
        with open("file2.py", "w") as f:
            f.write("print('hello')")
            
        result = trashclaw.list_dir(".")
        
        assert "subdir/" in result
        assert "file1.txt" in result
        assert "file2.py" in result
        
    def test_list_dir_specific_path(self):
        subdir = os.path.join(self.temp_dir, "testdir")
        os.makedirs(subdir)
        
        test_file = os.path.join(subdir, "nested.txt")
        with open(test_file, "w") as f:
            f.write("nested content")
            
        result = trashclaw.list_dir("testdir")
        assert "nested.txt" in result
        
    def test_search_files(self):
        # Create test files with content
        with open("search1.txt", "w") as f:
            f.write("This contains the target phrase\nAnd some other text")
        with open("search2.py", "w") as f:
            f.write("def func():\n    return 'target phrase here'")
        with open("search3.txt", "w") as f:
            f.write("No match in this file")
            
        result = trashclaw.search_files("target phrase", ".")
        
        assert "search1.txt" in result
        assert "search2.py" in result
        assert "search3.txt" not in result
        
    def test_find_files_by_name(self):
        # Create test file structure
        os.makedirs("nested/deep")
        with open("test.py", "w") as f:
            f.write("# test file")
        with open("nested/test.py", "w") as f:
            f.write("# another test")
        with open("nested/deep/test.py", "w") as f:
            f.write("# deep test")
        with open("other.txt", "w") as f:
            f.write("not a match")
            
        result = trashclaw.find_files("test.py", ".")
        
        # Should find all three test.py files
        lines = result.strip().split('\n')
        py_files = [line for line in lines if 'test.py' in line]
        assert len(py_files) == 3


class TestCommandExecution:
    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "command output"
        mock_run.return_value.stderr = ""
        
        result = trashclaw.run_command("echo hello")
        
        assert "command output" in result
        mock_run.assert_called_once()
        
    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "command failed"
        
        result = trashclaw.run_command("false")
        
        assert "Error running command" in result
        assert "command failed" in result


class TestGitOperations:
    @patch('subprocess.run')
    def test_git_status(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "On branch main\nnothing to commit"
        mock_run.return_value.stderr = ""
        
        result = trashclaw.git_status()
        
        assert "On branch main" in result
        mock_run.assert_called_with(['git', 'status'], capture_output=True, text=True)
        
    @patch('subprocess.run')
    def test_git_diff(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "diff --git a/file.txt b/file.txt\n+added line"
        mock_run.return_value.stderr = ""
        
        result = trashclaw.git_diff()
        
        assert "diff --git" in result
        assert "+added line" in result
        
    @patch('subprocess.run')
    def test_git_commit(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "[main abc123] Test commit"
        mock_run.return_value.stderr = ""
        
        result = trashclaw.git_commit("Test commit")
        
        assert "[main abc123] Test commit" in result
        mock_run.assert_called_with(['git', 'commit', '-m', 'Test commit'], capture_output=True, text=True)


class TestPatchOperations:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
    def teardown_method(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
        
    @patch('subprocess.run')
    def test_patch_file(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "patching file test.txt"
        mock_run.return_value.stderr = ""
        
        # Create a dummy patch file
        with open("test.patch", "w") as f:
            f.write("--- a/test.txt\n+++ b/test.txt\n@@ -1 +1 @@\n-old line\n+new line\n")
            
        result = trashclaw.patch_file("test.patch")
        
        assert "patching file" in result
        mock_run.assert_called_with(['patch', '-p1', '-i', 'test.patch'], capture_output=True, text=True)


class TestClipboard:
    @patch('subprocess.run')
    def test_clipboard_copy_linux(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        with patch('platform.system', return_value='Linux'):
            result = trashclaw.clipboard("test content")
            
        assert "Copied to clipboard" in result
        
    @patch('subprocess.run')
    def test_clipboard_copy_macos(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = ""
        
        with patch('platform.system', return_value='Darwin'):
            result = trashclaw.clipboard("test content")
            
        assert "Copied to clipboard" in result


class TestConfigSystem:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "config.json")
        
    def teardown_method(self):
        shutil.rmtree(self.temp_dir)
        
    def test_load_config_existing(self):
        config_data = {
            "achievements": {"file_operations": 5},
            "settings": {"theme": "dark"}
        }
        
        with open(self.config_file, "w") as f:
            json.dump(config_data, f)
            
        with patch.object(trashclaw, 'CONFIG_FILE', self.config_file):
            trashclaw._load_config()
            
        assert trashclaw.config["achievements"]["file_operations"] == 5
        assert trashclaw.config["settings"]["theme"] == "dark"
        
    def test_load_config_nonexistent(self):
        with patch.object(trashclaw, 'CONFIG_FILE', "/nonexistent/config.json"):
            trashclaw._load_config()
            
        # Should create default config
        assert "achievements" in trashclaw.config
        assert "undo_stack" in trashclaw.config
        
    def test_c_function_get_value(self):
        trashclaw.config = {
            "settings": {"editor": "vim"},
            "achievements": {"total": 10}
        }
        
        assert trashclaw._c("settings.editor") == "vim"
        assert trashclaw._c("achievements.total") == 10
        assert trashclaw._c("nonexistent.key") is None
        
    def test_c_function_set_value(self):
        trashclaw.config = {"settings": {}}
        
        trashclaw._c("settings.new_key", "new_value")
        assert trashclaw.config["settings"]["new_key"] == "new_value"


class TestAchievementTracking:
    def setup_method(self):
        trashclaw.config = {"achievements": {}}
        
    @patch('trashclaw._save_config')
    def test_track_tool_new_achievement(self, mock_save):
        trashclaw._track_tool("read_file")
        
        assert trashclaw.config["achievements"]["read_file"] == 1
        mock_save.assert_called_once()
        
    @patch('trashclaw._save_config')
    def test_track_tool_increment_existing(self, mock_save):
        trashclaw.config["achievements"]["write_file"] = 3
        
        trashclaw._track_tool("write_file")
        
        assert trashclaw.config["achievements"]["write_file"] == 4
        mock_save.assert_called_once()


class TestUndoSystem:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        trashclaw.config = {"undo_stack": []}
        
    def teardown_method(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
        
    @patch('trashclaw._save_config')
    def test_save_undo_file_operation(self, mock_save):
        # Create a test file
        with open("test.txt", "w") as f:
            f.write("original content")
            
        trashclaw._save_undo("write_file", "test.txt", "original content")
        
        assert len(trashclaw.config["undo_stack"]) == 1
        undo_entry = trashclaw.config["undo_stack"][0]
        assert undo_entry["action"] == "write_file"
        assert undo_entry["file"] == "test.txt"
        assert undo_entry["content"] == "original content"
        mock_save.assert_called_once()


class TestTabCompletion:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create test file structure
        os.makedirs("projects/myapp")
        with open("README.md", "w") as f:
            f.write("# Test")
        with open("app.py", "w") as f:
            f.write("print('hello')")
        with open("projects/myapp/main.py", "w") as f:
            f.write("# main file")
            
    def teardown_method(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
        
    def test_complete_filenames(self):
        completer = trashclaw.TrashClawCompleter()
        
        # Test completing files in current directory
        matches = completer.complete_filenames("app", 0)
        assert "app.py" in matches
        
        matches = completer.complete_filenames("READ", 0)
        assert "README.md" in matches
        
        # Test completing paths
        matches = completer.complete_filenames("projects/", 0)
        assert "projects/myapp/" in matches
        
    def test_complete_no_matches(self):
        completer = trashclaw.TrashClawCompleter()
        
        matches = completer.complete_filenames("nonexistent", 0)
        assert matches is None or matches == []


class TestIntegration:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        trashclaw.config = {"achievements": {}, "undo_stack": []}
        
    def teardown_method(self):
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
        
    @patch('trashclaw._save_config')
    def test_file_workflow_with_tracking(self, mock_save):
        # Write a file
        content = "Initial content"
        trashclaw.write_file("workflow.txt", content)
        
        # Read the file
        result = trashclaw.read_file("workflow.txt")
        assert result == content
        
        # Edit the file
        trashclaw.edit_file("workflow.txt", "Initial", "Modified")
        
        # Verify edit worked
        result = trashclaw.read_file("workflow.txt")
        assert "Modified content" in result
        assert "Initial content" not in result
        
        # Verify tracking was called
        assert mock_save.call_count >= 3  # At least one call for each operation
        
    def test_search_and_find_workflow(self):
        # Create multiple files with different content
        with open("doc1.txt", "w") as f:
            f.write("This document contains important information")
        with open("doc2.md", "w") as f:
            f.write("# Important Notes\nSome important details here")
        with open("code.py", "w") as f:
            f.write("def important_function():\n    pass")
        with open("other.txt", "w") as f:
            f.write("Nothing special here")
            
        # Search for content
        search_result = trashclaw.search_files("important", ".")
        assert "doc1.txt" in search_result
        assert "doc2.md" in search_result
        assert "code.py" in search_result
        assert "other.txt" not in search_result
        
        # Find specific files
        find_result = trashclaw.find_files("*.py", ".")
        assert "code.py" in find_result
        assert "doc1.txt" not in find_result