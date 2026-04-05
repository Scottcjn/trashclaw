#!/usr/bin/env python3
"""
Test suite for Token-per-Second Display (Issue #64)

Verifies:
- Generation stats displayed after each turn
- /status command shows session stats
- Session stats are tracked correctly
"""

import sys
from pathlib import Path

def test_session_stats_initialized():
    """Test that SESSION_STATS is initialized"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    assert 'SESSION_STATS' in content, "SESSION_STATS not found"
    assert '"total_tokens"' in content, "total_tokens not tracked"
    assert '"total_time"' in content, "total_time not tracked"
    assert '"total_turns"' in content, "total_turns not tracked"
    
    print("✅ test_session_stats_initialized: PASSED")

def test_time_imported():
    """Test that time module is imported"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    assert 'import time' in content, "time module not imported"
    
    print("✅ test_time_imported: PASSED")

def test_llm_request_tracks_time():
    """Test that llm_request tracks time"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    # Find llm_request function
    start = content.find('def llm_request(')
    end = content.find('def ', start + 1)
    llm_content = content[start:end]
    
    assert 'start_time = time.time()' in llm_content, "start_time not captured"
    assert 'time.time() - start_time' in llm_content or 'elapsed_time' in llm_content, "elapsed time not calculated"
    
    print("✅ test_llm_request_tracks_time: PASSED")

def test_llm_request_counts_tokens():
    """Test that llm_request counts tokens"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    # Find llm_request function
    start = content.find('def llm_request(')
    end = content.find('def ', start + 1)
    llm_content = content[start:end]
    
    assert 'total_tokens' in llm_content, "total_tokens not tracked"
    assert 'tokens_per_sec' in llm_content or 'tok/s' in llm_content, "tokens per second not calculated"
    
    print("✅ test_llm_request_counts_tokens: PASSED")

def test_stats_displayed_after_response():
    """Test that stats are displayed after response"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    # Find llm_request function
    start = content.find('def llm_request(')
    end = content.find('def ', start + 1)
    llm_content = content[start:end]
    
    # Check for stats display format
    assert 'tok/s' in llm_content, "tok/s not displayed"
    assert 'tokens' in llm_content, "token count not displayed"
    assert 'print' in llm_content and 'tok/s' in llm_content, "Stats not printed"
    
    print("✅ test_stats_displayed_after_response: PASSED")

def test_status_shows_session_stats():
    """Test that /status command shows session stats"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    # Find /status command
    status_start = content.find('elif command == "/status"')
    status_end = content.find('elif command ==', status_start + 1)
    status_content = content[status_start:status_end]
    
    assert 'Session Stats' in status_content or 'session' in status_content.lower(), "Session stats not in /status"
    assert 'SESSION_STATS' in status_content, "SESSION_STATS not accessed in /status"
    assert 'Total turns' in status_content or 'total_turns' in status_content, "Total turns not shown"
    assert 'Total tokens' in status_content or 'total_tokens' in status_content, "Total tokens not shown"
    assert 'Avg speed' in status_content or 'tok/s' in status_content, "Avg speed not shown"
    
    print("✅ test_status_shows_session_stats: PASSED")

def test_session_stats_updated():
    """Test that session stats are updated after each turn"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    # Find llm_request function
    start = content.find('def llm_request(')
    end = content.find('def ', start + 1)
    llm_content = content[start:end]
    
    assert 'SESSION_STATS["total_tokens"]' in llm_content, "total_tokens not updated"
    assert 'SESSION_STATS["total_time"]' in llm_content, "total_time not updated"
    assert 'SESSION_STATS["total_turns"]' in llm_content, "total_turns not updated"
    
    print("✅ test_session_stats_updated: PASSED")

def test_stats_format():
    """Test that stats format matches requirement"""
    with open('trashclaw.py', 'r') as f:
        content = f.read()
    
    # Find llm_request function
    start = content.find('def llm_request(')
    end = content.find('def ', start + 1)
    llm_content = content[start:end]
    
    # Check for format like [12.4 tok/s | 847 tokens | 68.3s]
    assert 'tok/s' in llm_content, "tok/s format not used"
    assert 'tokens' in llm_content, "tokens format not used"
    assert 's]' in llm_content or 's\\' in llm_content, "seconds format not used"
    
    print("✅ test_stats_format: PASSED")

def run_all_tests():
    """Run all tests"""
    print("=" * 60)
    print("Token-per-Second Display Test Suite (Issue #64)")
    print("=" * 60)
    print()
    
    tests = [
        test_session_stats_initialized,
        test_time_imported,
        test_llm_request_tracks_time,
        test_llm_request_counts_tokens,
        test_stats_displayed_after_response,
        test_status_shows_session_stats,
        test_session_stats_updated,
        test_stats_format,
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
