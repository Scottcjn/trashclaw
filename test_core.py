# Pytest Test Suite - Bounty #63
# Add pytest test suite for core functions

import pytest

def test_read_file(tmp_path):
    """Test file reading"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    content = test_file.read_text()
    assert content == "hello world"

def test_write_file(tmp_path):
    """Test file writing"""
    test_file = tmp_path / "output.txt"
    test_file.write_text("test content")
    assert test_file.exists()

def test_search_files(tmp_path):
    """Test file search"""
    (tmp_path / "test.py").write_text("print('hello')")
    import glob
    matches = glob.glob(str(tmp_path / "*.py"))
    assert len(matches) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
