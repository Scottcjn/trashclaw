"""
JSON Diff Plugin for TrashClaw

Diff two JSON files or strings showing added, removed, and changed keys.
Handles nested structures with dot-path notation.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import json
import os

TOOL_DEF = {
    "name": "json_diff",
    "description": "Diff two JSON files or strings. Shows added, removed, and changed keys with dot-path notation for nested structures.",
    "parameters": {
        "type": "object",
        "properties": {
            "file_a": {
                "type": "string",
                "description": "Path to first JSON file (or use json_a for inline JSON)"
            },
            "file_b": {
                "type": "string",
                "description": "Path to second JSON file (or use json_b for inline JSON)"
            },
            "json_a": {
                "type": "string",
                "description": "First JSON string (alternative to file_a)"
            },
            "json_b": {
                "type": "string",
                "description": "Second JSON string (alternative to file_b)"
            }
        },
        "required": []
    }
}


def _flatten(obj, prefix=""):
    """Flatten a nested dict/list into dot-path keys."""
    items = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)):
                items.update(_flatten(v, new_key))
            else:
                items[new_key] = v
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{prefix}[{i}]"
            if isinstance(v, (dict, list)):
                items.update(_flatten(v, new_key))
            else:
                items[new_key] = v
    else:
        items[prefix] = obj
    return items


def _load_json(file_path: str = "", json_str: str = "", label: str = "input"):
    """Load JSON from file or string. Returns (data, error_msg)."""
    if file_path:
        if not os.path.exists(file_path):
            return None, f"Error: file not found: {file_path}"
        try:
            with open(file_path, "r") as f:
                return json.load(f), None
        except json.JSONDecodeError as e:
            return None, f"Error: invalid JSON in {file_path}: {e}"
        except Exception as e:
            return None, f"Error reading {file_path}: {e}"
    elif json_str:
        try:
            return json.loads(json_str), None
        except json.JSONDecodeError as e:
            return None, f"Error: invalid JSON in {label}: {e}"
    return None, f"Error: no {label} provided (use file or inline JSON)."


def _format_value(v):
    """Format a value for display, truncating long strings."""
    s = json.dumps(v)
    if len(s) > 80:
        s = s[:77] + "..."
    return s


def run(file_a: str = "", file_b: str = "", json_a: str = "", json_b: str = "", **kwargs) -> str:
    data_a, err = _load_json(file_a, json_a, "A")
    if err:
        return err
    data_b, err = _load_json(file_b, json_b, "B")
    if err:
        return err

    flat_a = _flatten(data_a)
    flat_b = _flatten(data_b)

    keys_a = set(flat_a.keys())
    keys_b = set(flat_b.keys())

    added = sorted(keys_b - keys_a)
    removed = sorted(keys_a - keys_b)
    common = sorted(keys_a & keys_b)

    changed = []
    for k in common:
        if flat_a[k] != flat_b[k]:
            changed.append(k)

    if not added and not removed and not changed:
        return "No differences found. The JSON structures are identical."

    lines = ["JSON Diff Results", "=" * 40]

    label_a = file_a or "(inline A)"
    label_b = file_b or "(inline B)"
    lines.append(f"A: {label_a}")
    lines.append(f"B: {label_b}")
    lines.append("")

    if added:
        lines.append(f"ADDED ({len(added)} keys, only in B):")
        for k in added:
            lines.append(f"  + {k}: {_format_value(flat_b[k])}")
        lines.append("")

    if removed:
        lines.append(f"REMOVED ({len(removed)} keys, only in A):")
        for k in removed:
            lines.append(f"  - {k}: {_format_value(flat_a[k])}")
        lines.append("")

    if changed:
        lines.append(f"CHANGED ({len(changed)} keys):")
        for k in changed:
            lines.append(f"  ~ {k}:")
            lines.append(f"      A: {_format_value(flat_a[k])}")
            lines.append(f"      B: {_format_value(flat_b[k])}")
        lines.append("")

    summary = f"Summary: +{len(added)} added, -{len(removed)} removed, ~{len(changed)} changed"
    lines.append(summary)

    return "\n".join(lines)
