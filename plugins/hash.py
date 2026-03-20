"""
Hash Plugin for TrashClaw

Compute cryptographic hashes (MD5, SHA-1, SHA-256, SHA-512) of text or files.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import hashlib
import os

TOOL_DEF = {
    "name": "hash",
    "description": "Compute cryptographic hash (MD5, SHA-1, SHA-256, SHA-512) of text or a file.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "Text to hash"
            },
            "file": {
                "type": "string",
                "description": "Path to file to hash (optional)"
            },
            "algorithm": {
                "type": "string",
                "description": "Hash algorithm: md5, sha1, sha256, sha512 (default: sha256)"
            }
        },
        "required": []
    }
}


def _hash_text(text: str, algorithm: str) -> str:
    try:
        h = hashlib.new(algorithm)
        h.update(text.encode("utf-8"))
        return h.hexdigest()
    except ValueError:
        return f"Error: unsupported algorithm '{algorithm}'"


def _hash_file(path: str, algorithm: str) -> str:
    if not os.path.exists(path):
        return f"Error: file not found: {path}"
    try:
        h = hashlib.new(algorithm)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except ValueError:
        return f"Error: unsupported algorithm '{algorithm}'"
    except Exception as e:
        return f"Error: {e}"


def run(text: str = "", file: str = "", algorithm: str = "sha256", **kwargs) -> str:
    algorithm = algorithm.lower().replace("-", "")
    supported = ["md5", "sha1", "sha256", "sha512"]

    if algorithm not in supported:
        return f"Unsupported algorithm '{algorithm}'. Use: {', '.join(supported)}"

    results = []

    if file:
        digest = _hash_file(file, algorithm)
        results.append(f"{algorithm.upper()}({file}):\n{digest}")

    if text:
        digest = _hash_text(text, algorithm)
        results.append(f"{algorithm.upper()}(text):\n{digest}")

    if not text and not file:
        return "Error: provide 'text' or 'file' to hash."

    return "\n\n".join(results)
