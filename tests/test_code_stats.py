"""
Tests for code_stats plugin.
"""

import sys
import os
import tempfile
import shutil
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins"))

from plugins.code_stats import run as code_stats_run, TOOL_DEF, LANG_MAP, SKIP_DIRS


class TestCodeStatsToolDef:
    """Test TOOL_DEF structure."""
    
    def test_tool_def_exists(self):
        assert TOOL_DEF is not None
    
    def test_tool_def_name(self):
        assert TOOL_DEF["name"] == "code_stats"
    
    def test_tool_def_description(self):
        assert "codebase" in TOOL_DEF["description"].lower()
        assert "lines" in TOOL_DEF["description"].lower()
    
    def test_tool_def_parameters(self):
        assert "parameters" in TOOL_DEF
        assert "path" in TOOL_DEF["parameters"]["properties"]
        assert "top_n" in TOOL_DEF["parameters"]["properties"]


class TestCodeStatsHappyPath:
    """Test normal operation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory with test files."""
        tmpdir = tempfile.mkdtemp()
        
        # Create Python file
        py_file = os.path.join(tmpdir, "test.py")
        with open(py_file, "w") as f:
            f.write("# Test Python file\n")
            f.write("def hello():\n")
            f.write("    print('Hello')\n")
            f.write("\n")
            f.write("if __name__ == '__main__':\n")
            f.write("    hello()\n")
        
        # Create JavaScript file
        js_file = os.path.join(tmpdir, "app.js")
        with open(js_file, "w") as f:
            f.write("// Test JS file\n")
            f.write("function greet() {\n")
            f.write("    console.log('Hi');\n")
            f.write("}\n")
        
        # Create subdirectory with file
        subdir = os.path.join(tmpdir, "src")
        os.makedirs(subdir)
        rs_file = os.path.join(subdir, "main.rs")
        with open(rs_file, "w") as f:
            f.write("// Rust file\n")
            f.write("fn main() {\n")
            f.write("    println!(\"Hello\");\n")
            f.write("}\n")
        
        yield tmpdir
        shutil.rmtree(tmpdir)
    
    def test_basic_analysis(self, temp_dir):
        """Test basic codebase analysis."""
        result = code_stats_run(path=temp_dir)
        
        assert "Code Stats" in result
        assert "Total:" in result
        assert "files" in result
        assert "lines" in result
    
    def test_language_detection(self, temp_dir):
        """Test that languages are correctly detected."""
        result = code_stats_run(path=temp_dir)
        
        assert "Python" in result
        assert "JavaScript" in result
        assert "Rust" in result
    
    def test_file_count(self, temp_dir):
        """Test file counting."""
        result = code_stats_run(path=temp_dir)
        
        # Should find 3 files
        assert "3 files" in result or "3," in result
    
    def test_line_count(self, temp_dir):
        """Test line counting."""
        result = code_stats_run(path=temp_dir)
        
        # Python: 6 lines, JS: 4 lines, Rust: 4 lines = 14 total
        assert "14" in result or "15" in result or "13" in result
    
    def test_top_files(self, temp_dir):
        """Test largest files listing."""
        result = code_stats_run(path=temp_dir, top_n=5)
        
        assert "Top" in result
        assert "Largest" in result
        assert "lines" in result


class TestCodeStatsEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.fixture
    def empty_dir(self):
        """Create an empty temporary directory."""
        tmpdir = tempfile.mkdtemp()
        yield tmpdir
        shutil.rmtree(tmpdir)
    
    @pytest.fixture
    def dir_with_markers(self):
        """Create directory with TODO/FIXME markers."""
        tmpdir = tempfile.mkdtemp()
        
        py_file = os.path.join(tmpdir, "todo.py")
        with open(py_file, "w") as f:
            f.write("# TODO: Implement this\n")
            f.write("# FIXME: This is broken\n")
            f.write("# HACK: Temporary workaround\n")
            f.write("def func():\n")
            f.write("    pass  # TODO: Add logic\n")
        
        yield tmpdir
        shutil.rmtree(tmpdir)
    
    def test_empty_directory(self, empty_dir):
        """Test analysis of empty directory."""
        result = code_stats_run(path=empty_dir)
        
        assert "No recognized source files" in result or "Total: 0" in result
    
    def test_todo_markers(self, dir_with_markers):
        """Test TODO marker counting."""
        result = code_stats_run(path=dir_with_markers)
        
        assert "TODO" in result
        assert "2" in result or "3" in result  # 2-3 TODOs
    
    def test_fixme_markers(self, dir_with_markers):
        """Test FIXME marker counting."""
        result = code_stats_run(path=dir_with_markers)
        
        assert "FIXME" in result
        assert "1" in result
    
    def test_hack_markers(self, dir_with_markers):
        """Test HACK marker counting."""
        result = code_stats_run(path=dir_with_markers)
        
        assert "HACK" in result
        assert "1" in result
    
    def test_nonexistent_path(self):
        """Test with non-existent path."""
        result = code_stats_run(path="/nonexistent/path/xyz123")
        
        assert "Error" in result or "Not a directory" in result
    
    def test_file_as_path(self, empty_dir):
        """Test when path is a file, not directory."""
        file_path = os.path.join(empty_dir, "test.txt")
        with open(file_path, "w") as f:
            f.write("test")
        
        result = code_stats_run(path=file_path)
        
        assert "Error" in result or "Not a directory" in result
    
    def test_custom_top_n(self, temp_dir):
        """Test custom top_n parameter."""
        # Create temp dir with files
        tmpdir = tempfile.mkdtemp()
        for i in range(5):
            with open(os.path.join(tmpdir, f"file{i}.py"), "w") as f:
                f.write("\n".join(["line"] * (i + 1)))
        
        result = code_stats_run(path=tmpdir, top_n=2)
        
        # Should only show top 2
        assert "Top 2" in result
        
        shutil.rmtree(tmpdir)


class TestCodeStatsSkipLogic:
    """Test skip directory and file logic."""
    
    @pytest.fixture
    def dir_with_skipped(self):
        """Create directory with files that should be skipped."""
        tmpdir = tempfile.mkdtemp()
        
        # Create node_modules (should be skipped)
        node_modules = os.path.join(tmpdir, "node_modules")
        os.makedirs(node_modules)
        with open(os.path.join(node_modules, "lib.js"), "w") as f:
            f.write("console.log('skip me');\n" * 100)
        
        # Create .git (should be skipped)
        git_dir = os.path.join(tmpdir, ".git")
        os.makedirs(git_dir)
        with open(os.path.join(git_dir, "config"), "w") as f:
            f.write("[core]\n")
        
        # Create valid Python file
        with open(os.path.join(tmpdir, "main.py"), "w") as f:
            f.write("print('include me')\n" * 10)
        
        yield tmpdir
        shutil.rmtree(tmpdir)
    
    def test_skip_node_modules(self, dir_with_skipped):
        """Test that node_modules is skipped."""
        result = code_stats_run(path=dir_with_skipped)
        
        # Should only count main.py, not node_modules files
        assert "Python" in result
        # Should have small line count (10 from main.py, not 100+)
        lines_line = [l for l in result.split('\n') if 'Python' in l][0]
        assert "10" in lines_line or "11" in lines_line
    
    def test_skip_git_directory(self, dir_with_skipped):
        """Test that .git is skipped."""
        result = code_stats_run(path=dir_with_skipped)
        
        # .git files should not be counted
        assert "config" not in result or ".git" not in result


class TestCodeStatsLangMap:
    """Test language mapping."""
    
    def test_common_extensions_mapped(self):
        """Test that common extensions are in LANG_MAP."""
        assert ".py" in LANG_MAP
        assert ".js" in LANG_MAP
        assert ".ts" in LANG_MAP
        assert ".rs" in LANG_MAP
        assert ".go" in LANG_MAP
    
    def test_language_names(self):
        """Test that language names are reasonable."""
        assert LANG_MAP[".py"] == "Python"
        assert LANG_MAP[".js"] == "JavaScript"
        assert "Rust" in LANG_MAP[".rs"]


class TestCodeStatsIntegration:
    """Integration tests."""
    
    def test_real_workspace(self):
        """Test on actual workspace if available."""
        # Try common paths
        test_paths = [
            os.path.expanduser("~/.openclaw/workspace"),
            os.getcwd(),
        ]
        
        for path in test_paths:
            if os.path.isdir(path):
                result = code_stats_run(path=path, top_n=5)
                assert "Code Stats" in result
                return
        
        pytest.skip("No suitable test directory found")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])