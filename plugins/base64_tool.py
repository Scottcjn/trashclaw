"""
Base64 Plugin for TrashClaw

Encode or decode text and files using Base64.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import base64 as _b64
import os

TOOL_DEF = {
    "name": "base64",
    "description": "Encode or decode text using Base64 encoding.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to encode or decode"
            },
            "action": {
                "type": "string",
                "description": "Action to perform: encode or decode (default: encode)"
            }
        },
        "required": ["text"]
    }
}


def run(text: str = "", action: str = "encode", **kwargs) -> str:
    action = action.lower().strip()

    if not text:
        return "Error: provide 'text' to encode or decode."

    if action == "encode":
        try:
            encoded = _b64.b64encode(text.encode("utf-8")).decode("utf-8")
            return f"Base64 encoded:\n{encoded}"
        except Exception as e:
            return f"Error encoding: {e}"

    elif action == "decode":
        try:
            # Add padding if needed
            padded = text + "=" * (4 - len(text) % 4) if len(text) % 4 else text
            decoded = _b64.b64decode(padded).decode("utf-8")
            return f"Base64 decoded:\n{decoded}"
        except Exception as e:
            return f"Error decoding: {e}"

    else:
        return f"Unknown action '{action}'. Use: encode, decode"
