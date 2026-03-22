"""
System Info Plugin for TrashClaw

Provides detailed system and hardware information.
Cross-platform support for Windows, macOS, and Linux.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import platform
import os
import sys
from datetime import datetime

TOOL_DEF = {
    "name": "system_info",
    "description": "Get detailed system and hardware information including OS, CPU, memory, and environment details.",
    "parameters": {
        "type": "object",
        "properties": {
            "detailed": {
                "type": "boolean",
                "description": "Include detailed information (default: false)"
            }
        },
        "required": []
    }
}


def _get_cpu_info() -> str:
    """Get CPU information based on platform."""
    system = platform.system()

    if system == "Darwin":  # macOS
        import subprocess
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass

    elif system == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line.lower():
                        return line.split(":")[1].strip()
        except Exception:
            pass

    elif system == "Windows":
        import subprocess
        try:
            result = subprocess.run(
                ["wmic", "cpu", "get", "name"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    return lines[1].strip()
        except Exception:
            pass

    return platform.processor() or "Unknown CPU"


def _get_memory_info() -> str:
    """Get memory information based on platform."""
    system = platform.system()

    if system == "Darwin":  # macOS
        import subprocess
        try:
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                total_bytes = int(result.stdout.strip())
                return f"{total_bytes / (1024**3):.1f} GB"
        except Exception:
            pass

    elif system == "Linux":
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return f"{kb / (1024**2):.1f} GB"
        except Exception:
            pass

    elif system == "Windows":
        import subprocess
        try:
            result = subprocess.run(
                ["wmic", "OS", "get", "TotalVisibleMemorySize"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    kb = int(lines[1].strip())
                    return f"{kb / (1024**2):.1f} GB"
        except Exception:
            pass

    return "Unknown"


def _get_disk_info() -> str:
    """Get disk usage for root/home drive."""
    try:
        import shutil
        # Use CWD or root depending on platform
        path = "C:\\" if platform.system() == "Windows" else "/"
        total, used, free = shutil.disk_usage(path)
        return f"{free / (1024**3):.1f} GB free of {total / (1024**3):.1f} GB"
    except Exception:
        return "Unknown"


def run(detailed: bool = False, **kwargs) -> str:
    """
    Get system and hardware information.

    Args:
        detailed: Include extra details like environment variables

    Returns:
        Formatted system information string
    """
    info = []
    info.append("=== System Information ===\n")

    # Basic platform info
    info.append(f"OS: {platform.system()} {platform.release()}")
    info.append(f"Version: {platform.version()}")
    info.append(f"Architecture: {platform.machine()}")
    info.append(f"Processor: {_get_cpu_info()}")
    info.append(f"Memory: {_get_memory_info()}")
    info.append(f"Disk: {_get_disk_info()}")

    # Python info
    info.append(f"\nPython: {platform.python_version()}")
    info.append(f"Python Path: {sys.executable}")

    # Hostname
    info.append(f"\nHostname: {platform.node()}")

    # Current user
    try:
        import getpass
        info.append(f"User: {getpass.getuser()}")
    except Exception:
        pass

    # Boot time
    if platform.system() != "Windows":
        try:
            import subprocess
            result = subprocess.run(
                ["uptime", "-s"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                info.append(f"Boot Time: {result.stdout.strip()}")
        except Exception:
            pass

    if detailed:
        info.append("\n=== Environment ===")
        env_vars = ["PATH", "HOME", "USER", "SHELL", "EDITOR"]
        for var in env_vars:
            val = os.environ.get(var)
            if val:
                info.append(f"{var}: {val[:100]}{'...' if len(val) > 100 else ''}")

        info.append("\n=== CPU Cores ===")
        try:
            import multiprocessing
            info.append(f"Cores: {multiprocessing.cpu_count()}")
        except Exception:
            pass

    return "\n".join(info)
