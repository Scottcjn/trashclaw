#!/usr/bin/env python3
"""
TrashClaw v0.2 — Local Tool-Use Agent
======================================
A general-purpose agent powered by a local LLM. Reads files, writes files,
runs commands, searches codebases, fetches URLs, processes data — whatever
you need. OpenClaw-style tool-use loop with zero external dependencies.

Pure Python stdlib. Python 3.7+. Works with any OpenAI-compatible server.
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
import re
import glob as globlib
import difflib
import traceback
import base64
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Windows compatibility: use pyreadline3 or skip readline
if sys.platform == "win32":
    try:
        import pyreadline3 as readline
    except ImportError:
        # readline not available on Windows without pyreadline3
        # Create a minimal stub to avoid errors
        class _StubReadline:
            def parse_and_bind(self, *args): pass
        readline = _StubReadline()
else:
    import readline

# ── Config ──
LLAMA_URL = os.environ.get("TRASHCLAW_URL", "http://localhost:8080")
MODEL_NAME = os.environ.get("TRASHCLAW_MODEL", "local")
MAX_TOOL_ROUNDS = int(os.environ.get("TRASHCLAW_MAX_ROUNDS", "15"))
MAX_OUTPUT_CHARS = 8000
APPROVE_SHELL = os.environ.get("TRASHCLAW_AUTO_SHELL", "0") != "1"

# ── Image Helper ──
def load_image_to_base64(image_path: str) -> Optional[str]:
    """Load an image file and return base64 data URI."""
    if not os.path.exists(image_path):
        return None
    
    # Detect image type
    ext = os.path.splitext(image_path)[1].lower()
    mime_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }
    mime_type = mime_map.get(ext, 'image/png')
    
    try:
        with open(image_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        return f"data:{mime_type};base64,{image_data}"
    except Exception as e:
        print(f"\033[31m[ERROR]\033[0m Failed to load image: {e}")
        return None
HISTORY: List[Dict] = []
CWD = os.getcwd()
IMAGE_PATH: Optional[str] = None  # Optional image path for vision models

# ── Tool Definitions ──

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file. Use this to examine code, configs, or any text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative file path to read"},
                    "offset": {"type": "integer", "description": "Line number to start reading from (1-based). Optional."},
                    "limit": {"type": "integer", "description": "Max number of lines to read. Optional."}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with new content. Use for creating new files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write to"},
                    "content": {"type": "string", "description": "Full content to write"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace a specific string in a file. The old_string must match exactly. Use for targeted edits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_string": {"type": "string", "description": "Exact string to find and replace"},
                    "new_string": {"type": "string", "description": "Replacement string"}
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command and return its output. Use for builds, tests, git, system info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Search file contents using regex pattern. Like grep -rn.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "Directory or file to search in (default: current dir)"},
                    "glob_filter": {"type": "string", "description": "File glob pattern like '*.py' or '*.js'"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files matching a glob pattern. Like find or ls.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern like '**/*.py' or 'src/**/*.ts'"},
                    "path": {"type": "string", "description": "Base directory to search from (default: current dir)"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories in a path. Shows file sizes and types.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path to list (default: current dir)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch a URL and return its readable text content. Strips HTML tags. Good for browsing the web.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch (e.g. https://example.com)"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "think",
            "description": "Use this tool to think through a problem step by step before acting. No side effects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {"type": "string", "description": "Your reasoning or plan"}
                },
                "required": ["thought"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "view_image",
            "description": "Read an image file and return it as base64-encoded data for vision models. Supports PNG, JPG, GIF, WebP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Image file path to read"},
                    "resize_max": {"type": "integer", "description": "Max dimension for resizing (optional, reduces token usage)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot and return as base64-encoded image. Uses system screenshot tools (scrot/import/screencapture).",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {"type": "string", "description": "Screen region 'WIDTHxHEIGHT+X+Y' (optional, default: full screen)"}
                },
                "required": []
            }
        }
    }
]

TOOL_NAMES = {t["function"]["name"] for t in TOOLS}

# ── Tool Implementations ──

def _resolve_path(path: str) -> str:
    """Resolve a path relative to CWD."""
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(CWD, path)
    return os.path.normpath(path)


def tool_read_file(path: str, offset: int = None, limit: int = None) -> str:
    path = _resolve_path(path)
    try:
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except PermissionError:
        return f"Error: Permission denied: {path}"
    except Exception as e:
        return f"Error reading {path}: {e}"

    total = len(lines)
    start = max(0, (offset or 1) - 1)
    end = start + limit if limit else total

    numbered = []
    for i, line in enumerate(lines[start:end], start=start + 1):
        numbered.append(f"{i:>5}\t{line.rstrip()}")

    result = "\n".join(numbered)
    if len(result) > MAX_OUTPUT_CHARS:
        result = result[:MAX_OUTPUT_CHARS] + f"\n... [truncated, {total} lines total]"
    return result


def tool_write_file(path: str, content: str) -> str:
    path = _resolve_path(path)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        lines = content.count("\n") + 1
        return f"Wrote {len(content)} bytes ({lines} lines) to {path}"
    except Exception as e:
        return f"Error writing {path}: {e}"


def tool_edit_file(path: str, old_string: str, new_string: str) -> str:
    path = _resolve_path(path)
    try:
        with open(path, "r") as f:
            content = f.read()
    except FileNotFoundError:
        return f"Error: File not found: {path}"
    except Exception as e:
        return f"Error reading {path}: {e}"

    count = content.count(old_string)
    if count == 0:
        # Show close matches to help debug
        lines = content.split("\n")
        close = []
        needle = old_string.split("\n")[0].strip()
        for i, line in enumerate(lines, 1):
            if needle[:30] in line:
                close.append(f"  Line {i}: {line.rstrip()[:80]}")
        hint = "\n".join(close[:5]) if close else "  (no similar lines found)"
        return f"Error: old_string not found in {path}.\nSearched for: {repr(old_string[:80])}\nClose matches:\n{hint}"
    if count > 1:
        return f"Error: old_string found {count} times in {path}. Must be unique. Add more context."

    new_content = content.replace(old_string, new_string, 1)
    try:
        with open(path, "w") as f:
            f.write(new_content)
    except Exception as e:
        return f"Error writing {path}: {e}"

    # Show diff
    old_lines = old_string.split("\n")
    new_lines = new_string.split("\n")
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm="", n=2))
    diff_str = "\n".join(diff[:20]) if diff else "(no visible diff)"
    return f"Edited {path} (1 replacement)\n{diff_str}"


def tool_run_command(command: str, timeout: int = 30) -> str:
    global CWD
    if APPROVE_SHELL:
        try:
            answer = input(f"  \033[33mRun:\033[0m {command} \033[90m[y/N]\033[0m ").strip().lower()
        except EOFError:
            return "Error: User denied command (EOF)"
        if answer not in ("y", "yes"):
            return "Command cancelled by user."

    # Handle cd specially
    if command.strip().startswith("cd "):
        new_dir = command.strip()[3:].strip().strip('"').strip("'")
        new_dir = _resolve_path(new_dir)
        if os.path.isdir(new_dir):
            CWD = new_dir
            return f"Changed directory to {CWD}"
        else:
            return f"Error: Directory not found: {new_dir}"

    try:
        # Cross-platform PATH handling
        if sys.platform == "win32":
            # Windows: PATH separator is ;, add common Windows paths
            extra_path = ";C:\\Program Files\\Git\\usr\\bin;C:\\Windows\\System32"
            path_sep = ";"
        else:
            # Unix-like: PATH separator is :
            extra_path = ":/usr/local/bin:/usr/bin"
            path_sep = ":"
        
        current_path = os.environ.get("PATH", "")
        new_env = {**os.environ, "PATH": current_path + extra_path}
        
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=CWD, env=new_env
        )
        output = result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        output = output.strip() or "(no output)"
        if result.returncode != 0:
            output = f"[exit code {result.returncode}]\n{output}"
        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + "\n... [truncated]"
        return output
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


def tool_search_files(pattern: str, path: str = None, glob_filter: str = None) -> str:
    search_path = _resolve_path(path) if path else CWD
    results = []
    count = 0
    max_results = 50

    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Error: Invalid regex: {e}"

    for root, dirs, files in os.walk(search_path):
        # Skip hidden dirs and common noise
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "venv", ".git")]
        for fname in files:
            if glob_filter and not globlib.fnmatch.fnmatch(fname, glob_filter):
                continue
            fpath = os.path.join(root, fname)
            try:
                with open(fpath, "r", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if compiled.search(line):
                            rel = os.path.relpath(fpath, search_path)
                            results.append(f"{rel}:{i}: {line.rstrip()[:120]}")
                            count += 1
                            if count >= max_results:
                                results.append(f"... [{count}+ matches, showing first {max_results}]")
                                return "\n".join(results)
            except (PermissionError, IsADirectoryError, UnicodeDecodeError):
                continue

    if not results:
        return f"No matches for /{pattern}/ in {search_path}"
    return "\n".join(results)


def tool_find_files(pattern: str, path: str = None) -> str:
    base = _resolve_path(path) if path else CWD
    full_pattern = os.path.join(base, pattern)
    matches = sorted(globlib.glob(full_pattern, recursive=True))

    if not matches:
        return f"No files matching {pattern} in {base}"

    results = []
    for m in matches[:100]:
        rel = os.path.relpath(m, base)
        try:
            stat = os.stat(m)
            size = stat.st_size
            if size < 1024:
                size_str = f"{size}B"
            elif size < 1024 * 1024:
                size_str = f"{size // 1024}KB"
            else:
                size_str = f"{size // (1024*1024)}MB"
            kind = "dir" if os.path.isdir(m) else "file"
            results.append(f"  {rel:<50} {size_str:>8}  {kind}")
        except OSError:
            results.append(f"  {rel}")

    header = f"Found {len(matches)} match{'es' if len(matches) != 1 else ''}:"
    if len(matches) > 100:
        header += f" (showing first 100 of {len(matches)})"
    return header + "\n" + "\n".join(results)


def tool_list_dir(path: str = None) -> str:
    target = _resolve_path(path) if path else CWD
    if not os.path.isdir(target):
        return f"Error: Not a directory: {target}"

    entries = []
    try:
        items = sorted(os.listdir(target))
    except PermissionError:
        return f"Error: Permission denied: {target}"

    for item in items:
        if item.startswith("."):
            continue
        full = os.path.join(target, item)
        try:
            stat = os.stat(full)
            size = stat.st_size
            if os.path.isdir(full):
                entries.append(f"  {item + '/':.<50} {'dir':>8}")
            else:
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size // 1024}KB"
                else:
                    size_str = f"{size // (1024*1024)}MB"
                entries.append(f"  {item:.<50} {size_str:>8}")
        except OSError:
            entries.append(f"  {item}")

    if not entries:
        return f"{target}: (empty)"
    return f"{target}:\n" + "\n".join(entries)


def tool_fetch_url(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) TrashClaw/0.2'})
        with urllib.request.urlopen(req, timeout=30) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
            # Simple heuristic HTML tag stripping without external dependencies
            # 1. Remove style and script blocks
            html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style.*?>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
            
            # 2. Remove all HTML tags
            text = re.sub(r'<[^>]+>', ' ', html)
            
            # 3. Fix HTML entities
            text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"').replace('&#39;', "'")
            
            # 4. Collapse whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            if not text:
                return f"Fetched {url} successfully, but found no readable text."
                
            if len(text) > MAX_OUTPUT_CHARS:
                return f"Fetched {url}:\n\n{text[:MAX_OUTPUT_CHARS]}... [truncated]"
            return f"Fetched {url}:\n\n{text}"
    except urllib.error.HTTPError as e:
        return f"HTTP Error fetching {url}: {e.code} {e.reason}"
    except urllib.error.URLError as e:
        return f"URL Error fetching {url}: {e.reason}"
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"


def tool_think(thought: str) -> str:
    return f"[Thought recorded, no side effects]"


def tool_view_image(path: str, resize_max: int = None) -> str:
    """Read an image file and return as base64-encoded data for vision models."""
    import base64
    
    path = _resolve_path(path)
    
    if not os.path.exists(path):
        return f"Error: Image file not found: {path}"
    
    valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
    ext = os.path.splitext(path)[1].lower()
    if ext not in valid_extensions:
        return f"Error: Unsupported image format '{ext}'. Supported: {', '.join(valid_extensions)}"
    
    mime_types = {
        '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp',
    }
    mime_type = mime_types.get(ext, 'application/octet-stream')
    
    try:
        with open(path, 'rb') as f:
            image_data = f.read()
        
        size_kb = len(image_data) / 1024
        if size_kb > 5000:
            return f"Error: Image too large ({size_kb:.1f}KB). Max 5MB."
        
        base64_data = base64.b64encode(image_data).decode('utf-8')
        data_url = f"data:{mime_type};base64,{base64_data}"
        
        return f"Image loaded: {path}\nSize: {size_kb:.1f}KB\nFormat: {mime_type}\nBase64 length: {len(base64_data)} chars\n\nData URL: {data_url[:200]}..."
    
    except Exception as e:
        return f"Error reading image {path}: {e}"


def tool_take_screenshot(region: str = None) -> str:
    """Take a screenshot using system tools and return as base64."""
    import base64
    import tempfile
    import subprocess
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    try:
        if sys.platform == 'linux':
            cmd = ['scrot', temp_path]
            if region:
                cmd = ['scrot', '-a', region, temp_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                cmd = ['import', '-window', 'root', temp_path]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
        elif sys.platform == 'darwin':
            cmd = ['screencapture', '-x', temp_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
        elif sys.platform == 'win32':
            return "Error: Windows screenshot not yet implemented. Use view_image instead."
        else:
            return f"Error: Unsupported platform: {sys.platform}"
        
        if result.returncode != 0:
            return f"Error taking screenshot: {result.stderr}"
        
        with open(temp_path, 'rb') as f:
            image_data = f.read()
        
        base64_data = base64.b64encode(image_data).decode('utf-8')
        size_kb = len(image_data) / 1024
        os.unlink(temp_path)
        
        data_url = f"data:image/png;base64,{base64_data}"
        return f"Screenshot captured\nSize: {size_kb:.1f}KB\nFormat: image/png\nBase64 length: {len(base64_data)} chars\n\nData URL: {data_url[:200]}..."
    
    except subprocess.TimeoutExpired:
        if os.path.exists(temp_path): os.unlink(temp_path)
        return "Error: Screenshot timed out"
    except FileNotFoundError as e:
        if os.path.exists(temp_path): os.unlink(temp_path)
        return f"Error: Screenshot tool not found. Install 'scrot' (Linux). {e}"
    except Exception as e:
        if os.path.exists(temp_path): os.unlink(temp_path)
        return f"Error taking screenshot: {e}"


# Tool dispatch
TOOL_DISPATCH = {
    "read_file": lambda args: tool_read_file(args["path"], args.get("offset"), args.get("limit")),
    "write_file": lambda args: tool_write_file(args["path"], args["content"]),
    "edit_file": lambda args: tool_edit_file(args["path"], args["old_string"], args["new_string"]),
    "run_command": lambda args: tool_run_command(args["command"], args.get("timeout", 30)),
    "search_files": lambda args: tool_search_files(args["pattern"], args.get("path"), args.get("glob_filter")),
    "find_files": lambda args: tool_find_files(args["pattern"], args.get("path")),
    "list_dir": lambda args: tool_list_dir(args.get("path")),
    "fetch_url": lambda args: tool_fetch_url(args["url"]),
    "think": lambda args: tool_think(args["thought"]),
    "view_image": lambda args: tool_view_image(args["path"], args.get("resize_max")),
    "take_screenshot": lambda args: tool_take_screenshot(args.get("region")),
}


def detect_project_context() -> str:
    """Scan CWD for common project files and return a summary of the framework/language."""
    files = set(os.listdir(CWD))
    context = []
    
    if "package.json" in files:
        context.append("Node.js/JavaScript")
    if "Cargo.toml" in files:
        context.append("Rust")
    if "requirements.txt" in files or "pyproject.toml" in files or "setup.py" in files:
        context.append("Python")
    if "go.mod" in files:
        context.append("Go")
    if "Makefile" in files:
        context.append("Make")
    if "CMakeLists.txt" in files:
        context.append("C/C++ (CMake)")
    if "pom.xml" in files or "build.gradle" in files:
        context.append("Java")
    if "composer.json" in files:
        context.append("PHP (Composer)")
    if "Gemfile" in files:
        context.append("PHP (Composer)") # wait, gemfile is Ruby
        context[-1] = "Ruby"
        
    if not context:
        return "Unknown or Generic"
    return ", ".join(context)


# ── LLM Client ──

SYSTEM_PROMPT = """You are TrashClaw, a general-purpose local agent running on the user's machine.

