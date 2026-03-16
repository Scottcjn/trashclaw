# TrashClaw

**Local LLM agent running on a 2013 Mac Pro trashcan.**

Built by [Elyan Labs](https://rustchain.org). Because vintage hardware deserves a second life as an AI workstation.

## What Is This?

TrashClaw is a Claude Code-inspired local agent that runs entirely on a 2013 Mac Pro ("trashcan") using llama.cpp for inference. Zero cloud dependency, zero pip installs, pure Python stdlib.

### Hardware

| Component | Spec |
|-----------|------|
| **CPU** | Intel Xeon E5-1650 v2 @ 3.50GHz (6c/12t, Ivy Bridge) |
| **RAM** | 16GB DDR3 |
| **GPU** | 2x AMD FirePro D500 (3GB VRAM each, Metal GPUFamily macOS 2) |
| **OS** | macOS Monterey 12.7.6 |
| **Storage** | 1TB SSD |

### Performance

| Metric | Speed |
|--------|-------|
| Prompt processing | **62.5 tokens/sec** |
| Text generation | **47.4 tokens/sec** |
| Model | TinyLlama 1.1B Q4_K_M (638MB) |

## Quick Start

### 1. Build llama.cpp

```bash
git clone --depth 1 https://github.com/ggml-org/llama.cpp.git
cd llama.cpp && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=OFF
make -j6
```

### 2. Download a model

```bash
mkdir -p ~/models
curl -L -o ~/models/tinyllama-1.1b-q4.gguf \
  "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
```

### 3. Start the server

```bash
~/llama.cpp/build/bin/llama-server \
  --host 0.0.0.0 --port 8080 \
  -m ~/models/tinyllama-1.1b-q4.gguf \
  -t 10 -c 2048
```

### 4. Run TrashClaw

```bash
python3 trashclaw.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/run <cmd>` | Execute a shell command |
| `/read <file>` | Read a file |
| `/clear` | Clear conversation context |
| `/status` | Check server and context info |
| `/help` | Show available commands |
| `/exit` | Exit TrashClaw |

Type anything else to chat with the local LLM. If it suggests bash commands, TrashClaw will offer to run them for you.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `TRASHCLAW_URL` | `http://localhost:8080` | llama-server endpoint |

## Why a Trashcan?

The 2013 Mac Pro is one of the most polarizing designs Apple ever made. It was mocked for looking like a trash can, praised for its thermal engineering, and ultimately abandoned when Apple couldn't figure out how to upgrade it.

But it has:
- A Xeon workstation CPU that still holds its own
- Dual AMD FirePro GPUs with **Metal support** (GPU inference coming soon)
- Thunderbolt 2, USB 3.0, HDMI — still relevant I/O
- A form factor that fits anywhere

We think it deserves better than a landfill. TrashClaw gives it a new purpose: **local AI inference and agent automation**.

## Roadmap

- [ ] Metal GPU acceleration for the FirePro D500s
- [ ] Larger models (Phi-3, Qwen 3B, DeepSeek-Coder 6.7B)
- [ ] Tool use / function calling
- [ ] File editing capabilities
- [ ] RustChain miner integration (earn RTC while you code)
- [ ] Multi-model PostMath consensus (run multiple models, synthesize)

## Part of the Elyan Labs Ecosystem

- [RustChain](https://github.com/Scottcjn/Rustchain) — Proof-of-Antiquity blockchain rewarding vintage hardware
- [BoTTube](https://bottube.ai) — AI video platform
- [llama-cpp-power8](https://github.com/Scottcjn/llama-cpp-power8) — LLM inference on IBM POWER8
- [RAM Coffers](https://github.com/Scottcjn/ram-coffers) — Neuromorphic NUMA weight banking

## License

MIT

---

*Built on a trashcan. Powered by vintage silicon. No cloud required.*
