#!/usr/bin/env python3
"""
TrashClaw v0.1 — Local LLM Agent for Mac Pro Trashcan
=====================================================
A Claude Code-inspired agent powered by a local llama.cpp server
running on dual AMD FirePro D500s (coming soon) or Xeon E5-1650 v2.

Built by Elyan Labs. Runs on a 2013 Mac Pro trashcan because we can.

Zero dependencies — uses only Python stdlib. Works on Python 3.7+,
including macOS Leopard's broken-SSL Python.
"""

import os
import sys
import json
import subprocess
import readline
import urllib.request
import urllib.error
from datetime import datetime

# ── Config ──
LLAMA_URL = os.environ.get("TRASHCLAW_URL", "http://localhost:8080")
MODEL_NAME = "TinyLlama 1.1B"
SYSTEM_PROMPT = """You are TrashClaw, a helpful coding assistant running locally on a 2013 Mac Pro (trashcan).
You have access to the local filesystem and can run shell commands.
You are part of the Elyan Labs ecosystem — RustChain, BoTTube, Sophiacord.
Be concise and direct. You're running on vintage hardware, so keep responses efficient.
When asked to run commands, output them in ```bash blocks.
When asked to read files, use cat or head."""

MAX_CONTEXT = 2048
HISTORY = []


def llm_complete(messages, temperature=0.7, max_tokens=512):
    """Send chat completion to local llama-server."""
    payload = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{LLAMA_URL}/v1/chat/completions",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
    except urllib.error.URLError as e:
        return f"[ERROR] Cannot reach llama-server at {LLAMA_URL}: {e}"
    except Exception as e:
        return f"[ERROR] LLM request failed: {e}"


def run_command(cmd):
    """Execute a shell command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        output = result.stdout
        if result.stderr:
            output += "\n[stderr] " + result.stderr
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "[ERROR] Command timed out after 30s"
    except Exception as e:
        return f"[ERROR] {e}"


def read_file(path):
    """Read a file and return contents."""
    try:
        with open(os.path.expanduser(path), "r") as f:
            content = f.read()
        if len(content) > 4000:
            content = content[:4000] + f"\n... [truncated, {len(content)} bytes total]"
        return content
    except Exception as e:
        return f"[ERROR] Cannot read {path}: {e}"


def handle_slash_command(cmd):
    """Handle slash commands."""
    parts = cmd.strip().split(None, 1)
    command = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if command in ("/exit", "/quit", "/q"):
        print("\nTrashClaw out. Keep the trashcan warm.")
        sys.exit(0)

    elif command == "/run":
        if not arg:
            print("Usage: /run <command>")
            return None
        print(f"  Running: {arg}")
        output = run_command(arg)
        print(output)
        return None

    elif command == "/read":
        if not arg:
            print("Usage: /read <filepath>")
            return None
        content = read_file(arg)
        print(content)
        return None

    elif command == "/clear":
        HISTORY.clear()
        print("  Context cleared.")
        return None

    elif command == "/status":
        try:
            req = urllib.request.Request(f"{LLAMA_URL}/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                health = json.loads(resp.read().decode("utf-8"))
            print(f"  Server: {health.get('status', 'unknown')}")
        except Exception:
            print("  Server: unreachable")
        print(f"  Model: {MODEL_NAME}")
        print(f"  Context: {len(HISTORY)} messages")
        print(f"  CWD: {os.getcwd()}")
        return None

    elif command == "/help":
        print("""
  TrashClaw Commands:
    /run <cmd>     Run a shell command
    /read <file>   Read a file
    /clear         Clear conversation context
    /status        Check server and context status
    /exit          Exit TrashClaw
    /help          Show this help

  Or just type naturally — TrashClaw will respond using the local LLM.
        """)
        return None

    else:
        print(f"  Unknown command: {command}. Try /help")
        return None


def extract_and_offer_commands(response):
    """If the LLM suggests bash commands, offer to run them."""
    import re
    blocks = re.findall(r'```(?:bash|sh)?\n(.*?)```', response, re.DOTALL)
    if not blocks:
        return

    for block in blocks:
        commands = [l.strip() for l in block.strip().split('\n') if l.strip() and not l.strip().startswith('#')]
        for cmd in commands:
            try:
                answer = input(f"  Run `{cmd}`? [y/N] ").strip().lower()
            except EOFError:
                return
            if answer in ('y', 'yes'):
                output = run_command(cmd)
                print(output)
                HISTORY.append({"role": "user", "content": f"Command output:\n{output}"})


def banner():
    print("""
 ████████╗██████╗  █████╗ ███████╗██╗  ██╗ ██████╗██╗      █████╗ ██╗    ██╗
 ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║  ██║██╔════╝██║     ██╔══██╗██║    ██║
    ██║   ██████╔╝███████║███████╗███████║██║     ██║     ███████║██║ █╗ ██║
    ██║   ██╔══██╗██╔══██║╚════██║██╔══██║██║     ██║     ██╔══██║██║███╗██║
    ██║   ██║  ██║██║  ██║███████║██║  ██║╚██████╗███████╗██║  ██║╚███╔███╔╝
    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝

    Elyan Labs | Mac Pro Trashcan Edition | {model}
    Xeon E5-1650 v2 | Dual FirePro D500 | {date}
    Type /help for commands, or just start talking.
""".format(model=MODEL_NAME, date=datetime.now().strftime("%Y-%m-%d %H:%M")))


def main():
    banner()

    # Check server health
    try:
        req = urllib.request.Request(f"{LLAMA_URL}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        if health.get("status") != "ok":
            print(f"[WARN] Server status: {health}")
    except Exception:
        print(f"[ERROR] Cannot reach llama-server at {LLAMA_URL}")
        print("  Start it with:")
        print("  ~/llama.cpp/build/bin/llama-server -m ~/models/tinyllama-1.1b-q4.gguf -t 10 -c 2048")
        sys.exit(1)

    while True:
        try:
            user_input = input("\ntrashclaw> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTrashClaw out.")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            handle_slash_command(user_input)
            continue

        HISTORY.append({"role": "user", "content": user_input})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        context_msgs = HISTORY[-20:]
        messages.extend(context_msgs)

        print("  thinking...", end="", flush=True)
        response = llm_complete(messages)
        print("\r" + " " * 20 + "\r", end="")

        HISTORY.append({"role": "assistant", "content": response})
        print(f"\n{response}")

        extract_and_offer_commands(response)


if __name__ == "__main__":
    main()
