"""Tests for word_count, base64, and hash tools.

Each tool has at least 3 tests as required by the bounty.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trashclaw


# ── tool_word_count ──

class TestWordCount:
    def test_basic_count(self):
        result = trashclaw.tool_word_count("hello world")
        assert "Words: 2" in result
        assert "Lines: 1" in result

    def test_multiline(self):
        result = trashclaw.tool_word_count("line one\nline two\nline three")
        assert "Lines: 3" in result
        assert "Words: 6" in result

    def test_empty_string(self):
        result = trashclaw.tool_word_count("")
        assert "Words: 0" in result
        assert "Characters (with spaces): 0" in result

    def test_character_counts(self):
        result = trashclaw.tool_word_count("a b c")
        assert "Characters (with spaces): 5" in result
        assert "Characters (no spaces): 3" in result


# ── tool_base64 ──

class TestBase64:
    def test_encode(self):
        result = trashclaw.tool_base64("encode", "hello world")
        assert "aGVsbG8gd29ybGQ=" in result

    def test_decode(self):
        result = trashclaw.tool_base64("decode", "aGVsbG8gd29ybGQ=")
        assert "hello world" in result

    def test_roundtrip(self):
        original = "TrashClaw is awesome!"
        encoded = trashclaw.tool_base64("encode", original)
        # Extract the encoded string
        b64_str = encoded.split("\n")[1]
        decoded = trashclaw.tool_base64("decode", b64_str)
        assert original in decoded

    def test_invalid_decode(self):
        result = trashclaw.tool_base64("decode", "!!!not-valid-base64!!!")
        assert "Error" in result


# ── tool_hash ──

class TestHash:
    def test_sha256_default(self):
        result = trashclaw.tool_hash("hello")
        assert "SHA256:" in result
        assert "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824" in result

    def test_sha1(self):
        result = trashclaw.tool_hash("hello", "sha1")
        assert "SHA1:" in result
        assert "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d" in result

    def test_md5(self):
        result = trashclaw.tool_hash("hello", "md5")
        assert "MD5:" in result
        assert "5d41402abc4b2a76b9719d911017c592" in result

    def test_unsupported_algorithm(self):
        result = trashclaw.tool_hash("hello", "sha512")
        assert "Error" in result
        assert "Unsupported" in result
