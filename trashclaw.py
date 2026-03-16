#!/usr/bin/env python3
"""
TrashClaw v0.2 — Local Tool-Use Agent
======================================
A general-purpose agent powered by a local LLM. Reads files, writes files,
runs commands, searches codebases, fetches URLs, processes data — whatever
you need. OpenClaw-style tool-use loop with zero external dependencies.

Pure Python stdlib. Python 3.7+. Works with any OpenAI-compatible server.

Windows compatibility:
- readline fallback for Windows
- Cross-platform shell execution (PowerShell/CMD on Windows, bash/sh on *nix)
- Robust path normalization across OSes
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
import shutil
import platform
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# ── Safe readline import / fallback for Windows ──
try:
    import readline  # type: ignore
except Exception:
    class _ReadlineFallback:
        def set_history_length(self, n: int) -> None:
            pass
        def add_history(self, s: str) -> None:
            pass
    readline = _ReadlineFallback()  # type: ignore

# ── Config ──
LLAMA_URL = os.environ.get("TRASHCLAW_URL", "http://localhost:8080")
MODEL_NAME = os.environ.get("TRASHCLAW_MODEL", "local")
MAX_TOOL_ROUNDS = int(os.environ.get("TRASHCLAW_MAX_ROUNDS", "15"))
MAX_OUTPUT_CHARS = int(os.environ.get("TRASHCLAW_MAX_OUTPUT", "8000"))
APPROVE_SHELL = os.environ.get("TRASHCLAW_AUTO_SHELL", "0") != "1"
TRASHCLAW_SHELL = os.environ.get("TRASHCLAW_SHELL", "").strip()
TRASHCLAW_WIN_SHELL = os.environ.get("TRASHCLAW_WIN_SHELL", "").strip().lower()  # "powershell" | "cmd"
HISTORY: List[Dict[str, Any]] = []
CWD = os.getcwd()
IS_WINDOWS = os.name == "nt" or sys.platform.startswith("win")
PY_VERSION = sys.version_info[:3]

# ── Utilities ──

def _clip(s: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if s is None:
        return ""
    if len(s) <= limit:
        return s
    head = s[: max(0, limit - 200)]
    tail = s[-200:]
    return f"{head}\n...\n[truncated {len(s)-len(head)-len(tail)} chars]\n{tail}"

def _now() -> str:
    try:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""

def norm_path(path: str, base: Optional[str] = None) -> str:
    if not path:
        return path
    p = os.path.expandvars(os.path.expanduser(path))
    if not os.path.isabs(p):
        b = base if base else CWD
        p = os.path.join(b, p)
    # Normalize and resolve symlinks where possible
    try:
        p = os.path.normpath(p)
    except Exception:
        pass
    return p

def ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def detect_shell() -> Tuple[List[str], str]:
    """
    Returns (argv, kind)
    kind in {"bash", "sh", "powershell", "cmd"}
    Respects TRASHCLAW_SHELL and TRASHCLAW_WIN_SHELL env vars.
    """
    if TRASHCLAW_SHELL:
        # Custom shell path or command; executed with -lc if bash-like
        sh = TRASHCLAW_SHELL.strip()
        base = os.path.basename(sh).lower()
        if IS_WINDOWS:
            # If user specifies "cmd" or "powershell" we handle flags; else pass-through to powershell style
            if "powershell" in base or base == "pwsh.exe" or base == "pwsh":
                return ([sh, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"], "powershell")
            if base in ("cmd", "cmd.exe"):
                return ([sh, "/d", "/c"], "cmd")
            # Fallback to powershell style flags
            return ([sh, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"], "powershell")
        else:
            # If bash present in name, prefer -lc
            if "bash" in base:
                return ([sh, "-lc"], "bash")
            # Fallback to sh
            return ([sh, "-lc"], "sh")
    if IS_WINDOWS:
        # Prefer pwsh if available, else PowerShell 5, else cmd
        pwsh = shutil.which("pwsh.exe") or shutil.which("pwsh")
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        prefer = TRASHCLAW_WIN_SHELL
        if prefer == "cmd":
            cmd = shutil.which("cmd.exe") or "cmd.exe"
            return ([cmd, "/d", "/c"], "cmd")
        if prefer == "powershell":
            if pwsh:
                return ([pwsh, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"], "powershell")
            if powershell:
                return ([powershell, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"], "powershell")
        # Auto-detect
        if pwsh or powershell:
            sh = pwsh or powershell
            return ([sh, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command"], "powershell")
        # Last resort: cmd
        cmd = shutil.which("cmd.exe") or "cmd.exe"
        return ([cmd, "/d", "/c"], "cmd")
    # POSIX
    bash = shutil.which("bash")
    sh = shutil.which("sh") or "/bin/sh"
    if bash:
        return ([bash, "-lc"], "bash")
    return ([sh, "-lc"], "sh")

def run_shell(command: str, cwd: Optional[str] = None, timeout: Optional[int] = None, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    shell_argv, kind = detect_shell()
    cwd_use = cwd or CWD
    env_use = os.environ.copy()
    if env:
        env_use.update(env)
    # Windows unicode: use text=True + encoding/replace
    try:
        # Combine as: [shell, flags..., command]
        args = list(shell_argv) + [command]
        p = subprocess.run(
            args,
            cwd=cwd_use,
            env=env_use,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            universal_newlines=True,  # text mode for 3.7+
            encoding="utf-8",
            errors="replace",
        )
        return {
            "ok": p.returncode == 0,
            "exit_code": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
            "shell": kind,
            "argv": args,
        }
    except subprocess.TimeoutExpired as e:
        out = ""
        err = f"Timeout after {timeout}s" if timeout else "Timeout"
        try:
            out = e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            err_full = e.stderr.decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
            if err_full:
                err += "\n" + err_full
        except Exception:
            pass
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": out,
            "stderr": err,
            "shell": kind,
            "argv": list(shell_argv) + [command],
        }
    except Exception as e:
        return {
            "ok": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"{type(e).__name__}: {e}",
            "shell": kind,
            "argv": list(shell_argv) + [command],
        }

def http_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset, "replace")
            return {"ok": True, "status": resp.status, "json": json.loads(body)}
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", "replace")
        except Exception:
            err_body = ""
        return {"ok": False, "status": e.code, "error": err_body}
    except Exception as e:
        return {"ok": False, "status": 0, "error": f"{type(e).__name__}: {e}"}

def llm_chat(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, tool_choice: Optional[str] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.2,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        if tool_choice:
            payload["tool_choice"] = tool_choice
    url = LLAMA_URL.rstrip("/") + "/v1/chat/completions"
    return http_json(url, payload)

def safe_read_file(path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> Tuple[bool, str]:
    p = norm_path(path)
    if not os.path.exists(p):
        return False, f"File not found: {p}"
    try:
        with open(p, "r", encoding="utf-8", errors="replace", newline="") as f:
            if offset is None and limit is None:
                return True, f.read()
            # Line-based slicing, 1-based offset
            start = max(1, int(offset or 1))
            lim = limit if limit is not None else None
            out_lines = []
            for i, line in enumerate(f, start=1):
                if i < start:
                    continue
                out_lines.append(line)
                if lim is not None and len(out_lines) >= lim:
                    break
            return True, "".join(out_lines)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def safe_write_file(path: str, content: str) -> Tuple[bool, str]:
    p = norm_path(path)
    try:
        ensure_dir(p)
        with open(p, "w", encoding="utf-8", errors="replace", newline="") as f:
            f.write(content)
        return True, f"Wrote {len(content)} bytes to {p}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def safe_append_file(path: str, content: str) -> Tuple[bool, str]:
    p = norm_path(path)
    try:
        ensure_dir(p)
        with open(p, "a", encoding="utf-8", errors="replace", newline="") as f:
            f.write(content)
        return True, f"Appended {len(content)} bytes to {p}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def safe_edit_file(path: str, old_string: str, new_string: str, count: Optional[int] = None) -> Tuple[bool, str]:
    p = norm_path(path)
    if not os.path.exists(p):
        return False, f"File not found: {p}"
    try:
        with open(p, "r", encoding="utf-8", errors="replace", newline="") as f:
            data = f.read()
        if old_string not in data:
            return False, "old_string not found"
        n = -1 if count is None else max(0, int(count))
        replaced = data.replace(old_string, new_string, n if n >= 0 else data.count(old_string))
        with open(p, "w", encoding="utf-8", errors="replace", newline="") as f:
            f.write(replaced)
        changes = abs(len(replaced) - len(data))
        return True, f"Replaced occurrences; size delta {changes} bytes"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def safe_glob(pattern: str, base: Optional[str] = None, recursive: bool = True) -> List[str]:
    b = base or CWD
    pat = norm_path(pattern, base=b)
    # Keep pattern as-is for glob; but ensure directory separators are OS-native
    try:
        # If the pattern was absolute, okay; else join base and relative pattern
        if not os.path.isabs(pattern):
            pat = os.path.join(b, pattern)
    except Exception:
        pass
    files = globlib.glob(pat, recursive=recursive)
    # Normalize and make relative to current CWD when possible
    out = []
    for p in files:
        try:
            out.append(os.path.normpath(p))
        except Exception:
            out.append(p)
    return out

def safe_list_dir(path: Optional[str] = None) -> Tuple[bool, str]:
    p = norm_path(path or CWD)
    if not os.path.exists(p):
        return False, f"Not found: {p}"
    if not os.path.isdir(p):
        return False, f"Not a directory: {p}"
    try:
        entries = os.listdir(p)
        entries.sort()
        lines = []
        for name in entries:
            fp = os.path.join(p, name)
            try:
                st = os.stat(fp)
                size = st.st_size
                typ = "dir" if os.path.isdir(fp) else "file"
                lines.append(f"{typ:4} {size:10d}  {name}")
            except Exception:
                lines.append(f"????          ?  {name}")
        return True, "\n".join(lines)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def safe_search(pattern: str, paths: List[str], flags: Optional[str] = None, max_matches: int = 2000) -> Tuple[bool, str]:
    # flags: "i" case-insensitive, "m" multiline, "s" dotall
    fl = 0
    if flags:
        if "i" in flags:
            fl |= re.IGNORECASE
        if "m" in flags:
            fl |= re.MULTILINE
        if "s" in flags:
            fl |= re.DOTALL
    try:
        rx = re.compile(pattern, fl)
    except Exception as e:
        return False, f"Invalid regex: {type(e).__name__}: {e}"
    matches = []
    total = 0
    for p in paths:
        # Expand globs for each input path
        expanded = safe_glob(p, base=CWD, recursive=True) if any(ch in p for ch in ["*", "?", "["]) else [norm_path(p)]
        for fp in expanded:
            if not os.path.isfile(fp):
                continue
            try:
                with open(fp, "r", encoding="utf-8", errors="replace", newline="") as f:
                    for i, line in enumerate(f, start=1):
                        for m in rx.finditer(line):
                            snippet = line.rstrip("\n")
                            matches.append(f"{fp}:{i}:{m.start()}:{snippet}")
                            total += 1
                            if total >= max_matches:
                                break
                    if total >= max_matches:
                        break
            except Exception:
                continue
        if total >= max_matches:
            break
    if not matches:
        return True, "No matches."
    if total >= max_matches:
        matches.append(f"... truncated at {max_matches} matches")
    return True, "\n".join(matches)

def safe_diff(a_path: str, b_path: str, n: int = 3) -> Tuple[bool, str]:
    a_p = norm_path(a_path)
    b_p = norm_path(b_path)
    if not os.path.exists(a_p) or not os.path.exists(b_p):
        return False, "Both files must exist"
    try:
        with open(a_p, "r", encoding="utf-8", errors="replace", newline="") as fa:
            a_lines = fa.readlines()
        with open(b_p, "r", encoding="utf-8", errors="replace", newline="") as fb:
            b_lines = fb.readlines()
        diff = difflib.unified_diff(a_lines, b_lines, fromfile=a_p, tofile=b_p, lineterm="", n=n)
        return True, "\n".join(diff)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def http_get(url: str, timeout: int = 30) -> Tuple[bool, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "TrashClaw/0.2"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            body = resp.read().decode(charset, "replace")
            return True, body
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

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
                    "old_string": {"type": "string", "description": "Exact text to replace"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                    "count": {"type": "integer", "description": "Maximum number of replacements (optional)"}
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "append_file",
            "description": "Append text to a file, creating it if missing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files in a directory (name, size, type).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "Glob for files using patterns like **/*.py. Paths are relative to CWD unless absolute.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "recursive": {"type": "boolean"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_text",
            "description": "Regex search through files. Provide a list of file paths or glob patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "paths": {"type": "array", "items": {"type": "string"}},
                    "flags": {"type": "string", "description": "i,m,s"},
                    "max_matches": {"type": "integer"}
                },
                "required": ["pattern", "paths"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command in the project directory. Auto-detects OS shell (PowerShell/CMD on Windows, bash/sh on Unix).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer"},
                    "cwd": {"type": "string"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_dir",
            "description": "Change working directory for subsequent commands.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pwd",
            "description": "Return the current working directory.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "http_get",
            "description": "Fetch a URL via HTTP GET.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "timeout": {"type": "integer"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "diff_files",
            "description": "Unified diff between two files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a_path": {"type": "string"},
                    "b_path": {"type": "string"},
                    "context": {"type": "integer"}
                },
                "required": ["a_path", "b_path"]
            }
        }
    }
]

# ── Tool Handlers ──

def tool_read_file(args: Dict[str, Any]) -> str:
    ok, out = safe_read_file(args.get("path", ""), args.get("offset"), args.get("limit"))
    return out if ok else f"[ERROR] {out}"

def tool_write_file(args: Dict[str, Any]) -> str:
    ok, out = safe_write_file(args.get("path", ""), args.get("content", ""))
    return out if ok else f"[ERROR] {out}"

def tool_edit_file(args: Dict[str, Any]) -> str:
    ok, out = safe_edit_file(args.get("path", ""), args.get("old_string", ""), args.get("new_string", ""), args.get("count"))
    return out if ok else f"[ERROR] {out}"

def tool_append_file(args: Dict[str, Any]) -> str:
    ok, out = safe_append_file(args.get("path", ""), args.get("content", ""))
    return out if ok else f"[ERROR] {out}"

def tool_list_dir(args: Dict[str, Any]) -> str:
    ok, out = safe_list_dir(args.get("path"))
    return out if ok else f"[ERROR] {out}"

def tool_glob(args: Dict[str, Any]) -> str:
    pattern = args.get("pattern", "")
    recursive = bool(args.get("recursive", True))
    files = safe_glob(pattern, base=CWD, recursive=recursive)
    if not files:
        return "[]"
    return "\n".join(files)

def tool_search_text(args: Dict[str, Any]) -> str:
    pattern = args.get("pattern", "")
    paths = args.get("paths", [])
    flags = args.get("flags")
    max_matches = args.get("max_matches", 2000)
    ok, out = safe_search(pattern, paths, flags=flags, max_matches=max_matches)
    return out if ok else f"[ERROR] {out}"

def tool_run_shell(args: Dict[str, Any]) -> str:
    global CWD
    cmd = args.get("command", "")
    t = args.get("timeout")
    cwd = args.get("cwd") or CWD
    if not cmd.strip():
        return "[ERROR] Empty command"
    if APPROVE_SHELL:
        print(f"\n[approve] Run shell command in {cwd} using {detect_shell()[1]}:\n$ {cmd}")
        resp = input("Proceed? [y/N] ").strip().lower()
        if resp not in ("y", "yes"):
            return "[CANCELLED] Shell command rejected by user."
    res = run_shell(cmd, cwd=norm_path(cwd), timeout=int(t) if t else None)
    out = ""
    if res.get("stdout"):
        out += res["stdout"]
    if res.get("stderr"):
        if out:
            out += "\n"
        out += f"[stderr]\n{res['stderr']}"
    meta = f"[exit {res.get('exit_code')} via {res.get('shell')}]"
    if not out.strip():
        out = meta
    else:
        out = f"{out}\n{meta}"
    return _clip(out)

def tool_change_dir(args: Dict[str, Any]) -> str:
    global CWD
    p = norm_path(args.get("path", ""))
    if not os.path.exists(p):
        return f"[ERROR] Path not found: {p}"
    if not os.path.isdir(p):
        return f"[ERROR] Not a directory: {p}"
    CWD = p
    os.chdir(CWD)
    return f"Changed directory to: {CWD}"

def tool_pwd(args: Dict[str, Any]) -> str:
    return CWD

def tool_http_get(args: Dict[str, Any]) -> str:
    ok, out = http_get(args.get("url", ""), timeout=int(args.get("timeout", 30)))
    return out if ok else f"[ERROR] {out}"

def tool_diff_files(args: Dict[str, Any]) -> str:
    ok, out = safe_diff(args.get("a_path", ""), args.get("b_path", ""), n=int(args.get("context", 3)))
    return out if ok else f"[ERROR] {out}"

TOOL_IMPLS = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "edit_file": tool_edit_file,
    "append_file": tool_append_file,
    "list_dir": tool_list_dir,
    "glob": tool_glob,
    "search_text": tool_search_text,
    "run_shell": tool_run_shell,
    "change_dir": tool_change_dir,
    "pwd": tool_pwd,
    "http_get": tool_http_get,
    "diff_files": tool_diff_files,
}

# ── Chat / Tool Loop ──

def pretty_print_assistant(text: str) -> None:
    print("\nAssistant:")
    print(text)

def pretty_print_tool_call(name: str, args: Dict[str, Any]) -> None:
    print(f"\n[tool] {name}({json.dumps(args, ensure_ascii=False)})")

def run_agent_round(user_input: str) -> None:
    # Seed system prompt with minimal context and OS hint
    system_prompt = f"""You are TrashClaw, a local tool-use agent. You can read/write files, run shell commands, search code, and fetch URLs using provided tools.