You can accomplish any task that involves files, commands, or information on this system.
You are not limited to coding — you handle research, system administration, file management,
data processing, automation, and anything else the user asks.

Current Directory: {cwd}
Detected Project Context: {project_context}

You have access to these tools:
- read_file: Read file contents with optional line range
- write_file: Create or overwrite files
- edit_file: Replace exact strings in files (must match uniquely)
- run_command: Execute shell commands (curl, git, grep, python, anything installed)
- search_files: Grep for patterns across files
- find_files: Find files by glob pattern
- list_dir: List directory contents
- think: Reason through a problem step by step before acting

IMPORTANT RULES:
1. Always read a file before editing it.
2. Use edit_file for surgical changes, write_file for new files.
3. Use think to plan multi-step tasks before starting.
4. Be concise — every token counts.
5. After making changes, verify them.
6. If a command might be destructive, explain what it does first.
7. Use run_command freely — curl for web requests, python for computation, etc.
8. Chain tools together to accomplish complex tasks autonomously.

You are part of the Elyan Labs ecosystem. Current directory: {cwd}"""


def llm_request(messages: List[Dict], tools: List[Dict] = None) -> Dict:
    """Send request to llama-server and return the full response while streaming text."""
    payload = {
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
        "stream": True,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{LLAMA_URL}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    
    full_content = ""
    tool_calls_dict = {}
    finish_reason = None
    
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    choice = chunk.get("choices", [{}])[0]
                    delta = choice.get("delta", {})
                    
                    if "content" in delta and delta["content"]:
                        content = delta["content"]
                        full_content += content
                        print(content, end="", flush=True)
                        
                    if "tool_calls" in delta and delta["tool_calls"]:
                        for tc in delta["tool_calls"]:
                            idx = tc.get("index", 0)
                            if idx not in tool_calls_dict:
                                tool_calls_dict[idx] = {
                                    "id": tc.get("id", f"tc_{idx}"),
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                }
                            func = tc.get("function", {})
                            if "name" in func and func["name"]:
                                tool_calls_dict[idx]["function"]["name"] += func["name"]
                            if "arguments" in func and func["arguments"]:
                                tool_calls_dict[idx]["function"]["arguments"] += func["arguments"]
                                
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]
                        
                except json.JSONDecodeError:
                    pass
        print() # Newline after streaming completes
    except urllib.error.URLError as e:
        return {"error": f"Cannot reach llama-server: {e}"}
    except Exception as e:
        return {"error": f"LLM request failed: {e}"}

    tool_calls_list = [v for k, v in sorted(tool_calls_dict.items())] if tool_calls_dict else None
    
    return {
        "choices": [{
            "message": {
                "content": full_content,
                "tool_calls": tool_calls_list
            },
            "finish_reason": finish_reason
        }]
    }


def _try_parse_tool_calls_from_text(text: str) -> Optional[List[Dict]]:
    """Fallback: parse tool calls from text if model doesn't use native function calling.

    Supports formats:
      <tool_call>{"name": "...", "arguments": {...}}</tool_call>
      ```json\n{"name": "...", "arguments": {...}}\n```
      {"tool": "...", "args": {...}}
    """
    calls = []

    # Format 1: <tool_call> tags
    tag_matches = re.findall(r'<tool_call>\s*(\{.*?\})\s*</tool_call>', text, re.DOTALL)
    for m in tag_matches:
        try:
            obj = json.loads(m)
            name = obj.get("name") or obj.get("tool") or obj.get("function", "")
            args = obj.get("arguments") or obj.get("args") or obj.get("parameters", {})
            if isinstance(args, str):
                args = json.loads(args)
            if name in TOOL_NAMES:
                calls.append({"name": name, "arguments": args})
        except (json.JSONDecodeError, TypeError):
            continue

    if calls:
        return calls

    # Format 2: JSON in code blocks
    block_matches = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    for m in block_matches:
        try:
            obj = json.loads(m)
            name = obj.get("name") or obj.get("tool") or obj.get("function", "")
            args = obj.get("arguments") or obj.get("args") or obj.get("parameters", {})
            if isinstance(args, str):
                args = json.loads(args)
            if name in TOOL_NAMES:
                calls.append({"name": name, "arguments": args})
        except (json.JSONDecodeError, TypeError):
            continue

    if calls:
        return calls

    # Format 3: bare JSON with tool/name field
    json_matches = re.findall(r'\{[^{}]*"(?:name|tool)"[^{}]*\}', text)
    for m in json_matches:
        try:
            obj = json.loads(m)
            name = obj.get("name") or obj.get("tool", "")
            args = obj.get("arguments") or obj.get("args") or obj.get("parameters", {})
            if isinstance(args, str):
                args = json.loads(args)
            if name in TOOL_NAMES:
                calls.append({"name": name, "arguments": args})
        except (json.JSONDecodeError, TypeError):
            continue

    return calls if calls else None


# ── Agent Loop ──

def agent_turn(user_message: str):
    """Run the full agent loop: LLM thinks, calls tools, observes, repeats."""
    # Build user message content (with optional image)
    if IMAGE_PATH:
        image_data = load_image_to_base64(IMAGE_PATH)
        if image_data:
            # Vision model format: content can be a list of text + image
            user_content = [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]
        else:
            user_content = user_message
    else:
        user_content = user_message
    
    HISTORY.append({"role": "user", "content": user_content})

    for round_num in range(MAX_TOOL_ROUNDS):
        # Build messages
        sys_prompt = SYSTEM_PROMPT.format(cwd=CWD, project_context=detect_project_context())
        messages = [{"role": "system", "content": sys_prompt}]
        # Keep recent context
        messages.extend(HISTORY[-40:])

        # Show thinking indicator
        indicator = f"  \033[90m[round {round_num + 1}]\033[0m " if round_num > 0 else "  "
        print(f"{indicator}\033[90mthinking...\033[0m", end="", flush=True)

        # Call LLM
        response = llm_request(messages, tools=TOOLS)

        # Clear thinking indicator
        print(f"\r{' ' * 60}\r", end="")

        if "error" in response:
            err_msg = response["error"]
            print(f"\033[31m[ERROR]\033[0m {err_msg}")
            HISTORY.append({"role": "assistant", "content": f"Error: {err_msg}"})
            return

        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls")
        finish_reason = choice.get("finish_reason", "")

        # If no native tool calls, try parsing from text
        if not tool_calls and content:
            parsed = _try_parse_tool_calls_from_text(content)
            if parsed:
                tool_calls = [
                    {
                        "id": f"tc_{i}",
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}
                    }
                    for i, tc in enumerate(parsed)
                ]
                # Strip the tool call JSON from displayed content
                display_content = re.sub(r'<tool_call>.*?</tool_call>', '', content, flags=re.DOTALL).strip()
                display_content = re.sub(r'```json\s*\{.*?\}\s*```', '', display_content, flags=re.DOTALL).strip()
                if display_content:
                    print(display_content)

        # No tool calls — just a text response, we're done
        if not tool_calls:
            if content:
                print(content)
            HISTORY.append({"role": "assistant", "content": content})
            return

        # Execute tool calls
        assistant_msg = {"role": "assistant", "content": content or None, "tool_calls": tool_calls}
        HISTORY.append(assistant_msg)

        for tc in tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "unknown")
            tool_id = tc.get("id", "tc_0")

            # Parse arguments
            try:
                args_raw = func.get("arguments", "{}")
                if isinstance(args_raw, str):
                    args = json.loads(args_raw)
                else:
                    args = args_raw
            except json.JSONDecodeError:
                args = {}

            # Display what's happening
            if tool_name == "think":
                thought = args.get("thought", "")
                print(f"  \033[36m[think]\033[0m {thought[:200]}")
            elif tool_name == "read_file":
                print(f"  \033[34m[read]\033[0m {args.get('path', '?')}")
            elif tool_name == "write_file":
                print(f"  \033[32m[write]\033[0m {args.get('path', '?')}")
            elif tool_name == "edit_file":
                print(f"  \033[33m[edit]\033[0m {args.get('path', '?')}")
            elif tool_name == "run_command":
                print(f"  \033[35m[run]\033[0m {args.get('command', '?')}")
            elif tool_name == "search_files":
                print(f"  \033[34m[search]\033[0m /{args.get('pattern', '?')}/")
            elif tool_name == "find_files":
                print(f"  \033[34m[find]\033[0m {args.get('pattern', '?')}")
            elif tool_name == "list_dir":
                print(f"  \033[34m[ls]\033[0m {args.get('path', CWD)}")
            elif tool_name == "fetch_url":
                print(f"  \033[34m[fetch]\033[0m {args.get('url', '?')}")

            # Execute
            handler = TOOL_DISPATCH.get(tool_name)
            if handler:
                try:
                    result = handler(args)
                except Exception as e:
                    result = f"Error executing {tool_name}: {e}\n{traceback.format_exc()}"
            else:
                result = f"Error: Unknown tool '{tool_name}'"

            # Add tool result to history
            HISTORY.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": result
            })

        # Continue loop — LLM will see tool results and decide next action

    # Max rounds reached
    print(f"\033[33m[WARN]\033[0m Max tool rounds ({MAX_TOOL_ROUNDS}) reached. Stopping.")


# ── Slash Commands ──

def handle_slash(cmd: str) -> bool:
    """Handle slash commands. Returns True if handled."""
    parts = cmd.strip().split(None, 1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if command in ("/exit", "/quit", "/q"):
        print("\nTrashClaw out. Keep the trashcan warm.")
        sys.exit(0)

    elif command == "/clear":
        HISTORY.clear()
        print("  Context cleared.")

    elif command == "/cd":
        global CWD
        new_dir = _resolve_path(arg) if arg else os.path.expanduser("~")
        if os.path.isdir(new_dir):
            CWD = new_dir
            print(f"  CWD: {CWD}")
        else:
            print(f"  Error: {new_dir} not found")

    elif command == "/status":
        try:
            req = urllib.request.Request(f"{LLAMA_URL}/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                health = json.loads(resp.read().decode("utf-8"))
            status = health.get("status", "unknown")
        except Exception:
            status = "unreachable"
        print(f"  Server: {status} ({LLAMA_URL})")
        print(f"  Model: {MODEL_NAME}")
        print(f"  Context: {len(HISTORY)} messages")
        print(f"  CWD: {CWD}")
        print(f"  Project: {detect_project_context()}")
        print(f"  Max rounds: {MAX_TOOL_ROUNDS}")
        print(f"  Shell approval: {'on' if APPROVE_SHELL else 'off'}")

    elif command == "/compact":
        # Keep only last 10 messages
        old_len = len(HISTORY)
        HISTORY[:] = HISTORY[-10:]
        print(f"  Compacted {old_len} -> {len(HISTORY)} messages")

    elif command == "/screenshot":
        # Take a screenshot and show it
        print("  Taking screenshot...")
        result = tool_take_screenshot(region=arg if arg else None)
        print(f"  {result}")

    elif command == "/img":
        # View an image file
        if not arg:
            print("  Usage: /img <image_path>")
        else:
            print(f"  Loading image: {arg}")
            result = tool_view_image(arg)
            print(f"  {result}")

    elif command == "/vision":
        # Check if connected LLM supports vision
        print(f"  Checking vision support at {LLAMA_URL}...")
        try:
            req = urllib.request.Request(f"{LLAMA_URL}/v1/models")
            with urllib.request.urlopen(req, timeout=10) as resp:
                models_data = json.loads(resp.read().decode("utf-8"))
            models = models_data.get("data", [])
            vision_models = [m for m in models if any(v in m.get("id", "").lower() for v in ['vision', 'vl', 'llava', 'qwen-vl'])]
            if vision_models:
                print(f"  Vision models available: {[m['id'] for m in vision_models]}")
            else:
                print(f"  No vision models detected. Models: {[m['id'] for m in models[:5]]}")
        except Exception as e:
            print(f"  Could not check vision support: {e}")

    elif command == "/save":
        # Save current conversation to JSON file
        if not arg:
            print("  Usage: /save <session_name>")
        else:
            session_dir = os.path.join(os.path.expanduser("~"), ".trashclaw", "sessions")
            os.makedirs(session_dir, exist_ok=True)
            session_file = os.path.join(session_dir, f"{arg}.json")
            session_data = {
                "name": arg,
                "saved_at": datetime.now().isoformat(),
                "cwd": CWD,
                "history": HISTORY
            }
            try:
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                print(f"  Saved session to {session_file}")
            except Exception as e:
                print(f"  Error saving session: {e}")

    elif command == "/load":
        # Load conversation from JSON file
        if not arg:
            print("  Usage: /load <session_name>")
        else:
            session_dir = os.path.join(os.path.expanduser("~"), ".trashclaw", "sessions")
            session_file = os.path.join(session_dir, f"{arg}.json")
            if not os.path.exists(session_file):
                print(f"  Error: Session '{arg}' not found")
            else:
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    HISTORY[:] = session_data.get("history", [])
                    if "cwd" in session_data and os.path.isdir(session_data["cwd"]):
                        CWD = session_data["cwd"]
                    print(f"  Loaded session '{arg}' ({len(HISTORY)} messages)")
                except Exception as e:
                    print(f"  Error loading session: {e}")

    elif command == "/sessions":
        # List saved sessions
        session_dir = os.path.join(os.path.expanduser("~"), ".trashclaw", "sessions")
        if not os.path.exists(session_dir):
            print("  No saved sessions")
        else:
            sessions = [f[:-5] for f in os.listdir(session_dir) if f.endswith('.json')]
            if not sessions:
                print("  No saved sessions")
            else:
                print("  Saved sessions:")
                for name in sorted(sessions):
                    session_file = os.path.join(session_dir, f"{name}.json")
                    try:
                        with open(session_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        saved_at = data.get("saved_at", "unknown")[:19]
                        msg_count = len(data.get("history", []))
                        print(f"    - {name} ({msg_count} messages, saved {saved_at})")
                    except:
                        print(f"    - {name} (unreadable)")

    elif command == "/help":
        print("""
  \033[1mTrashClaw Agent Commands\033[0m

  /cd <dir>      Change working directory
  /clear         Clear all conversation context
  /compact       Keep only last 10 messages (saves context)
  /status        Show server, model, and context info
  /save <name>   Save current conversation to session file
  /load <name>   Load conversation from session file
  /sessions      List all saved sessions
  /exit          Exit TrashClaw
  /help          Show this help

  \033[1mCommand-line Options\033[0m
  --image <path>   Analyze an image with vision models (png, jpg, gif, webp)
  --url <url>      Set custom LLM server URL
  --cwd <dir>      Set working directory
  --auto-shell     Skip shell command approval prompts

  \033[1mEnvironment Variables\033[0m
  TRASHCLAW_URL        llama-server endpoint (default: http://localhost:8080)
  TRASHCLAW_MODEL      Model name for display
  TRASHCLAW_MAX_ROUNDS Max tool execution rounds (default: 15)
  TRASHCLAW_AUTO_SHELL Set to 1 to skip shell command approval

  Just type naturally. TrashClaw will use tools autonomously to help you.
        """)
    else:
        print(f"  Unknown command: {command}. Try /help")

    return True


# ── Main ──

def banner():
    image_info = f" | Image: {IMAGE_PATH}" if IMAGE_PATH else ""
    print("""
\033[36m ████████╗██████╗  █████╗ ███████╗██╗  ██╗ ██████╗██╗      █████╗ ██╗    ██╗
 ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║  ██║██╔════╝██║     ██╔══██╗██║    ██║
    ██║   ██████╔╝███████║███████╗███████║██║     ██║     ███████║██║ █╗ ██║
    ██║   ██╔══██╗██╔══██║╚════██║██╔══██║██║     ██║     ██╔══██║██║███╗██║
    ██║   ██║  ██║██║  ██║███████║██║  ██║╚██████╗███████╗██║  ██║╚███╔███╔╝
    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝\033[0m

    \033[1mElyan Labs\033[0m | Mac Pro Trashcan Edition | v0.2
    General-purpose agent — files, commands, search, automation, anything local.
    Model: {model} | CWD: {cwd}{image}
    Type /help for commands, or just describe what you want to do.
    \033[90mUse --image <path> to analyze images with vision models\033[0m
""".format(model=MODEL_NAME, cwd=CWD, image=image_info))


def main():
    global CWD, IMAGE_PATH

    # Parse command-line arguments
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--cwd" and i < len(sys.argv):
            CWD = os.path.abspath(sys.argv[i + 1])
        elif arg.startswith("--cwd="):
            CWD = os.path.abspath(arg.split("=", 1)[1])
        elif arg == "--url" and i < len(sys.argv):
            globals()["LLAMA_URL"] = sys.argv[i + 1]
        elif arg.startswith("--url="):
            globals()["LLAMA_URL"] = arg.split("=", 1)[1]
        elif arg == "--auto-shell":
            globals()["APPROVE_SHELL"] = False
        elif arg == "--image" and i < len(sys.argv):
            IMAGE_PATH = sys.argv[i + 1]
        elif arg.startswith("--image="):
            IMAGE_PATH = arg.split("=", 1)[1]

    banner()

    # Backend Detection
    backend = "Unknown"
    base_url = LLAMA_URL.rstrip("/")
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]

    # 1. Try LM Studio (/v1/models)
    try:
        req = urllib.request.Request(f"{base_url}/v1/models")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "data" in data:
                backend = "LM Studio"
                globals()["LLAMA_URL"] = f"{base_url}/v1"
    except Exception:
        pass

    # 2. Try Ollama (/api/tags)
    if backend == "Unknown":
        try:
            req = urllib.request.Request(f"{base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "models" in data:
                    backend = "Ollama"
                    globals()["LLAMA_URL"] = f"{base_url}/v1"
        except Exception:
            pass

    # 3. Try llama.cpp (/health)
    if backend == "Unknown":
        try:
            req = urllib.request.Request(f"{base_url}/health")
            with urllib.request.urlopen(req, timeout=2) as resp:
                health = json.loads(resp.read().decode("utf-8"))
            if health.get("status") in ("ok", "error", "loading"):
                backend = "llama.cpp"
                # llama.cpp also typically exposes /v1 for OpenAI compat
                globals()["LLAMA_URL"] = base_url
        except Exception:
            pass

    if backend == "Unknown":
        print(f"\033[33m[WARN]\033[0m Cannot definitively detect backend at {LLAMA_URL}. Assuming OpenAI-compatible.")
    else:
        print(f"  \033[32mConnected to {backend} at {LLAMA_URL}\033[0m\n")

    while True:
        try:
            prompt = f"\033[1mtrashclaw\033[0m \033[90m{os.path.basename(CWD)}\033[0m> "
            user_input = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTrashClaw out.")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            handle_slash(user_input)
            continue

        agent_turn(user_input)


if __name__ == "__main__":
    main()
