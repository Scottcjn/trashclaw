"""
Tests for system_info plugin (TrashClaw)
Author: Nexus
"""

import os
import sys
import platform
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "plugins"))
from system_info import run, TOOL_DEF, _get_cpu_info, _get_memory_info, _get_disk_info


# ── Tests TOOL_DEF ──

def test_tool_def_has_required_keys():
    assert "name" in TOOL_DEF
    assert "description" in TOOL_DEF
    assert "parameters" in TOOL_DEF

def test_tool_def_name():
    assert TOOL_DEF["name"] == "system_info"

def test_tool_def_description_not_empty():
    assert len(TOOL_DEF["description"]) > 0

def test_tool_def_parameters_schema():
    params = TOOL_DEF["parameters"]
    assert params["type"] == "object"
    assert "properties" in params
    assert "detailed" in params["properties"]


# ── Tests run() basic ──

def test_run_returns_string():
    result = run()
    assert isinstance(result, str)

def test_run_contains_system_info():
    result = run()
    assert "System Information" in result

def test_run_contains_os():
    result = run()
    assert "OS:" in result

def test_run_contains_python():
    result = run()
    assert "Python:" in result

def test_run_contains_hostname():
    result = run()
    assert "Hostname:" in result

def test_run_contains_memory():
    result = run()
    assert "Memory:" in result

def test_run_contains_disk():
    result = run()
    assert "Disk:" in result


# ── Tests run(detailed=True) ──

def test_run_detailed_contains_environment():
    result = run(detailed=True)
    assert "Environment" in result

def test_run_detailed_contains_cores():
    result = run(detailed=True)
    assert "Cores:" in result

def test_run_detailed_longer_than_basic():
    basic = run(detailed=False)
    detailed = run(detailed=True)
    assert len(detailed) > len(basic)


# ── Tests fonctions internes ──

def test_get_cpu_info_returns_string():
    result = _get_cpu_info()
    assert isinstance(result, str)
    assert len(result) > 0

def test_get_memory_info_returns_string():
    result = _get_memory_info()
    assert isinstance(result, str)

def test_get_memory_info_contains_gb_or_unknown():
    result = _get_memory_info()
    assert "GB" in result or result == "Unknown"

def test_get_disk_info_returns_string():
    result = _get_disk_info()
    assert isinstance(result, str)

def test_get_disk_info_contains_gb_or_unknown():
    result = _get_disk_info()
    assert "GB" in result or result == "Unknown"


# ── Tests edge cases ──

def test_run_with_unknown_kwargs():
    result = run(detailed=False, unknown_param="test")
    assert isinstance(result, str)

def test_run_os_matches_platform():
    result = run()
    current_os = platform.system()
    assert current_os in result

def test_run_python_version_matches():
    result = run()
    assert platform.python_version() in result
