"""Tests for the env_audit plugin."""

import os
import stat
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
from env_audit import run, _scan_file_contents


# ── Basic operation ──

def test_clean_dir(tmp_path):
    """A directory with no issues should report clean."""
    (tmp_path / "readme.txt").write_text("hello")
    result = run(path=str(tmp_path))
    assert "No issues" in result or "clean" in result.lower()


def test_nonexistent_dir():
    result = run(path="/tmp/nonexistent_trashclaw_env_audit_test")
    assert "Error" in result


# ── .env detection ──

def test_env_file_detected(tmp_path):
    """A .env file should be flagged."""
    (tmp_path / ".env").write_text("SECRET_KEY=abc123def456ghi789")
    result = run(path=str(tmp_path))
    assert ".env" in result
    # Should find at least a warning about the .env or a secret inside it
    assert "WARNING" in result or "CRITICAL" in result or "secret" in result.lower()


def test_env_production_detected(tmp_path):
    (tmp_path / ".env.production").write_text("DB_PASSWORD=supersecret123")
    result = run(path=str(tmp_path))
    assert ".env.production" in result


# ── Secret pattern detection ──

def test_api_key_in_source(tmp_path):
    f = tmp_path / "config.py"
    f.write_text('API_KEY = "sk-abc123def456ghi789jkl012mno345"\n')
    result = run(path=str(tmp_path), deep=True)
    assert "secret" in result.lower() or "WARNING" in result


def test_github_pat_detected(tmp_path):
    f = tmp_path / "deploy.sh"
    f.write_text('TOKEN=ghp_abcdefghijklmnopqrstuvwxyz1234567890\n')
    result = run(path=str(tmp_path), deep=True)
    assert "GitHub" in result or "WARNING" in result


def test_private_key_block_detected(tmp_path):
    f = tmp_path / "certs.py"
    f.write_text('KEY = """-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n"""\n')
    result = run(path=str(tmp_path), deep=True)
    assert "Private key" in result or "WARNING" in result


def test_bearer_token_detected(tmp_path):
    f = tmp_path / "api.js"
    f.write_text('const headers = { "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc" };\n')
    result = run(path=str(tmp_path), deep=True)
    assert "Bearer" in result or "WARNING" in result


# ── Key file permissions ──

def test_world_readable_key(tmp_path):
    """A .pem file with world-readable permissions should be flagged."""
    keyfile = tmp_path / "server.pem"
    keyfile.write_text("fake key content")
    os.chmod(str(keyfile), 0o644)  # world-readable
    result = run(path=str(tmp_path), deep=False)
    assert "world-readable" in result or "WARNING" in result or "permissions" in result.lower()


# ── Deep scan disabled ──

def test_no_deep_scan(tmp_path):
    """With deep=False, file contents should not be scanned for secrets."""
    f = tmp_path / "config.py"
    f.write_text('API_KEY = "sk-abc123def456ghi789jkl012mno345"\n')
    result = run(path=str(tmp_path), deep=False)
    # Should NOT find the API key since content scanning is off
    # (unless the file is named as a sensitive file)
    assert "secret_in_source" not in result


# ── _scan_file_contents helper ──

def test_scan_file_contents_finds_secrets(tmp_path):
    f = tmp_path / "test.py"
    f.write_text('password = "MyS3cretP@ss!"\napi_key: AKIAIOSFODNN7EXAMPLE1234\n')
    findings = _scan_file_contents(str(f))
    assert len(findings) >= 1
    # At least one finding should mention password or API key
    pattern_names = [name for _, name, _ in findings]
    assert any("Password" in n or "API" in n for n in pattern_names)


def test_scan_empty_file(tmp_path):
    f = tmp_path / "empty.py"
    f.write_text("")
    findings = _scan_file_contents(str(f))
    assert findings == []


def test_scan_nonexistent():
    findings = _scan_file_contents("/tmp/nonexistent_trashclaw_test_file")
    assert findings == []
