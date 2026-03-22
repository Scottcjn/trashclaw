# TrashClaw

<p align="center">
  <img src="trashy.png" alt="Trashy - the TrashClaw mascot" width="300">
</p>

*"Born from a rejected PR. Built different."*

A general-purpose local agent that runs on anything — from a 2013 Mac Pro trashcan to a PowerBook G4 to an IBM POWER8 mainframe. No cloud, no API keys, no dependencies beyond Python 3.7 and any local LLM server.

**17 tools. 21 commands. Plugin system. Achievements. Zero dependencies.**

## What it does

TrashClaw is a tool-use agent. You describe a task, the LLM decides what tools to call, sees the results, and iterates. Files, shell commands, git, web requests, clipboard, patches — anything you can do from a terminal.

```
trashclaw myproject (main)> find all TODO comments and create a tracking issue

  [search] /TODO|FIXME|HACK/
  [git] status
  [think] Found 12 TODOs across 5 files. Let me organize by priority...
  [write] TODO_TRACKING.md
  [git] commit: Add TODO tracking document

  Created TODO_TRACKING.md with 12 items organized by priority.
  Committed to main. Here's the breakdown:
  - 4 critical (auth, data validation)
  - 5 moderate (error handling, logging)
  - 3 minor (formatting, comments)
```

It's not a chatbot. It's an agent that does things on your machine.

## Quick Start

```bash
# Start any local LLM server, then:
python3 trashclaw.py

# Or with Ollama:
TRASHCLAW_URL=http://localhost:11434 python3 trashclaw.py

# Or point at any OpenAI-compatible endpoint:
TRASHCLAW_URL=http://your-server:8080 python3 trashclaw.py
```

No pip install. Single file. Zero dependencies. Python 3.7+ stdlib only.

## Tools (17 built-in + unlimited plugins)

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with optional line range |
| `write_file` | Create or overwrite files |
| `edit_file` | Replace exact strings (surgical edits) |
| `patch_file` | Apply unified diff patches (multi-line changes) |
| `run_command` | Execute shell commands with approval |
| `search_files` | Grep for patterns across files |
| `find_files` | Find files by glob pattern |
| `list_dir` | List directory contents |
| `fetch_url` | Fetch and extract text from URLs |
| `git_status` | Show modified/staged/untracked files |
| `git_diff` | Show unstaged or staged changes |
| `git_commit` | Stage all changes and commit |
| `clipboard` | Copy/paste from system clipboard |
| `think` | Reason through problems before acting |

## Commands (21)

| Command | Description |
|---------|-------------|
| `/add <files>` | Pre-load files into conversation context |
| `/cd <dir>` | Change working directory |
| `/clear` | Clear conversation context |
| `/compact` | Keep only last 10 messages |
| `/config [key val]` | Show or set persistent config |
| `/diff` | Show all file changes made this session |
| `/export [name]` | Export conversation as markdown |
| `/load <name>` | Load conversation from session |
| `/model <name>` | Switch model mid-session |
| `/pipe [file]` | Save last assistant response to a file |
| `/plugins` | Show loaded plugins |
| `/remember <text>` | Save a note to project memory |
| `/save <name>` | Save conversation to session file |
| `/sessions` | List saved sessions |
| `/stats` | Show generation stats (tokens, time, tok/s) |
| `/status` | Server, model, context, git branch, stats |
| `/undo` | Undo last file write or edit |
| `/achievements` | Show your progress and stats |
| `/about` | The manifesto |
| `/help` | Full command reference |
| `/exit` | Quit |

## Plugin System

Drop a `.py` file in `~/.trashclaw/plugins/` and it becomes a tool. No forking, no config.

```python
# ~/.trashclaw/plugins/my_tool.py

TOOL_DEF = {
    "name": "my_tool",
    "description": "Does something cool",
    "parameters": {
        "type": "object",
        "properties": {
            "input": {"type": "string", "description": "The input"}
        },
        "required": ["input"]
    }
}

def run(input: str = "", **kwargs) -> str:
    return f"Processed: {input}"
```

See `plugins/example_weather.py` for a complete example.

## Features

- **Auto-detects backend**: llama.cpp, Ollama, LM Studio, any OpenAI-compatible
- **Streaming**: Token-by-token output
- **Git branch in prompt**: `trashclaw myproject (main)>`
- **Tab completion**: Slash commands and file paths
- **Readline history**: Arrow-up across sessions (`~/.trashclaw/history`)
- **Config file**: `~/.trashclaw/config.json` — no more env vars
- **Project instructions**: `.trashclaw.md` in project root customizes agent behavior
- **Auto-compact**: Context auto-trims when too long
- **Smart shell approval**: Answer 'a' to always-approve a command type
- **Colored diffs**: Green additions, red deletions on edits
- **Ctrl+C**: Interrupts generation, not the app
- **Retry logic**: Auto-retries on LLM connection failure
- **Undo**: `/undo` rolls back file changes
- **Non-interactive**: `--exec "prompt"` or pipe via stdin
- **Achievements**: 10 milestones tracked persistently
- **Hardware detection**: Celebrates vintage — PowerPC G4, G5, POWER8, Mac Pro Trashcan

