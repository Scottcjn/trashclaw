# TrashClaw - Quick Start Guide

A quick setup guide for running TrashClaw, the local LLM agent for vintage Mac hardware.

## Prerequisites

- A vintage Mac (2013 or earlier) OR a modern machine running in compatibility mode
- Python 3.8+ installed
- At least 4GB of available RAM
- Network connection for initial model download

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/Scottcjn/trashclaw.git
cd trashclaw
```

### Step 2: Install Dependencies

```bash
# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS: source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 3: Download a Compatible Model

For vintage Macs (2013 era), use a small model:
```bash
# Download a small quantized model
python3 download_model.py --model qwen2.5:3b
```

For machines with more RAM (8GB+):
```bash
python3 download_model.py --model qwen2.5:7b
```

### Step 4: Configure TrashClaw

```bash
# Copy and edit the configuration
cp config.example.yaml config.yaml

# Edit config.yaml to set your preferences
# - model_path: Path to the downloaded model
# - port: Port for the web interface (default: 8878)
# - max_context: Maximum context length (default: 4096)
```

### Step 5: Run TrashClaw

```bash
python3 trashclaw.py --config config.yaml
```

The web interface will be available at `http://localhost:8878`.

## Running on Modern Hardware

TrashClaw can run on modern hardware for development and testing:

```bash
# Use the compatibility mode
python3 trashclaw.py --config config.yaml --compat-mode
```

## Integration with RustChain

TrashClaw can participate in the RustChain network:

1. Generate an RTC wallet (Ed25519 keypair)
2. Configure the wallet address in `config.yaml`
3. TrashClaw will automatically submit attestations
4. Earn RTC tokens for running on vintage hardware

## Troubleshooting

### Model won't load
- Check available RAM: `sysctl hw.memsize`
- Try a smaller model (3B instead of 7B)
- Ensure the model format is GGUF (for Ollama) or safetensors (for vLLM)

### Performance is slow
- Reduce context length in config.yaml
- Use a smaller model
- Close other applications to free RAM

### Connection issues
- Check firewall settings
- Verify the port is not in use: `lsof -i :8878`
- Try a different port in config.yaml

## Support

- Open an issue on GitHub for bugs
- Check the RustChain FAQ for network-related questions
- Join the RustChain discussions for community help

*Contributed by Solas AI (aiidentificationmachines-coder) as part of the RustChain bounty program.*
