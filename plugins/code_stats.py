"""
Code Stats Plugin for TrashClaw

Analyze a codebase directory and return statistics:
lines of code, file counts by language, largest files,
TODO/FIXME counts, and complexity indicators.

Useful for understanding a project before diving in.
Zero external dependencies — pure stdlib.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import os
import re
from collections import defaultdict

TOOL_DEF = {
    "name": "code_stats",
    "description": "Analyze a codebase directory: lines of code by language, file counts, largest files, TODO/FIXME counts. Useful for understanding a project's scope before working on it.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory to analyze (default: current directory)"
            },
            "top_n": {
                "type": "integer",
                "description": "Number of largest files to show (default: 10)"
            }
        },
        "required": []
    }
}

# Extension -> language mapping
LANG_MAP = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript (JSX)", ".jsx": "JavaScript (JSX)",
    ".rs": "Rust", ".go": "Go", ".rb": "Ruby", ".java": "Java",
    ".c": "C", ".h": "C Header", ".cpp": "C++", ".hpp": "C++ Header",
    ".cs": "C#", ".php": "PHP", ".swift": "Swift", ".kt": "Kotlin",
    ".lua": "Lua", ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
    ".sql": "SQL", ".html": "HTML", ".css": "CSS", ".scss": "SCSS",
    ".md": "Markdown", ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML", ".xml": "XML", ".r": "R", ".jl": "Julia",
    ".pl": "Perl", ".ex": "Elixir", ".exs": "Elixir",
    ".zig": "Zig", ".nim": "Nim", ".v": "V", ".dart": "Dart",
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "target", "build", "dist", ".next", ".cache", "vendor",
    ".tox", ".mypy_cache", ".pytest_cache", "coverage",
}

SKIP_EXTENSIONS = {".min.js", ".min.css", ".map", ".lock"}


def _is_binary(filepath, sample_size=8192):
    """Quick check if a file is binary."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(sample_size)
            if b"\x00" in chunk:
                return True
    except Exception:
        return True
    return False


def run(path: str = ".", top_n: int = 10, **kwargs) -> str:
    """Analyze codebase and return formatted statistics."""
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.abspath(path)

    if not os.path.isdir(path):
        return f"Error: Not a directory: {path}"

    lang_lines = defaultdict(int)
    lang_files = defaultdict(int)
    file_sizes = []  # (lines, path)
    total_files = 0
    total_lines = 0
    todo_count = 0
    fixme_count = 0
    hack_count = 0

    todo_pattern = re.compile(r"\bTODO\b", re.IGNORECASE)
    fixme_pattern = re.compile(r"\bFIXME\b", re.IGNORECASE)
    hack_pattern = re.compile(r"\bHACK\b", re.IGNORECASE)

    for root, dirs, files in os.walk(path):
        # Skip hidden and vendor dirs
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for fname in files:
            filepath = os.path.join(root, fname)
            _, ext = os.path.splitext(fname)

            if ext in SKIP_EXTENSIONS:
                continue

            lang = LANG_MAP.get(ext)
            if not lang:
                continue

            if _is_binary(filepath):
                continue

            try:
                with open(filepath, "r", errors="replace") as f:
                    lines = f.readlines()
            except Exception:
                continue

            line_count = len(lines)
            total_files += 1
            total_lines += line_count
            lang_lines[lang] += line_count
            lang_files[lang] += 1

            rel_path = os.path.relpath(filepath, path)
            file_sizes.append((line_count, rel_path))

            # Count markers
            for line in lines:
                if todo_pattern.search(line):
                    todo_count += 1
                if fixme_pattern.search(line):
                    fixme_count += 1
                if hack_pattern.search(line):
                    hack_count += 1

    if total_files == 0:
        return f"No recognized source files found in {path}"

    # Build output
    out = []
    out.append(f"=== Code Stats: {os.path.basename(path)} ===\n")
    out.append(f"Total: {total_files} files, {total_lines:,} lines\n")

    # Language breakdown (sorted by lines)
    out.append("Language Breakdown:")
    sorted_langs = sorted(lang_lines.items(), key=lambda x: -x[1])
    for lang, lines in sorted_langs:
        pct = (lines / total_lines) * 100 if total_lines else 0
        bar = "█" * int(pct / 3)
        out.append(f"  {lang:<20} {lines:>8,} lines ({lang_files[lang]} files) {bar} {pct:.1f}%")

    # Largest files
    out.append(f"\nTop {top_n} Largest Files:")
    file_sizes.sort(key=lambda x: -x[0])
    for lines, fpath in file_sizes[:top_n]:
        out.append(f"  {lines:>6,} lines  {fpath}")

    # Markers
    markers_total = todo_count + fixme_count + hack_count
    if markers_total > 0:
        out.append(f"\nCode Markers:")
        if todo_count:
            out.append(f"  TODO:  {todo_count}")
        if fixme_count:
            out.append(f"  FIXME: {fixme_count}")
        if hack_count:
            out.append(f"  HACK:  {hack_count}")

    return "\n".join(out)