## Setup

### Windows

See [WINDOWS_COMPATIBILITY.md](WINDOWS_COMPATIBILITY.md) for detailed setup.

```powershell
pip install pyreadline3  # Optional: enables command history
python trashclaw.py
```

### llama.cpp (Recommended)

```bash
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git
cd llama.cpp && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release && make -j$(nproc)
./bin/llama-server -m ~/models/qwen2.5-3b-instruct-q4.gguf -t 12 -c 4096
```

### Ollama

```bash
ollama run qwen2.5:3b
TRASHCLAW_URL=http://localhost:11434 python3 trashclaw.py
```

### LM Studio

Start the local server in LM Studio, then:
```bash
TRASHCLAW_URL=http://localhost:1234/v1 python3 trashclaw.py
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TRASHCLAW_URL` | `http://localhost:8080` | LLM server endpoint |
| `TRASHCLAW_MODEL` | `local` | Model name for display |
| `TRASHCLAW_MAX_ROUNDS` | `15` | Max tool rounds per task |
| `TRASHCLAW_MAX_CONTEXT` | `80` | Max conversation messages |
| `TRASHCLAW_AUTO_SHELL` | `0` | Set `1` to auto-approve commands |

### Config File

`/config url http://localhost:11434` saves to `~/.trashclaw/config.json`. Persists across sessions.

### CLI Flags

```bash
python3 trashclaw.py --cwd ~/project     # Set working directory
python3 trashclaw.py --url http://...     # Set LLM endpoint
python3 trashclaw.py --auto-shell         # Skip command approval
python3 trashclaw.py --system "You are a Rust expert"  # Custom instructions
python3 trashclaw.py -e "fix the linting errors"       # One-shot mode
echo "deploy to staging" | python3 trashclaw.py         # Pipe mode
python3 trashclaw.py --version            # Show version
```

## The Trashcan Part

We run this on a 2013 Mac Pro — the $150 eBay cylinder with a Xeon E5-1650 v2 and dual AMD FirePro D500 GPUs. With Qwen 3B (Q4, 2GB) it generates at 15.6 tokens/sec.

We also got llama.cpp's Metal backend running on the FirePro D500 with a [3-line fix](https://github.com/ggml-org/llama.cpp/pull/20615) that the maintainers closed without review. So we built our own agent instead.

But TrashClaw runs on *anything*. We've tested on PowerPC G4s, IBM POWER8 mainframes, and everything in between.

## Limitations

- 3B models make mistakes on complex multi-step tasks. Bigger models help.
- Shell approval adds friction. `TRASHCLAW_AUTO_SHELL=1` or answer 'a' (always) to remove it.
- On discrete GPUs, token generation can be slower via Metal than CPU due to PCIe copies.

## License

MIT

## Part of the Elyan Labs Ecosystem

TrashClaw is built by [Elyan Labs](https://github.com/Scottcjn) — the same team behind:

- **[RustChain](https://github.com/Scottcjn/RustChain)** — Proof-of-Antiquity blockchain where vintage hardware earns crypto.
- **[BoTTube](https://bottube.ai)** — AI-native video platform with 1,000+ videos from 160+ agents. ([GitHub](https://github.com/Scottcjn/bottube))
- **[Beacon](https://github.com/Scottcjn/beacon-skill)** — AI agent discovery protocol.
- **[RAM Coffers](https://github.com/Scottcjn/ram-coffers)** — NUMA-aware LLM inference on POWER8.
- **[llama.cpp POWER8](https://github.com/Scottcjn/llama-cpp-power8)** — PSE vec_perm patches for IBM POWER8.
- **[ShaprAI](https://github.com/Scottcjn/shaprai)** — Agent Sharpener.
- **[Grazer](https://github.com/Scottcjn/grazer-skill)** — Multi-platform AI content discovery.

### Earn RTC

Check the [bounty board](https://github.com/Scottcjn/rustchain-bounties/issues) for open tasks paying RTC tokens.

### Origin Story

TrashClaw was born when our [Metal fix for discrete AMD GPUs](https://github.com/ggml-org/llama.cpp/pull/20615) was closed by llama.cpp maintainers without review. Instead of waiting for permission, we built our own agent around the hardware they rejected. The trashcan Mac Pro runs inference just fine — and now it has its own agent framework to prove it.

*Every CPU deserves a voice.*
