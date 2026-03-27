"""
Tests for hash, base64, and json_format plugins.
"""

import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins"))

from plugins.hash import run as hash_run, TOOL_DEF as HASH_DEF
from plugins.base64_tool import run as b64_run, TOOL_DEF as B64_DEF
from plugins.json_format import run as json_run, TOOL_DEF as JSON_DEF


# ── hash ──

class TestHash:
    def test_tool_def(self):
        assert HASH_DEF["name"] == "hash"
        assert "algorithm" in HASH_DEF["parameters"]["properties"]

    def test_sha256(self):
        result = hash_run(text="hello", algorithm="sha256")
        assert "2cf24dba" in result

    def test_md5(self):
        result = hash_run(text="hello", algorithm="md5")
        assert "5d41402a" in result

    def test_sha1(self):
        result = hash_run(text="hello", algorithm="sha1")
        assert isinstance(result, str)
        assert "SHA1" in result

    def test_sha512(self):
        result = hash_run(text="hello", algorithm="sha512")
        assert isinstance(result, str)
        assert "SHA512" in result

    def test_default_algorithm_is_sha256(self):
        result = hash_run(text="hello")
        assert "SHA256" in result

    def test_unknown_algorithm(self):
        result = hash_run(text="hello", algorithm="fakehash")
        assert "Unsupported" in result

    def test_no_input(self):
        result = hash_run()
        assert "Error" in result

    def test_file_not_found(self):
        result = hash_run(file="/nonexistent/file.txt")
        assert "Error" in result

    def test_file_hash(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = hash_run(file=str(f))
        assert "SHA256" in result
        assert len(result) > 10


# ── base64 ──

class TestBase64:
    def test_tool_def(self):
        assert B64_DEF["name"] == "base64"
        assert "action" in B64_DEF["parameters"]["properties"]

    def test_encode(self):
        result = b64_run(text="Hello", action="encode")
        assert "SGVsbG8=" in result

    def test_decode(self):
        result = b64_run(text="SGVsbG8=", action="decode")
        assert "Hello" in result

    def test_roundtrip(self):
        original = "Hello Nexus!"
        encoded = b64_run(text=original, action="encode").split("\n")[1]
        decoded = b64_run(text=encoded, action="decode").split("\n")[1]
        assert decoded == original

    def test_default_action_is_encode(self):
        result = b64_run(text="test")
        assert "encoded" in result

    def test_empty_text(self):
        result = b64_run(text="")
        assert "Error" in result

    def test_unknown_action(self):
        result = b64_run(text="hello", action="compress")
        assert "Unknown" in result

    def test_invalid_base64_decode(self):
        result = b64_run(text="not-valid-base64!!!", action="decode")
        assert "Error" in result


# ── json_format ──

class TestJsonFormat:
    SAMPLE = '{"name": "Nexus", "version": 1, "active": true}'

    def test_tool_def(self):
        assert JSON_DEF["name"] == "json_format"
        assert "action" in JSON_DEF["parameters"]["properties"]

    def test_pretty(self):
        result = json_run(text=self.SAMPLE, action="pretty")
        assert '"name"' in result
        assert "\n" in result

    def test_pretty_is_valid_json(self):
        result = json_run(text=self.SAMPLE, action="pretty")
        parsed = json.loads(result)
        assert parsed["name"] == "Nexus"

    def test_minify(self):
        result = json_run(text=self.SAMPLE, action="minify")
        assert "\n" not in result
        assert " " not in result

    def test_validate(self):
        result = json_run(text=self.SAMPLE, action="validate")
        assert "Valid" in result
        assert "3 keys" in result

    def test_keys(self):
        result = json_run(text=self.SAMPLE, action="keys")
        assert "name" in result
        assert "version" in result

    def test_invalid_json(self):
        result = json_run(text="{bad json}")
        assert "Invalid" in result

    def test_empty_text(self):
        result = json_run(text="")
        assert "Error" in result

    def test_unknown_action(self):
        result = json_run(text=self.SAMPLE, action="explode")
        assert "Unknown" in result

    def test_array_validate(self):
        result = json_run(text="[1,2,3]", action="validate")
        assert "array" in result
        assert "3" in result

    def test_custom_indent(self):
        result = json_run(text=self.SAMPLE, action="pretty", indent=4)
        assert "    " in result

class TestUntestedTool(unittest.TestCase):
    def test_untested_tool(self):
        # Implement test cases here
        pass

if __name__ == '__main__':
    unittest.main()
