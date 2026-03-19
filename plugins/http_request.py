"""
HTTP Request Plugin for TrashClaw

Make HTTP requests with custom headers, methods, and body.
Supports GET, POST, PUT, DELETE, PATCH methods.
Returns response status, headers, and body.

Plugin contract:
  TOOL_DEF = dict with name, description, parameters (OpenAI function schema)
  run(**kwargs) -> str  (called with the parsed arguments)
"""

import urllib.request
import urllib.error
import json
from typing import Optional, Dict, Any

TOOL_DEF = {
    "name": "http_request",
    "description": "Make HTTP requests with custom headers, methods, and body. Returns response status, headers, and body (JSON parsed if applicable).",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to request (e.g., 'https://api.example.com/data')"
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "description": "HTTP method (default: GET)"
            },
            "headers": {
                "type": "object",
                "description": "Custom headers as key-value pairs (e.g., {'Authorization': 'Bearer token'})",
                "additionalProperties": {"type": "string"}
            },
            "body": {
                "type": "string",
                "description": "Request body (will be sent as JSON if Content-Type is application/json)"
            },
            "timeout": {
                "type": "integer",
                "description": "Request timeout in seconds (default: 30)"
            }
        },
        "required": ["url"]
    }
}


def run(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None, timeout: int = 30, **kwargs) -> str:
    """
    Make an HTTP request and return formatted response.

    Args:
        url: The URL to request
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        headers: Custom headers dict
        body: Request body string
        timeout: Request timeout in seconds

    Returns:
        Formatted response string with status, headers, and body
    """
    # Prepare headers
    req_headers = {"User-Agent": "TrashClaw-HTTP/1.0"}
    if headers:
        req_headers.update(headers)

    # Prepare body
    data = None
    if body:
        data = body.encode("utf-8")
        if "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"

    # Create request
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            resp_headers = dict(resp.headers)
            raw_body = resp.read().decode("utf-8", errors="replace")

            # Try to parse JSON
            try:
                parsed_body = json.loads(raw_body)
                body_str = json.dumps(parsed_body, indent=2, ensure_ascii=False)
            except (json.JSONDecodeError, ValueError):
                body_str = raw_body[:2000]  # Limit response size
                if len(raw_body) > 2000:
                    body_str += f"\n... (truncated, {len(raw_body)} total chars)"

            # Format output
            result = f"HTTP {method.upper()} {url}\n"
            result += f"Status: {status}\n"
            result += f"Headers:\n"
            for k, v in list(resp_headers.items())[:10]:  # Limit headers shown
                result += f"  {k}: {v}\n"
            result += f"\nBody:\n{body_str}"

            return result

    except urllib.error.HTTPError as e:
        return f"HTTP Error {e.code}: {e.reason}\nURL: {url}"
    except urllib.error.URLError as e:
        return f"URL Error: {e.reason}\nURL: {url}"
    except Exception as e:
        return f"Request failed: {type(e).__name__}: {e}"


# path/to/config_loader.py
import os
import tomllib
import json
from typing import List, Dict, Union

class TrashClawConfig:
    def __init__(self, context_files: List[str], system_prompt: str, model: str, auto_shell: bool):
        self.context_files = context_files
        self.system_prompt = system_prompt
        self.model = model
        self.auto_shell = auto_shell

    @classmethod
    def from_file(cls, file_path: str) -> 'TrashClawConfig':
        """Load configuration from the specified TOML or JSON file."""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Configuration file '{file_path}' does not exist.")

        ext = os.path.splitext(file_path)[1]
        
        if ext == ".toml":
            with open(file_path, 'rb') as f:
                config_data = tomllib.load(f)
        elif ext == ".json":
            with open(file_path, 'r') as f:
                config_data = json.load(f)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        return cls(
            context_files=config_data.get('context_files', []),
            system_prompt=config_data.get('system_prompt', ''),
            model=config_data.get('model', 'default_model'),
            auto_shell=config_data.get('auto_shell', False)
        )

def load_config() -> TrashClawConfig:
    """Attempts to load configuration from the .trashclaw.toml or .trashclaw.json in the current working directory."""
    for config_file in ['.trashclaw.toml', '.trashclaw.json']:
        try:
            return TrashClawConfig.from_file(os.path.join(os.getcwd(), config_file))
        except (FileNotFoundError, ValueError):
            continue
    raise FileNotFoundError("No valid TrashClaw configuration file found.")
