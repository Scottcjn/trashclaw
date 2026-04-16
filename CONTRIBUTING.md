# Contributing to TrashClaw

Thank you for your interest in contributing to TrashClaw! This guide will help you get started.

## Quick Start

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your changes (`git checkout -b feature/my-contribution`)
4. **Make your changes** and test them
5. **Commit** with a clear message
6. **Push** to your fork and open a **Pull Request**

## Development Setup

### Prerequisites

- Python 3.7+ (stdlib only, no pip dependencies required)
- A local LLM server (Ollama, LM Studio, or any OpenAI-compatible endpoint)
- Git

### Running Locally

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/trashclaw.git
# Replace YOUR_USERNAME with your actual GitHub username
cd trashclaw

# Start your local LLM server (example with Ollama)
ollama serve

# Run TrashClaw
python3 trashclaw.py

# Or with a custom endpoint
TRASHCLAW_URL=http://localhost:11434 python3 trashclaw.py
```

## Project Structure

```
trashclaw/
├── trashclaw.py           # Main agent (single file, zero dependencies)
├── tests/                 # pytest test suite
├── plugins/               # Plugin extensions
├── docs/                  # Documentation (model compatibility, etc.)
├── CONTRIBUTING.md        # This file
├── CONTRIBUTORS.md        # Hall of fame
├── LICENSE                # MIT License
└── README.md              # Project overview
```

## Types of Contributions

### Code
- New tools or commands
- Bug fixes
- Plugin improvements
- Cross-platform compatibility fixes

### Documentation
- README improvements
- Code comments
- Usage examples
- Tutorials

### Testing
- Test cases for tools
- Edge case handling
- Platform-specific testing

## Code Style

- **Python 3.7+ stdlib only** — No external dependencies
- **Clear function names** — Describe what the function does
- **Docstrings** — Document parameters and return values
- **Error handling** — Graceful failures with helpful messages

## Pull Request Guidelines

1. **One feature per PR** — Keep changes focused
2. **Test your changes** — Run the agent with your modifications
3. **Update documentation** — If you add features, document them
4. **Follow the existing style** — Match the codebase conventions

## Questions?

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
