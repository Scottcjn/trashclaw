"""Tests for .trashclaw.toml / .trashclaw.json project config loading."""
import json
import os
import sys

import pytest

# Add parent dir to path so we can import from trashclaw
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestParseTomlMinimal:
    """Test the minimal TOML parser fallback."""

    def test_string_value(self, tmp_path):
        from trashclaw import _parse_toml_minimal
        f = tmp_path / "test.toml"
        f.write_text('model = "codestral"\n')
        result = _parse_toml_minimal(str(f))
        assert result["model"] == "codestral"

    def test_bool_true(self, tmp_path):
        from trashclaw import _parse_toml_minimal
        f = tmp_path / "test.toml"
        f.write_text('auto_shell = true\n')
        result = _parse_toml_minimal(str(f))
        assert result["auto_shell"] is True

    def test_bool_false(self, tmp_path):
        from trashclaw import _parse_toml_minimal
        f = tmp_path / "test.toml"
        f.write_text('auto_shell = false\n')
        result = _parse_toml_minimal(str(f))
        assert result["auto_shell"] is False

    def test_integer_value(self, tmp_path):
        from trashclaw import _parse_toml_minimal
        f = tmp_path / "test.toml"
        f.write_text('max_rounds = 25\n')
        result = _parse_toml_minimal(str(f))
        assert result["max_rounds"] == 25

    def test_string_array(self, tmp_path):
        from trashclaw import _parse_toml_minimal
        f = tmp_path / "test.toml"
        f.write_text('context_files = ["src/main.py", "README.md"]\n')
        result = _parse_toml_minimal(str(f))
        assert result["context_files"] == ["src/main.py", "README.md"]

    def test_empty_array(self, tmp_path):
        from trashclaw import _parse_toml_minimal
        f = tmp_path / "test.toml"
        f.write_text('context_files = []\n')
        result = _parse_toml_minimal(str(f))
        assert result["context_files"] == []

    def test_comments_ignored(self, tmp_path):
        from trashclaw import _parse_toml_minimal
        f = tmp_path / "test.toml"
        f.write_text('# This is a comment\nmodel = "gpt-4"\n# Another comment\n')
        result = _parse_toml_minimal(str(f))
        assert result == {"model": "gpt-4"}

    def test_empty_lines_ignored(self, tmp_path):
        from trashclaw import _parse_toml_minimal
        f = tmp_path / "test.toml"
        f.write_text('\n\nmodel = "test"\n\n')
        result = _parse_toml_minimal(str(f))
        assert result["model"] == "test"

    def test_full_config(self, tmp_path):
        from trashclaw import _parse_toml_minimal
        f = tmp_path / "test.toml"
        f.write_text(
            'context_files = ["src/main.py", "README.md"]\n'
            'system_prompt = "You are a Rust expert"\n'
            'model = "codestral"\n'
            'auto_shell = true\n'
        )
        result = _parse_toml_minimal(str(f))
        assert result["context_files"] == ["src/main.py", "README.md"]
        assert result["system_prompt"] == "You are a Rust expert"
        assert result["model"] == "codestral"
        assert result["auto_shell"] is True


class TestLoadConfig:
    """Test _load_config with TOML and JSON project configs."""

    def test_toml_config_loaded(self, tmp_path):
        from trashclaw import _load_config
        toml = tmp_path / ".trashclaw.toml"
        toml.write_text('model = "codestral"\nauto_shell = true\n')
        cfg = _load_config(str(tmp_path))
        assert cfg.get("model") == "codestral"
        assert cfg.get("auto_shell") is True

    def test_json_fallback(self, tmp_path):
        from trashclaw import _load_config
        jf = tmp_path / ".trashclaw.json"
        jf.write_text(json.dumps({
            "model": "gpt-4",
            "context_files": ["README.md"],
            "system_prompt": "Be helpful"
        }))
        cfg = _load_config(str(tmp_path))
        assert cfg.get("model") == "gpt-4"
        assert cfg.get("context_files") == ["README.md"]

    def test_toml_takes_precedence_over_json(self, tmp_path):
        from trashclaw import _load_config
        toml = tmp_path / ".trashclaw.toml"
        toml.write_text('model = "codestral"\n')
        jf = tmp_path / ".trashclaw.json"
        jf.write_text(json.dumps({"model": "gpt-4"}))
        cfg = _load_config(str(tmp_path))
        assert cfg.get("model") == "codestral"

    def test_no_config_returns_base(self, tmp_path):
        from trashclaw import _load_config
        cfg = _load_config(str(tmp_path))
        # Should return at least an empty-ish dict (base config or empty)
        assert isinstance(cfg, dict)


class TestContextFilesLoading:
    """Test that context_files from config are loaded into project instructions."""

    def test_context_files_loaded(self, tmp_path, monkeypatch):
        from trashclaw import _load_project_instructions
        # Create project files
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("def hello(): pass")
        (tmp_path / "README.md").write_text("# My Project")
        # Create config
        toml = tmp_path / ".trashclaw.toml"
        toml.write_text('context_files = ["src/main.py", "README.md"]\n')
        # Monkeypatch CWD
        monkeypatch.setattr("trashclaw.CWD", str(tmp_path))
        result = _load_project_instructions()
        assert "def hello(): pass" in result
        assert "# My Project" in result
        assert "Auto-loaded Context Files" in result

    def test_system_prompt_appended(self, tmp_path, monkeypatch):
        from trashclaw import _load_project_instructions
        toml = tmp_path / ".trashclaw.toml"
        toml.write_text('system_prompt = "You are a Rust expert"\n')
        monkeypatch.setattr("trashclaw.CWD", str(tmp_path))
        result = _load_project_instructions()
        assert "You are a Rust expert" in result
        assert "Project System Prompt" in result

    def test_missing_context_file_skipped(self, tmp_path, monkeypatch):
        from trashclaw import _load_project_instructions
        toml = tmp_path / ".trashclaw.toml"
        toml.write_text('context_files = ["nonexistent.py"]\n')
        monkeypatch.setattr("trashclaw.CWD", str(tmp_path))
        result = _load_project_instructions()
        # Should not crash, just skip
        assert "nonexistent.py" not in result
