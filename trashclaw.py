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
HISTORY: List[Dict] = []

# Backend detection
BACKEND_TYPE = None  # Will be set to: llama-server, ollama, lmstudio, or openai

def detect_backend() -> str:
    """Detect the type of LLM server running at LLAMA_URL."""
    global BACKEND_TYPE
    if BACKEND_TYPE is not None:
        return BACKEND_TYPE
    
    try:
        # Check if it's Ollama by looking for /api/tags
        ollama_url = LLAMA_URL.rstrip('/') + '/api/tags'
        req = urllib.request.Request(ollama_url)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if 'models' in data:
                    BACKEND_TYPE = 'ollama'
                    return BACKEND_TYPE
        except urllib.error.HTTPError:
            pass  # Not Ollama, try next
        
        # Check if it's LM Studio or OpenAI compatible
        # Try the standard OpenAI endpoint
        openai_url = LLAMA_URL.rstrip('/') + '/v1/models'
        req = urllib.request.Request(openai_url)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if 'data' in data and isinstance(data.get('data'), list):
                    BACKEND_TYPE = 'openai'
                    return BACKEND_TYPE
        except urllib.error.HTTPError:
            pass
        
        # Fallback to llama-server (original behavior)
        BACKEND_TYPE = 'llama-server'
        return BACKEND_TYPE
    except Exception as e:
        # Default to llama-server on any error
        BACKEND_TYPE = 'llama-server'
        return BACKEND_TYPE
# ── Tool Definitions ────# ── Tool Definitions ──

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
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=CWD, env={**os.environ, "PATH": os.environ.get("PATH", "") + ":/usr/local/bin"}
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


def tool_think(thought: str) -> str:
    return f"[Thought recorded, no side effects]"


# Tool dispatch
TOOL_DISPATCH = {
    "read_file": lambda args: tool_read_file(args["path"], args.get("offset"), args.get("limit")),
    "write_file": lambda args: tool_write_file(args["path"], args["content"]),
    "edit_file": lambda args: tool_edit_file(args["path"], args["old_string"], args["new_string"]),
    "run_command": lambda args: tool_run_command(args["command"], args.get("timeout", 30)),
    "search_files": lambda args: tool_search_files(args["pattern"], args.get("path"), args.get("glob_filter")),
    "find_files": lambda args: tool_find_files(args["pattern"], args.get("path")),
    "list_dir": lambda args: tool_list_dir(args.get("path")),
    "think": lambda args: tool_think(args["thought"]),
}


# ── LLM Client ──

SYSTEM_PROMPT = """You are TrashClaw, a general-purpose local agent running on the user's machine.

You can accomplish any task that involves files, commands, or information on this system.
You are not limited to coding — you handle research, system administration, file management,
data processing, automation, and anything else the user asks.

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
    """Send request to llama-server and return the full response."""
    payload = {
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
        "stream": False,
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
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return {"error": f"Cannot reach llama-server: {e}"}
    except Exception as e:
        return {"error": f"LLM request failed: {e}"}


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
    HISTORY.append({"role": "user", "content": user_message})

    for round_num in range(MAX_TOOL_ROUNDS):
        # Build messages
        sys_prompt = SYSTEM_PROMPT.format(cwd=CWD)
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
        print(f"  Max rounds: {MAX_TOOL_ROUNDS}")
        print(f"  Shell approval: {'on' if APPROVE_SHELL else 'off'}")

    elif command == "/compact":
        # Keep only last 10 messages
        old_len = len(HISTORY)
        HISTORY[:] = HISTORY[-10:]
        print(f"  Compacted {old_len} -> {len(HISTORY)} messages")

    elif command == "/help":
        print("""
  \033[1mTrashClaw Agent Commands\033[0m

  /cd <dir>      Change working directory
  /clear         Clear all conversation context
  /compact       Keep only last 10 messages (saves context)
  /status        Show server, model, and context info
  /exit          Exit TrashClaw
  /help          Show this help

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
    print("""
\033[36m ████████╗██████╗  █████╗ ███████╗██╗  ██╗ ██████╗██╗      █████╗ ██╗    ██╗
 ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║  ██║██╔════╝██║     ██╔══██╗██║    ██║
    ██║   ██████╔╝███████║███████╗███████║██║     ██║     ███████║██║ █╗ ██║
    ██║   ██╔══██╗██╔══██║╚════██║██╔══██║██║     ██║     ██╔══██║██║███╗██║
    ██║   ██║  ██║██║  ██║███████║██║  ██║╚██████╗███████╗██║  ██║╚███╔███╔╝
    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝\033[0m

    \033[1mElyan Labs\033[0m | Mac Pro Trashcan Edition | v0.2
    General-purpose agent — files, commands, search, automation, anything local.
    Model: {model} | CWD: {cwd}
    Type /help for commands, or just describe what you want to do.
""".format(model=MODEL_NAME, cwd=CWD))


def main():
    global CWD

    # Parse --cwd argument
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

    banner()

    # Check server
    try:
        req = urllib.request.Request(f"{LLAMA_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        if health.get("status") != "ok":
            print(f"\033[33m[WARN]\033[0m Server status: {health}")
    except Exception:
        print(f"\033[31m[ERROR]\033[0m Cannot reach llama-server at {LLAMA_URL}")
        print("  Start it with:")
        print("  llama-server -m <model.gguf> --host 0.0.0.0 --port 8080 -t 10 -c 4096")
        sys.exit(1)

    print(f"  \033[32mConnected to {LLAMA_URL}\033[0m\n")

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
