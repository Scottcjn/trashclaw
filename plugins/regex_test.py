"""
Regex Test Plugin for TrashClaw

Test regular expressions against input text. Shows matches, groups, and positions.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str
"""

import re

TOOL_DEF = {
    "name": "regex_test",
    "description": "Test a regular expression pattern against input text. Shows all matches with positions and groups.",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regular expression pattern to test"
            },
            "text": {
                "type": "string",
                "description": "Text to match against"
            },
            "flags": {
                "type": "string",
                "description": "Regex flags: i (ignore case), m (multiline), s (dotall), x (verbose). Combine: 'im'"
            }
        },
        "required": ["pattern", "text"]
    }
}


def _parse_flags(flags_str: str) -> int:
    flag_map = {
        "i": re.IGNORECASE,
        "m": re.MULTILINE,
        "s": re.DOTALL,
        "x": re.VERBOSE,
    }
    result = 0
    for ch in flags_str.lower():
        if ch in flag_map:
            result |= flag_map[ch]
    return result


def run(pattern: str = "", text: str = "", flags: str = "", **kwargs) -> str:
    if not pattern:
        return "Error: 'pattern' is required."
    if not text:
        return "Error: 'text' is required."

    try:
        compiled = re.compile(pattern, _parse_flags(flags))
    except re.error as e:
        return f"Regex compile error: {e}"

    matches = list(compiled.finditer(text))

    if not matches:
        return f"Pattern: /{pattern}/{''.join(sorted(flags.lower()))}\nNo matches found."

    lines = [
        f"Pattern: /{pattern}/{''.join(sorted(flags.lower()))}",
        f"Matches: {len(matches)}",
        "",
    ]

    for i, m in enumerate(matches[:50]):  # cap at 50 matches
        line = f"  [{i}] \"{m.group()}\" at {m.start()}-{m.end()}"
        if m.groups():
            groups = ", ".join(
                f"${j+1}=\"{g}\"" for j, g in enumerate(m.groups()) if g is not None
            )
            line += f"  groups: {groups}"
        if m.groupdict():
            named = ", ".join(
                f"{k}=\"{v}\"" for k, v in m.groupdict().items() if v is not None
            )
            if named:
                line += f"  named: {named}"
        lines.append(line)

    if len(matches) > 50:
        lines.append(f"  ... and {len(matches) - 50} more matches")

    return "\n".join(lines)
