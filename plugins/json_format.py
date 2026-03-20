"""
JSON Format Plugin for TrashClaw

Pretty-print, validate, minify, or extract keys from JSON text.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import json

TOOL_DEF = {
    "name": "json_format",
    "description": "Pretty-print, validate, minify, or extract keys from JSON text.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "JSON text to process"
            },
            "action": {
                "type": "string",
                "description": "Action: pretty (default), minify, validate, keys"
            },
            "indent": {
                "type": "integer",
                "description": "Indentation spaces for pretty mode (default: 2)"
            }
        },
        "required": ["text"]
    }
}


def run(text: str = "", action: str = "pretty", indent: int = 2, **kwargs) -> str:
    if not text:
        return "Error: provide 'text' to format."

    action = action.lower().strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    if action == "pretty":
        return json.dumps(data, indent=indent, ensure_ascii=False)

    elif action == "minify":
        return json.dumps(data, separators=(",", ":"), ensure_ascii=False)

    elif action == "validate":
        kind = type(data).__name__
        if isinstance(data, dict):
            return f"Valid JSON object with {len(data)} keys: {', '.join(list(data.keys())[:10])}"
        elif isinstance(data, list):
            return f"Valid JSON array with {len(data)} items"
        else:
            return f"Valid JSON {kind}: {data}"

    elif action == "keys":
        if not isinstance(data, dict):
            return "Error: 'keys' action requires a JSON object (dict)"
        return "\n".join(data.keys())

    else:
        return f"Unknown action '{action}'. Use: pretty, minify, validate, keys"
