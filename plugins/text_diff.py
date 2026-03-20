"""
TrashClaw Plugin — Text Diff

Compare two strings or file contents and show differences.
Useful for reviewing changes before committing.
"""

import difflib

TOOL_DEF = {
    "name": "text_diff",
    "description": "Compare two text blocks and show a unified diff of differences. Useful for comparing before/after changes.",
    "parameters": {
        "type": "object",
        "properties": {
            "text_a": {
                "type": "string",
                "description": "Original text (before changes)"
            },
            "text_b": {
                "type": "string",
                "description": "Modified text (after changes)"
            },
            "context_lines": {
                "type": "integer",
                "description": "Number of context lines around changes (default: 3)"
            }
        },
        "required": ["text_a", "text_b"]
    }
}


def run(text_a: str = "", text_b: str = "", context_lines: int = 3, **kwargs) -> str:
    """Generate a unified diff between two text blocks."""
    try:
        lines_a = text_a.splitlines(keepends=True)
        lines_b = text_b.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            lines_a, lines_b,
            fromfile="original",
            tofile="modified",
            n=context_lines
        ))

        if not diff:
            return "No differences found — texts are identical."

        return "".join(diff)
    except Exception as e:
        return f"Diff failed: {e}"
