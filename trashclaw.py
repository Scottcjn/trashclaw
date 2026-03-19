import os
import pytest
import tempfile

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def edit_file(path, old_text, new_text):
    content = read_file(path)
    content = content.replace(old_text, new_text)
    write_file(path, content)

# --- Pytest Test Suite ---

def test_read_file(tmp_path):
    test_file = tmp_path / "test_read.txt"
    test_file.write_text("test content", encoding="utf-8")
    assert read_file(str(test_file)) == "test content"

def test_write_file(tmp_path):
    test_file = tmp_path / "test_write.txt"
    write_file(str(test_file), "new content")
    assert test_file.read_text(encoding="utf-8") == "new content"

def test_edit_file(tmp_path):
    test_file = tmp_path / "test_edit.txt"
    test_file.write_text("hello world", encoding="utf-8")
    edit_file(str(test_file), "world", "pytest")
    assert test_file.read_text(encoding="utf-8") == "hello pytest"
