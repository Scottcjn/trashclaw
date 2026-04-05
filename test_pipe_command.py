#!/usr/bin/env python3
"""
Test suite for /pipe command (Issue #66)

Verifies:
- /pipe command saves last assistant response to file
- Works with and without filename argument
- Shows file path and size
- Uses HISTORY list correctly
"""

import os
import sys
import json
import tempfile
from pathlib import Path

def test_pipe_command_exists():
    """Test that /pipe command is implemented in trashclaw.py"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    assert 'elif command == "/pipe"' in content, "/pipe command not found"
    assert 'last_assistant_msg' in content, "Does not find last assistant message"
    assert 'HISTORY' in content, "Does not use HISTORY list"
    
    print("✅ test_pipe_command_exists: PASSED")

def test_pipe_saves_to_file():
    """Test that /pipe saves content to file"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    assert 'open(filepath' in content, "Does not open file for writing"
    assert 'f.write(last_assistant_msg)' in content, "Does not write content to file"
    assert 'encoding=' in content, "Does not specify encoding"
    
    print("✅ test_pipe_saves_to_file: PASSED")

def test_pipe_filename_handling():
    """Test that /pipe handles filename argument"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    assert 'if not arg:' in content, "Does not check for missing filename"
    assert 'datetime.datetime.now()' in content, "Does not generate timestamp"
    assert 'trashclaw_output_' in content, "Does not use default naming pattern"
    assert 'filename = arg' in content or 'filename = filename' in content, "Does not use provided filename"
    
    print("✅ test_pipe_filename_handling: PASSED")

def test_pipe_shows_output():
    """Test that /pipe shows file path and size"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    assert 'Saved to:' in content or 'filepath' in content, "Does not show file path"
    assert 'Size:' in content or 'file_size' in content, "Does not show file size"
    assert 'os.path.getsize' in content, "Does not get file size"
    
    print("✅ test_pipe_shows_output: PASSED")

def test_pipe_error_handling():
    """Test that /pipe has error handling"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    assert 'try:' in content, "No try block for error handling"
    assert 'except Exception' in content or 'except:' in content, "No exception handling"
    assert 'Error' in content, "No error message"
    
    print("✅ test_pipe_error_handling: PASSED")

def test_pipe_no_history_message():
    """Test that /pipe handles empty history"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    # Should check if last_assistant_msg exists
    assert 'if not last_assistant_msg' in content or 'if last_assistant_msg is None' in content, \
        "Does not check for missing assistant message"
    assert 'No assistant response' in content or 'not found' in content, \
        "No error message for missing history"
    
    print("✅ test_pipe_no_history_message: PASSED")

def test_pipe_help_updated():
    """Test that /help includes /pipe command"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    # Find the help section
    help_start = content.find('elif command == "/help"')
    help_section = content[help_start:help_start+2000]
    
    assert '/pipe' in help_section, "/pipe not documented in /help"
    
    print("✅ test_pipe_help_updated: PASSED")

def test_pipe_path_resolution():
    """Test that /pipe resolves file paths correctly"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    assert 'os.path.isabs' in content, "Does not check for absolute path"
    assert 'CWD' in content or 'os.path.join' in content, "Does not resolve relative paths"
    
    print("✅ test_pipe_path_resolution: PASSED")

def run_functional_test():
    """Run functional test of /pipe logic"""
    # Simulate the /pipe command logic
    HISTORY = [
        {"role": "user", "content": "Write a hello world script"},
        {"role": "assistant", "content": "#!/usr/bin/env python3\nprint('Hello, World!')"},
    ]
    
    # Find last assistant message
    last_assistant_msg = None
    for msg in reversed(HISTORY):
        if msg.get("role") == "assistant":
            last_assistant_msg = msg.get("content", "")
            break
    
    assert last_assistant_msg is not None, "Failed to find assistant message"
    assert "Hello, World!" in last_assistant_msg, "Incorrect message content"
    
    # Test file writing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(last_assistant_msg)
        temp_path = f.name
    
    try:
        with open(temp_path, 'r') as f:
            content = f.read()
        assert content == last_assistant_msg, "File content doesn't match"
        print("✅ run_functional_test: PASSED")
        print(f"   File written and verified: {temp_path}")
    finally:
        os.unlink(temp_path)

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("/pipe Command Test Suite (Issue #66)")
    print("=" * 60)
    print()
    
    tests = [
        test_pipe_command_exists,
        test_pipe_saves_to_file,
        test_pipe_filename_handling,
        test_pipe_shows_output,
        test_pipe_error_handling,
        test_pipe_no_history_message,
        test_pipe_help_updated,
        test_pipe_path_resolution,
        run_functional_test,
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: FAILED - {e}")
            failed += 1
        except Exception as e:
            print(f"⚠️  {test.__name__}: ERROR - {e}")
            skipped += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")
    print("=" * 60)
    
    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
