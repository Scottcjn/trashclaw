"""
Word Count Plugin for TrashClaw

Count words, characters, lines, sentences, and paragraphs in text or a file.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str
"""

import os
import re

TOOL_DEF = {
    "name": "word_count",
    "description": "Count words, characters, lines, sentences, and paragraphs in text or a file.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to analyze"
            },
            "file": {
                "type": "string",
                "description": "Path to file to analyze (optional, used instead of text)"
            }
        },
        "required": []
    }
}


def _count(text: str) -> dict:
    lines = text.split("\n")
    words = text.split()
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    return {
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "").replace("\t", "")),
        "words": len(words),
        "lines": len(lines),
        "sentences": len(sentences),
        "paragraphs": len(paragraphs),
    }


def run(text: str = "", file: str = "", **kwargs) -> str:
    if file:
        if not os.path.exists(file):
            return f"Error: file not found: {file}"
        try:
            with open(file, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    if not text:
        return "Error: provide 'text' or 'file' to analyze."

    stats = _count(text)
    source = f" ({file})" if file else ""
    lines = [f"Word Count{source}:"]
    for key, val in stats.items():
        label = key.replace("_", " ").title()
        lines.append(f"  {label}: {val:,}")
    return "\n".join(lines)
