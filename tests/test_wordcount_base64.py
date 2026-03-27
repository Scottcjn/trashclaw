"""Tests for word_count and base64 built-in tools.

Uses only pytest + stdlib. All file operations use tmp directories.
"""

import os
import sys
import pytest

# Add project root to path so we can import from trashclaw
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trashclaw


# ── Fixtures ──

@pytest.fixture(autouse=True)
def set_cwd(tmp_path, monkeypatch):
    """Set TrashClaw's CWD to a temp directory for all tests."""
    monkeypatch.setattr(trashclaw, "CWD", str(tmp_path))
    return tmp_path


@pytest.fixture
def sample_text_file(tmp_path):
    """Create a sample text file for testing."""
    f = tmp_path / "sample.txt"
    f.write_text("Hello World\nThis is a test file\nWith three lines\n")
    return f


@pytest.fixture
def empty_file(tmp_path):
    """Create an empty file for edge case testing."""
    f = tmp_path / "empty.txt"
    f.write_text("")
    return f


# ── tool_word_count ──

class TestWordCount:
    def test_count_text(self):
        """Test counting words in direct text."""
        result = trashclaw.tool_word_count(text="Hello World")
        assert "Words: 2" in result
        assert "Characters: 11" in result
        assert "Lines: 1" in result
    
    def test_count_multiline(self):
        """Test counting multiline text."""
        text = "Line one\nLine two\nLine three"
        result = trashclaw.tool_word_count(text=text)
        assert "Words: 6" in result
        assert "Lines: 3" in result
    
    def test_count_file(self, sample_text_file):
        """Test counting words in a file."""
        result = trashclaw.tool_word_count(path=str(sample_text_file))
        assert "Words: 9" in result
        assert "Characters: 47" in result
        assert "Lines: 3" in result
    
    def test_count_empty_file(self, empty_file):
        """Test counting words in an empty file."""
        result = trashclaw.tool_word_count(path=str(empty_file))
        assert "Words: 0" in result
        assert "Characters: 0" in result
        assert "Lines: 0" in result
    
    def test_count_nonexistent_file(self):
        """Test counting words in a nonexistent file."""
        result = trashclaw.tool_word_count(path="/nonexistent/file.txt")
        assert "Error" in result
        assert "not found" in result
    
    def test_count_no_params(self):
        """Test counting with no parameters."""
        result = trashclaw.tool_word_count()
        assert "Error" in result
        assert "Provide either" in result
    
    def test_count_with_punctuation(self):
        """Test counting text with punctuation."""
        result = trashclaw.tool_word_count(text="Hello, World! How are you?")
        assert "Words: 5" in result


# ── tool_base64 ──

class TestBase64:
    def test_encode_simple(self):
        """Test encoding simple text."""
        result = trashclaw.tool_base64(action="encode", text="hello")
        assert "Encoded: aGVsbG8=" in result
    
    def test_encode_chinese(self):
        """Test encoding Chinese characters."""
        result = trashclaw.tool_base64(action="encode", text="你好")
        assert "Encoded:" in result
        # Verify it can be decoded back
        import base64
        encoded = result.split(": ")[1]
        decoded = base64.b64decode(encoded).decode('utf-8')
        assert decoded == "你好"
    
    def test_decode_simple(self):
        """Test decoding simple text."""
        result = trashclaw.tool_base64(action="decode", text="aGVsbG8=")
        assert "Decoded: hello" in result
    
    def test_decode_file(self, tmp_path):
        """Test decoding from a file."""
        f = tmp_path / "encoded.txt"
        f.write_text("aGVsbG8gd29ybGQ=")
        result = trashclaw.tool_base64(action="decode", path=str(f))
        assert "Decoded: hello world" in result
    
    def test_encode_file(self, tmp_path):
        """Test encoding from a file."""
        f = tmp_path / "plain.txt"
        f.write_text("hello")
        result = trashclaw.tool_base64(action="encode", path=str(f))
        assert "Encoded: aGVsbG8=" in result
    
    def test_invalid_action(self):
        """Test with invalid action parameter."""
        result = trashclaw.tool_base64(action="invalid", text="hello")
        assert "Error" in result
        assert "encode" in result
        assert "decode" in result
    
    def test_no_params(self):
        """Test with no parameters."""
        result = trashclaw.tool_base64()
        assert "Error" in result
        assert "Provide either" in result
    
    def test_decode_invalid_base64(self):
        """Test decoding invalid base64."""
        result = trashclaw.tool_base64(action="decode", text="not-valid-base64!!!")
        assert "Error" in result
    
    def test_encode_empty_string(self):
        """Test encoding empty string."""
        result = trashclaw.tool_base64(action="encode", text="")
        assert "Encoded:" in result


# ── Integration Tests ──

class TestIntegration:
    def test_wordcount_then_base64(self, sample_text_file):
        """Test using word_count and base64 together."""
        # First count words
        count_result = trashclaw.tool_word_count(path=str(sample_text_file))
        assert "Words:" in count_result
        
        # Then encode the result
        encode_result = trashclaw.tool_base64(action="encode", text=count_result)
        assert "Encoded:" in encode_result
    
    def test_roundtrip(self):
        """Test encode then decode roundtrip."""
        original = "Test message 123!"
        encode_result = trashclaw.tool_base64(action="encode", text=original)
        encoded = encode_result.split(": ")[1]
        decode_result = trashclaw.tool_base64(action="decode", text=encoded)
        assert f"Decoded: {original}" in decode_result
