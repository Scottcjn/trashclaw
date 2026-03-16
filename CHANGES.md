# TrashClaw Changelog

## v0.2.1 (Unreleased)

### Added
- Multi-LLM backend support: automatic detection of Ollama, LM Studio/OpenAI-compatible, and llama-server backends.
- vLLM compatibility: works with any OpenAI-compatible endpoint (including local vLLM instances).
- Enhanced tool descriptions and error handling.

### Changed
- Refactored backend detection to try Ollama first, then OpenAI-compatible endpoints, falling back to llama-server.
- Improved `_try_parse_tool_calls_from_text` to handle more varied output formats.
- Updated `llm_request` to use standard OpenAI chat completions endpoint.

### Fixed
- Fixed issue where tool calls in plain text were not being parsed correctly.
- Fixed path resolution for relative paths.
- Various minor bug fixes and stability improvements.

## v0.2.0

### Added
- Initial release of TrashClaw v0.2 with full OpenClaw-style tool-use loop.
- Built-in tools: read_file, write_file, edit_file, run_command, search_files, find_files, list_dir, think.
- Agent loop with tool calling, thinking, and slash commands.
- Pure Python stdlib implementation, zero external dependencies.
