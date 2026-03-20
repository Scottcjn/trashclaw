import os
import sys
import shutil
import pytest
import json
from trashclaw import (
    tool_read_file, tool_write_file, tool_edit_file, tool_patch_file,
    tool_list_dir, tool_find_files, tool_search_files, tool_run_command,
    _load_config, _CFG, CWD
)

@pytest.fixture
def test_env(tmp_path):
    """Setup a temporary workspace for file operations."""
    d = tmp_path / "workspace"
    d.mkdir()
    # Mock global CWD or just pass absolute paths
    return d

def test_write_and_read_file(test_env):
    path = str(test_env / "hello.txt")
    content = "Hello, TrashClaw!\nLine 2"
    
    # Test write
    res = tool_write_file(path, content)
    assert "Wrote" in res
    assert os.path.exists(path)
    
    # Test read
    read_res = tool_read_file(path)
    assert "Hello, TrashClaw!" in read_res
    assert "Line 2" in read_res
    assert "1" in read_res # Line numbering

def test_edit_file(test_env):
    path = str(test_env / "config.py")
    content = "VERSION = '0.1.0'\nDEBUG = False"
    tool_write_file(path, content)
    
    # Test precise edit
    res = tool_edit_file(path, "VERSION = '0.1.0'", "VERSION = '0.2.0'")
    assert "Edited" in res
    
    with open(path, 'r') as f:
        new_content = f.read()
    assert "VERSION = '0.2.0'" in new_content
    assert "DEBUG = False" in new_content

def test_patch_file(test_env):
    path = str(test_env / "main.py")
    content = "def start():\n    print('Starting')\n\nif __name__ == '__main__':\n    start()"
    tool_write_file(path, content)
    
    patch = """@@ -1,5 +1,6 @@
 def start():
+    print('Initializing...')
     print('Starting')
 
 if __name__ == '__main__':"""
    
    res = tool_patch_file(path, patch)
    assert "Patched" in res
    
    with open(path, 'r') as f:
        patched = f.read()
    assert "Initializing..." in patched
    assert "Starting" in patched

def test_list_dir(test_env):
    (test_env / "subdir").mkdir()
    tool_write_file(str(test_env / "file1.txt"), "test")
    
    res = tool_list_dir(str(test_env))
    assert "subdir/" in res
    assert "file1.txt" in res

def test_find_files(test_env):
    (test_env / "src").mkdir()
    tool_write_file(str(test_env / "src/main.py"), "test")
    tool_write_file(str(test_env / "README.md"), "test")
    
    res = tool_find_files("**/*.py", str(test_env))
    assert "src/main.py" in res
    assert "README.md" not in res

def test_search_files(test_env):
    tool_write_file(str(test_env / "data.txt"), "Secret: 12345\nOther stuff")
    
    res = tool_search_files(r"Secret: \d+", str(test_env))
    assert "data.txt:1: Secret: 12345" in res

def test_run_command_basic():
    # run_command respects global APPROVE_SHELL, usually off in tests or we need to mock it
    # For now, test a simple echo that usually doesn't prompt or mock if needed
    import trashclaw
    trashclaw.APPROVE_SHELL = False
    
    res = tool_run_command("echo 'Hello World'")
    assert "Hello World" in res

def test_load_config_project(test_env):
    toml_path = test_env / ".trashclaw.toml"
    with open(toml_path, "w") as f:
        f.write("model = \"test-model-abc\"\nauto_shell = true\n")
    
    cfg = _load_config(str(test_env))
    assert cfg.get("model") == "test-model-abc"
    assert cfg.get("auto_shell") == True
