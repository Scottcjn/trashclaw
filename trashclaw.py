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
import readline
import urllib.request
import urllib.error
import re
import glob as globlib
import difflib
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# ── Config ──
LLAMA_URL = os.environ.get("TRASHCLAW_URL", "http://localhost:8080")
MODEL_NAME = os.environ.get("TRASHCLAW_MODEL", "local")
MAX_TOOL_ROUNDS = int(os.environ.get("TRASHCLAW_MAX_ROUNDS", "15"))
MAX_OUTPUT_CHARS = 8000
APPROVE_SHELL = os.environ.get("TRASHCLAW_AUTO_SHELL", "0") != "1"
HISTORY: List[Dict[str, Any]] = []
CWD = os.getcwd()

# ── Utilities ──

def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def clamp_text(s: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    if s is None:
        return ""
    if len(s) <= max_chars:
        return s
    head = s[: max_chars // 2]
    tail = s[-max_chars // 2 :]
    return f"{head}\n...\n[output truncated: {len(s) - max_chars} chars omitted]\n...\n{tail}"


def http_post_json(url: str, payload: Dict[str, Any], timeout: int = 300) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def print_err(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def is_tty() -> bool:
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


# ── Tool Implementations ──

def tool_read_file(path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> str:
    real_path = os.path.abspath(os.path.join(CWD, path))
    with open(real_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    start = max(0, (offset or 1) - 1)
    end = start + limit if limit is not None else len(lines)
    selected = lines[start:end]
    return "".join(selected)


def tool_write_file(path: str, content: str) -> str:
    real_path = os.path.abspath(os.path.join(CWD, path))
    os.makedirs(os.path.dirname(real_path) or ".", exist_ok=True)
    with open(real_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {len(content)} bytes to {real_path}"


def tool_edit_file(path: str, old_string: str, new_string: str, count: Optional[int] = None) -> str:
    real_path = os.path.abspath(os.path.join(CWD, path))
    with open(real_path, "r", encoding="utf-8", errors="replace") as f:
        data = f.read()
    if count is None:
        new_data = data.replace(old_string, new_string)
        replaced = data.count(old_string)
    else:
        new_data = data.replace(old_string, new_string, max(0, count))
        # count only up to the first count occurrences
        replaced = min(data.count(old_string), max(0, count))
    with open(real_path, "w", encoding="utf-8") as f:
        f.write(new_data)
    return f"Replaced {replaced} occurrence(s) in {real_path}"


def tool_append_file(path: str, content: str) -> str:
    real_path = os.path.abspath(os.path.join(CWD, path))
    os.makedirs(os.path.dirname(real_path) or ".", exist_ok=True)
    with open(real_path, "a", encoding="utf-8") as f:
        f.write(content)
    return f"Appended {len(content)} bytes to {real_path}"


def tool_run_shell(command: str, timeout: Optional[int] = None, cwd: Optional[str] = None) -> str:
    run_cwd = cwd or CWD
    if APPROVE_SHELL:
        print(f"[shell] {command}")
        resp = input("Approve? [y/N] ").strip().lower()
        if resp not in ("y", "yes"):
            return "Shell command rejected by user."
    try:
        completed = subprocess.run(
            command,
            cwd=run_cwd,
            shell=True,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout if timeout and timeout > 0 else None,
            env=os.environ.copy(),
        )
        return completed.stdout
    except subprocess.TimeoutExpired as e:
        return f"Command timed out after {timeout}s.\nPartial output:\n{e.output or ''}"
    except Exception as e:
        return f"Shell error: {e}"


def tool_glob(pattern: str) -> str:
    real_pattern = os.path.join(CWD, pattern)
    matches = sorted(globlib.glob(real_pattern, recursive=True))
    rels = [os.path.relpath(m, CWD) for m in matches]
    return "\n".join(rels)


def tool_grep(pattern: str, path: str = ".", ignore_case: bool = True) -> str:
    flags = re.IGNORECASE if ignore_case else 0
    root = os.path.abspath(os.path.join(CWD, path))
    out = []
    for base, dirs, files in os.walk(root):
        for fn in files:
            fp = os.path.join(base, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if re.search(pattern, line, flags):
                            rel = os.path.relpath(fp, CWD)
                            out.append(f"{rel}:{i}:{line.rstrip()}")
            except Exception:
                pass
    return "\n".join(out)


def tool_diff(a_path: str, b_path: str) -> str:
    a_real = os.path.abspath(os.path.join(CWD, a_path))
    b_real = os.path.abspath(os.path.join(CWD, b_path))
    with open(a_real, "r", encoding="utf-8", errors="replace") as fa:
        a_lines = fa.readlines()
    with open(b_real, "r", encoding="utf-8", errors="replace") as fb:
        b_lines = fb.readlines()
    diff_lines = difflib.unified_diff(a_lines, b_lines, fromfile=a_path, tofile=b_path)
    return "".join(diff_lines)


def tool_http_get(url: str, timeout: int = 30) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TrashClaw/0.2"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            data = resp.read().decode(charset, errors="replace")
            return data
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code} - {e.reason}"
    except Exception as e:
        return f"Fetch error: {e}"


# ── Tool Schema ──

TOOLS: List[Dict[str, Any]] = [
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
                    "old_string": {"type": "string", "description": "Exact string to replace"},
                    "new_string": {"type": "string", "description": "Replacement text"},
                    "count": {"type": "integer", "description": "Max replacements (optional)"}
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "append_file",
            "description": "Append text to a file (creates file if missing).",
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
            "name": "run_shell",
            "description": "Run a shell command in the current working directory.",
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
            "name": "glob",
            "description": "List files matching a glob pattern. Supports ** for recursion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search files under a path for a regex pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string"},
                    "ignore_case": {"type": "boolean"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "diff",
            "description": "Unified diff between two files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "a_path": {"type": "string"},
                    "b_path": {"type": "string"}
                },
                "required": ["a_path", "b_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "http_get",
            "description": "Fetch a URL (GET).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "timeout": {"type": "integer"}
                },
                "required": ["url"]
            }
        }
    }
]

# Map tool name -> function
TOOL_FUNCS = {
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "edit_file": tool_edit_file,
    "append_file": tool_append_file,
    "run_shell": tool_run_shell,
    "glob": tool_glob,
    "grep": tool_grep,
    "diff": tool_diff,
    "http_get": tool_http_get,
}

# ── LLM Chat ──

def llm_chat(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.2,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    try:
        data = http_post_json(f"{LLAMA_URL.rstrip('/')}/v1/chat/completions", payload)
    except Exception as e:
        raise RuntimeError(f"LLM request failed: {e}")
    if not data.get("choices"):
        raise RuntimeError("No choices from LLM")
    choice = data["choices"][0]
    msg = choice.get("message", {})
    return msg


def run_tools_if_any(assistant_msg: Dict[str, Any]) -> Optional[str]:
    tool_calls = assistant_msg.get("tool_calls") or []
    if not tool_calls:
        return None

    tool_results = []
    for call in tool_calls:
        fn = (call.get("function") or {}).get("name")
        args_str = (call.get("function") or {}).get("arguments") or "{}"
        try:
            args = json.loads(args_str) if isinstance(args_str, str) else (args_str or {})
        except Exception:
            args = {}
        impl = TOOL_FUNCS.get(fn)
        if not impl:
            result = f"Unknown tool: {fn}"
        else:
            try:
                result = impl(**args)
            except TypeError:
                # fallback if kwargs mismatch
                try:
                    result = impl(*args.values())
                except Exception as e:
                    result = f"Tool invocation error: {e}"
            except Exception as e:
                result = f"Tool error: {e}"
        tool_results.append((call.get("id") or fn or "tool", result))
        HISTORY.append({
            "role": "tool",
            "tool_call_id": call.get("id"),
            "name": fn,
            "content": clamp_text(str(result)),
        })
    # After executing tools, ask the model to continue
    return "ok"


def agent_rounds() -> Optional[str]:
    # Drive tool-use rounds until the model produces a final message
    for _ in range(MAX_TOOL_ROUNDS):
        msg = llm_chat(HISTORY, tools=TOOLS)
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []
        HISTORY.append({"role": "assistant", "content": content, "tool_calls": tool_calls} if tool_calls else {"role": "assistant", "content": content})
        if tool_calls:
            run_tools_if_any(msg)
            continue
        # No tool calls, final answer
        return content
    return "[max tool rounds reached]"


# ── Session Save/Load ──

def session_dir() -> str:
    d = os.path.expanduser("~/.trashclaw/sessions")
    os.makedirs(d, exist_ok=True)
    return d


def sanitize_session_name(name: str) -> str:
    # Allow alphanum, dash, underscore, dot
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    safe = safe.strip("._") or "session"
    # Prevent sneaky paths
    safe = os.path.basename(safe)
    return safe


def save_session(name: str) -> None:
    if not name or not name.strip():
        print("Usage: /save <name>")
        return
    if not HISTORY:
        print("Nothing to save: history is empty.")
        return
    safe = sanitize_session_name(name)
    path = os.path.join(session_dir(), f"{safe}.json")
    data = {
        "version": "0.2",
        "saved_at": now_iso(),
        "model": MODEL_NAME,
        "cwd": CWD,
        "history": HISTORY,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved session '{safe}' ({len(HISTORY)} messages) to {path}")


def load_session(name: str) -> None:
    if not name or not name.strip():
        print("Usage: /load <name>")
        return
    safe = sanitize_session_name(name)
    path = os.path.join(session_dir(), f"{safe}.json")
    if not os.path.exists(path):
        print(f"Session not found: {safe}")
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        loaded = data.get("history") if isinstance(data, dict) else None
        if loaded is None and isinstance(data, list):
            loaded = data
        if not isinstance(loaded, list):
            print("Invalid session file format.")
            return
        # Replace in place to keep references
        HISTORY.clear()
        for m in loaded:
            if isinstance(m, dict) and "role" in m and "content" in m or m.get("tool_calls"):
                HISTORY.append(m)
        print(f"Loaded session '{safe}' with {len(HISTORY)} messages.")
    except Exception as e:
        print(f"Failed to load session: {e}")


def list_sessions() -> None:
    d = session_dir()
    files = sorted([f for f in os.listdir(d) if f.endswith(".json")])
    if not files:
        print("(no saved sessions)")
        return
    for fn in files:
        name = fn[:-5]
        fp = os.path.join(d, fn)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M")
            size = os.path.getsize(fp)
            print(f"{name}\t{mtime}\t{size}B")
        except Exception:
            print(name)


def handle_slash_command(line: str) -> bool:
    line = line.strip()
    if not line.startswith("/"):
        return False
    parts = line.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "/save":
        save_session(arg)
        return True
    if cmd == "/load":
        load_session(arg)
        return True
    if cmd == "/sessions":
        list_sessions()
        return True
    if cmd == "/cd":
        target = arg or os.path.expanduser("~")
        try:
            os.chdir(target)
            global CWD
            CWD = os.getcwd()
            print(CWD)
        except Exception as e:
            print(f"cd: {e}")
        return True
    if cmd == "/pwd":
        print(CWD)
        return True
    if cmd in ("/q", "/quit", "/exit"):
        print("bye.")
        sys.exit(0)
    if cmd in ("/help", "/h", "/?"):
        print("Commands:")
        print("  /save <name>      Save current conversation to ~/.trashclaw/sessions/<name>.json")
        print("  /load <name>      Load conversation from ~/.trashclaw/sessions/<name>.json")
        print("  /sessions         List saved sessions")
        print("  /cd [dir]         Change directory")
        print("  /pwd              Print current directory")
        print("  /quit             Exit")
        return True
    return False


# ── REPL ──

PROMPT = "» "

def print_banner():
    print("TrashClaw v0.2 — Local Tool-Use Agent")
    print("Model:", MODEL_NAME, "| Endpoint:", LLAMA_URL)
    print("Type your request. Use /help for commands.")


def add_user_message(text: str) -> None:
    HISTORY.append({"role": "user", "content": text})


def repl():
    print_banner()
    while True:
        try:
            line = input(PROMPT)
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            continue
        line = line.rstrip("\n")
        if not line.strip():
            continue
        # Slash commands
        if handle_slash_command(line):
            continue
        # Regular conversation
        add_user_message(line)
        try:
            out = agent_rounds()
        except Exception as e:
            print_err(f"[error] {e}")
            if os.environ.get("TRASHCLAW_TRACE", "0") == "1":
                traceback.print_exc()
            continue
        if out:
            print(clamp_text(out))


# ── Entry ──

def main(argv: List[str]) -> int:
    # If user passed -c/--command on CLI, run one-shot
    if len(argv) > 1:
        text = " ".join(argv[1:])
        if text.startswith("/"):
            handled = handle_slash_command(text)
            return 0 if handled else 1
        add_user_message(text)
        try:
            out = agent_rounds()
        except Exception as e:
            print_err(f"[error] {e}")
            return 1
        if out:
            print(clamp_text(out))
        return 0
    # Interactive
    repl()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))