Follow the user's instructions carefully. Prefer minimal, correct changes. Summarize your results.
Environment:
- OS: {platform.system()} {platform.release()}
- Python: {platform.python_version()}
- CWD: {CWD}
"""
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    # Add prior history
    messages.extend(HISTORY)
    messages.append({"role": "user", "content": user_input})

    tool_rounds = 0
    tool_results: List[Dict[str, Any]] = []

    while tool_rounds < MAX_TOOL_ROUNDS:
        resp = llm_chat(messages, tools=TOOLS, tool_choice="auto")
        if not resp.get("ok"):
            err = f"LLM request failed: HTTP {resp.get('status')} - {resp.get('error')}"
            pretty_print_assistant(err)
            HISTORY.append({"role": "assistant", "content": err})
            return
        data = resp.get("json", {})
        choices = data.get("choices") or []
        if not choices:
            pretty_print_assistant("[ERROR] Empty response from model.")
            HISTORY.append({"role": "assistant", "content": "[ERROR] Empty response from model."})
            return
        choice = choices[0]
        message = choice.get("message") or {}
        content = message.get("content")
        tool_calls = message.get("tool_calls") or []

        if tool_calls:
            # Process tool calls sequentially (OpenAI-style)
            for tc in tool_calls:
                f = tc.get("function") or {}
                name = f.get("name")
                args_str = f.get("arguments") or "{}"
                try:
                    args = json.loads(args_str) if isinstance(args_str, str) else args_str
                except Exception:
                    args = {}
                pretty_print_tool_call(name, args)
                impl = TOOL_IMPLS.get(name)
                if not impl:
                    result_text = f"[ERROR] Unknown tool: {name}"
                else:
                    try:
                        result_text = impl(args)
                    except Exception as e:
                        tb = traceback.format_exc()
                        result_text = f"[ERROR] {type(e).__name__}: {e}\n{tb}"
                tool_results.append({"tool_call_id": tc.get("id") or "", "name": name, "content": _clip(result_text)})
                # Push tool result back
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id") or "",
                    "name": name,
                    "content": _clip(result_text),
                })
            tool_rounds += 1
            # Continue loop to let assistant observe results and respond
            continue

        # No tools requested: final assistant content
        final_text = content or ""
        pretty_print_assistant(final_text)
        HISTORY.append({"role": "user", "content": user_input})
        HISTORY.append({"role": "assistant", "content": final_text})
        return

    # If loop exceeded rounds, print whatever assistant said last (if any)
    pretty_print_assistant("[stopped] Reached max tool rounds.")
    HISTORY.append({"role": "assistant", "content": "[stopped] Reached max tool rounds."})

# ── CLI ──

def print_banner() -> None:
    print("TrashClaw v0.2 — Local Tool-Use Agent")
    print(f"- URL: {LLAMA_URL} | Model: {MODEL_NAME}")
    print(f"- OS: {platform.system()} {platform.release()} | Python: {platform.python_version()}")
    print(f"- CWD: {CWD}")
    print("- Shell approval:", "ON" if APPROVE_SHELL else "OFF")
    sh, kind = detect_shell()
    print(f"- Shell: {kind} ({' '.join(sh[:-1])})")  # omit trailing placeholder for -lc/-Command
    print("Type your task. Ctrl+C to exit.")

def repl() -> None:
    print_banner()
    try:
        readline.set_history_length(1000)  # type: ignore
    except Exception:
        pass
    while True:
        try:
            s = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not s:
            continue
        try:
            readline.add_history(s)  # type: ignore
        except Exception:
            pass
        if s in (":quit", ":exit"):
            print("Bye.")
            break
        if s.startswith("!"):  # Quick local shell execution
            cmd = s[1:].strip()
            out = tool_run_shell({"command": cmd})
            print(out)
            continue
        run_agent_round(s)

def main(argv: List[str]) -> int:
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print("Usage: trashclaw.py")
        print("Environment:")
        print("  TRASHCLAW_URL           OpenAI-compatible base URL (default http://localhost:8080)")
        print("  TRASHCLAW_MODEL         Model name (default local)")
        print("  TRASHCLAW_MAX_ROUNDS    Max tool rounds per prompt (default 15)")
        print("  TRASHCLAW_MAX_OUTPUT    Max chars in tool outputs (default 8000)")
        print("  TRASHCLAW_AUTO_SHELL    Set to 1 to auto-approve shell commands (default 0)")
        print("  TRASHCLAW_SHELL         Full shell path to use (overrides auto-detect)")
        print("  TRASHCLAW_WIN_SHELL     powershell|cmd (Windows only, default auto)")
        return 0
    try:
        repl()
        return 0
    except KeyboardInterrupt:
        print("\nBye.")
        return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))