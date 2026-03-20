"""
Tests for the system_info plugin.

Covers: TOOL_DEF schema, run() output, detailed mode,
internal helpers, and cross-platform edge cases.
"""

import os
import sys
import platform
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "plugins"))

from plugins.system_info import run, TOOL_DEF, _get_cpu_info, _get_memory_info, _get_disk_info


# ── TOOL_DEF schema ──

class TestToolDef:
    def test_has_required_keys(self):
        assert {"name", "description", "parameters"} <= TOOL_DEF.keys()

    def test_name(self):
        assert TOOL_DEF["name"] == "system_info"

    def test_description_not_empty(self):
        assert len(TOOL_DEF["description"]) > 10

    def test_parameters_schema(self):
        params = TOOL_DEF["parameters"]
        assert params["type"] == "object"
        assert "detailed" in params["properties"]
        assert params["properties"]["detailed"]["type"] == "boolean"

    def test_detailed_not_required(self):
        assert "detailed" not in TOOL_DEF["parameters"].get("required", [])


# ── run() basic ──

class TestRunBasic:
    def test_returns_string(self):
        assert isinstance(run(), str)

    def test_not_empty(self):
        assert len(run()) > 0

    def test_contains_section_header(self):
        assert "System Information" in run()

    def test_contains_os(self):
        assert "OS:" in run()

    def test_contains_python(self):
        assert "Python:" in run()

    def test_contains_hostname(self):
        assert "Hostname:" in run()

    def test_contains_memory(self):
        assert "Memory:" in run()

    def test_contains_disk(self):
        assert "Disk:" in run()

    def test_os_matches_platform(self):
        assert platform.system() in run()

    def test_python_version_matches(self):
        assert platform.python_version() in run()

    def test_no_detailed_section_by_default(self):
        assert "Environment" not in run(detailed=False)


# ── run(detailed=True) ──

class TestRunDetailed:
    def test_contains_environment_section(self):
        assert "Environment" in run(detailed=True)

    def test_contains_cores(self):
        assert "Cores:" in run(detailed=True)

    def test_longer_than_basic(self):
        assert len(run(detailed=True)) > len(run(detailed=False))

    def test_extra_kwargs_ignored(self):
        result = run(detailed=False, unknown="ignored")
        assert isinstance(result, str)


# ── Internal helpers ──

class TestGetCpuInfo:
    def test_returns_string(self):
        assert isinstance(_get_cpu_info(), str)

    def test_not_empty(self):
        assert len(_get_cpu_info()) > 0

    def test_fallback_on_linux_error(self):
        with patch("builtins.open", side_effect=OSError):
            with patch("platform.system", return_value="Linux"):
                result = _get_cpu_info()
                assert isinstance(result, str)


class TestGetMemoryInfo:
    def test_returns_string(self):
        assert isinstance(_get_memory_info(), str)

    def test_contains_gb_or_unknown(self):
        result = _get_memory_info()
        assert "GB" in result or result == "Unknown"

    def test_fallback_on_linux_error(self):
        with patch("builtins.open", side_effect=OSError):
            with patch("platform.system", return_value="Linux"):
                result = _get_memory_info()
                assert result == "Unknown"


class TestGetDiskInfo:
    def test_returns_string(self):
        assert isinstance(_get_disk_info(), str)

    def test_contains_gb_or_unknown(self):
        result = _get_disk_info()
        assert "GB" in result or result == "Unknown"

    def test_fallback_on_error(self):
        with patch("shutil.disk_usage", side_effect=OSError):
            result = _get_disk_info()
            assert result == "Unknown"
