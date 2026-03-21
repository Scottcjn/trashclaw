import pytest
import os
import subprocess
import sys

# Add parent directory to path so we can import trashclaw
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import trashclaw
from trashclaw import tool_git_status, tool_git_diff, tool_git_commit

@pytest.fixture
def repo_path(tmp_path, monkeypatch):
    # Create an actual git repo
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    
    # Initialize git
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    
    # Create initial commit
    test_file = repo_dir / "test.txt"
    test_file.write_text("initial content\n")
    subprocess.run(["git", "add", "test.txt"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo_dir, check=True)
    
    # Mock trashclaw's CWD
    monkeypatch.setattr(trashclaw, "CWD", str(repo_dir))
    
    return repo_dir

def test_git_status_clean(repo_path):
    result = tool_git_status()
    # the format is --short --branch: ## master
    assert "## master" in result or "## main" in result

def test_git_status_modified(repo_path):
    # Modify a file
    (repo_path / "test.txt").write_text("modified content\n")
    result = tool_git_status()
    assert "M test.txt" in result

def test_git_diff_unstaged(repo_path):
    # Modify a file
    (repo_path / "test.txt").write_text("modified content\n")
    result = tool_git_diff(staged=False)
    assert "diff --git a/test.txt b/test.txt" in result
    assert "-initial content" in result
    assert "+modified content" in result

def test_git_diff_staged(repo_path):
    # Modify and stage
    (repo_path / "test.txt").write_text("modified content\n")
    subprocess.run(["git", "add", "test.txt"], cwd=repo_path, check=True)
    
    result = tool_git_diff(staged=True)
    assert "diff --git a/test.txt b/test.txt" in result
    assert "-initial content" in result
    assert "+modified content" in result

def test_git_commit_success(repo_path):
    # Modify and stage
    (repo_path / "test.txt").write_text("modified content\n")
    subprocess.run(["git", "add", "test.txt"], cwd=repo_path, check=True)
    
    result = tool_git_commit("update test.txt")
    assert "update test.txt" in result
    
    # Verify commit happened
    log = subprocess.run(["git", "log", "-1", "--oneline"], cwd=repo_path, capture_output=True, text=True).stdout
    assert "update test.txt" in log
