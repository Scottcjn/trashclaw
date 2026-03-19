import os
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def test_file(temp_dir):
    """Create a test file with sample content."""
    file_path = temp_dir / "test.txt"
    content = "Hello, World!\nThis is a test file.\nLine 3"
    file_path.write_text(content)
    return file_path


@pytest.fixture
def empty_file(temp_dir):
    """Create an empty test file."""
    file_path = temp_dir / "empty.txt"
    file_path.touch()
    return file_path


@pytest.fixture
def nested_dirs(temp_dir):
    """Create nested directory structure with files."""
    dirs = {
        'src': temp_dir / 'src',
        'tests': temp_dir / 'tests',
        'docs': temp_dir / 'docs'
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir()
    
    # Create some test files
    (dirs['src'] / 'main.py').write_text('print("hello")')
    (dirs['src'] / 'utils.py').write_text('def helper(): pass')
    (dirs['tests'] / 'test_main.py').write_text('import unittest')
    (dirs['docs'] / 'README.md').write_text('# Documentation')
    
    return dirs


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for command testing."""
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "command output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_clipboard():
    """Mock clipboard operations."""
    with patch('pyperclip.copy') as mock_copy, \
         patch('pyperclip.paste') as mock_paste:
        mock_paste.return_value = "clipboard content"
        yield {'copy': mock_copy, 'paste': mock_paste}


@pytest.fixture
def git_repo(temp_dir):
    """Create a temporary git repository."""
    repo_path = temp_dir / 'git_repo'
    repo_path.mkdir()
    
    # Initialize git repo
    subprocess.run(['git', 'init'], cwd=repo_path, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo_path, capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo_path, capture_output=True)
    
    # Create initial commit
    test_file = repo_path / 'initial.txt'
    test_file.write_text('initial content')
    subprocess.run(['git', 'add', '.'], cwd=repo_path, capture_output=True)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=repo_path, capture_output=True)
    
    return repo_path


@pytest.fixture
def config_file(temp_dir):
    """Create a test config file."""
    config_path = temp_dir / 'config.json'
    config_content = {
        "max_file_size": 1000000,
        "excluded_dirs": [".git", "__pycache__"],
        "achievements": []
    }
    import json
    config_path.write_text(json.dumps(config_content, indent=2))
    return config_path


@pytest.fixture
def mock_config():
    """Mock config dictionary for testing."""
    return {
        "max_file_size": 1000000,
        "excluded_dirs": [".git", "__pycache__", "node_modules"],
        "achievements": [],
        "undo_history": []
    }


@pytest.fixture
def sample_patch():
    """Sample patch content for testing."""
    return """--- a/test.txt
+++ b/test.txt
@@ -1,3 +1,3 @@
 Hello, World!
-This is a test file.
+This is a modified test file.
 Line 3"""


@pytest.fixture(autouse=True)
def reset_global_state():
    """Reset any global state before each test."""
    yield
    # Clean up any global variables that might persist between tests


@pytest.fixture
def capture_output(monkeypatch):
    """Capture print output for testing."""
    outputs = []
    
    def mock_print(*args, **kwargs):
        outputs.append(' '.join(str(arg) for arg in args))
    
    monkeypatch.setattr('builtins.print', mock_print)
    return outputs