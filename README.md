# TrashClaw

A general-purpose local agent that runs on anything — including a 2013 Mac Pro that looks like a trash can. No cloud, no API keys, no dependencies beyond Python 3.7 and a llama-server.

Think OpenClaw but it runs on your old hardware.

## What it does

TrashClaw is a tool-use agent. You describe a task, the LLM decides what tools to call, sees the results, and iterates. It handles files, shell commands, web requests, data processing, system admin — anything you can do from a terminal.

```
trashclaw ~> find all large files on this machine over 1GB and summarize them

  [run] find / -type f -size +1G 2>/dev/null [y/N] y
  [think] Found 8 large files. Let me categorize them...

  Here's what's taking up space:
  - /Users/sophia/models/qwen2.5-3b-instruct-q4.gguf (2.0GB) — LLM model
  - /Library/Developer/... (4.2GB) — Xcode command line tools
  - /System/Library/... (1.8GB) — macOS system files
  Total: 8.0GB across 8 files. The model file is the only user-removable one.

trashclaw ~> check if my web server is responding and show me the last 5 errors

  [run] curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/health [y/N] y
  [run] grep -i error ~/server.log | tail -5 [y/N] y

  Server is up (200). Last 5 errors were all timeout-related, most recent 2 hours ago.
```

It's not a chatbot. It's an agent that does things on your machine.

## How it works

1. You describe a task in natural language
2. The LLM picks from 8 tools: `read_file`, `write_file`, `edit_file`, `run_command`, `search_files`, `find_files`, `list_dir`, `think`
3. Tools execute locally, results go back to the LLM
4. Repeat up to 15 rounds until the task is done
5. Shell commands require your approval (configurable)

Tool calls are parsed three ways for broad model compatibility:
- Native function calling (Qwen 2.5, Llama 3.1+, Mistral)
- `<tool_call>` XML tags
- JSON in text (fallback for smaller models)

## Setup

TrashClaw automatically detects the backend you are using (llama-server, Ollama, or LM Studio) and formats tool requests accordingly.

### Option 1: Ollama (Easiest)
```bash
# Start Ollama and run a model that supports tool use
ollama run qwen2.5:3b

# In a new terminal, run TrashClaw (Ollama runs on port 11434 by default)
TRASHCLAW_URL=http://localhost:11434 python3 trashclaw.py
```

### Option 2: LM Studio
1. Open LM Studio and load a tool-compatible model.
2. Start the Local Server (ensure the port is 1234).
3. Run TrashClaw:
```bash
TRASHCLAW_URL=http://localhost:1234 python3 trashclaw.py
```

### Option 3: llama.cpp (Raw)
```bash
# Build llama.cpp
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git
cd llama.cpp && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release && make -j$(nproc)

# Start the server with your model
./bin/llama-server -m ~/models/qwen2.5-3b-instruct-q4.gguf -t 12 -c 4096

# Run TrashClaw
python3 trashclaw.py
```

No pip install. Single file, zero dependencies, Python 3.7+ stdlib only.

## The trashcan part

We happen to run this on a 2013 Mac Pro — the $150 eBay cylinder with a Xeon E5-1650 v2 and dual AMD FirePro D500 GPUs.

With Qwen 3B (Q4, 2GB) it generates at 15.6 tokens/sec. Agent responses take about 2 seconds. It works.

We also got llama.cpp's Metal backend running on the FirePro D500, which was previously broken on all discrete AMD GPUs. The [3-line fix](https://github.com/ggml-org/llama.cpp/pull/20615) handles `StorageModeManaged` for non-unified memory. Prompt processing is 16% faster with Metal vs CPU-only on the 3B model.

But TrashClaw runs on anything. Point `TRASHCLAW_URL` at any server.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TRASHCLAW_URL` | `http://localhost:8080` | Any OpenAI-compatible endpoint |
| `TRASHCLAW_MAX_ROUNDS` | `15` | Max tool rounds per task |
| `TRASHCLAW_AUTO_SHELL` | `0` | Set `1` to auto-approve commands |

```bash
# Use a remote server
TRASHCLAW_URL=http://192.168.0.50:8080 python3 trashclaw.py

# Work in a specific directory, auto-approve commands
TRASHCLAW_AUTO_SHELL=1 python3 trashclaw.py --cwd ~/myproject
```

## Commands

| Command | Description |
|---------|-------------|
| `/cd <dir>` | Change working directory |
| `/clear` | Clear context |
| `/compact` | Trim to last 10 messages |
| `/status` | Server and context info |
| `/exit` | Quit |

## Limitations

- 3B models make mistakes on complex multi-step tasks. Bigger models help.
- No streaming yet — output appears after full generation.
- Shell approval adds friction. `TRASHCLAW_AUTO_SHELL=1` removes it but use with care.
- On discrete GPUs, token generation is slower via Metal than CPU due to PCIe copies.

## License

MIT
