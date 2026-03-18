#!/usr/bin/env python3
"""
TrashClaw v0.3 — Local Tool-Use Agent
========================================
A general-purpose agent powered by a local LLM. Reads files, writes files,
runs commands, searches codebases, manages git — whatever you need.
OpenClaw-style tool-use loop with zero external dependencies.

Pure Python stdlib. Python 3.7+. Works with llama.cpp, Ollama, LM Studio,
or any OpenAI-compatible server.
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
import re
import glob as globlib
import difflib
import traceback
import time
import signal
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Windows compatibility: use pyreadline3 or skip readline
if sys.platform == "win32":
    try:
        import pyreadline3 as readline
    except ImportError:
        # readline not available on Windows without pyreadline3
        # Create a minimal stub to avoid errors
        class _StubReadline:
            def parse_and_bind(self, *args): pass
        readline = _StubReadline()
else:
    import readline

# ── Config ──
VERSION = "0.7.0"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".trashclaw")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history")

# ── Backend Detection ──
BACKEND_TYPE = None  # Will be set to: llama-server, ollama, lmstudio, or openai

def detect_backend() -> str:
    """Detect the type of LLM server running at LLAMA_URL."""
    global BACKEND_TYPE
    if BACKEND_TYPE is not None:
        return BACKEND_TYPE
    
    try:
        # Try a simple request to the base URL
        req = urllib.request.Request(LLAMA_URL)
        with urllib.request.urlopen(req, timeout=2) as resp:
            # Check for server-specific headers or responses
            if "ollama" in resp.headers.get("server", "").lower():
                BACKEND_TYPE = "ollama"
            elif "lmstudio" in resp.headers.get("server", "").lower():
                BACKEND_TYPE = "lmstudio"
            else:
                # Default to openai-compatible if no specific server detected
                BACKEND_TYPE = "openai"
    except Exception:
        # If we can't connect, default to openai-compatible
        BACKEND_TYPE = "openai"
    
    return BACKEND_TYPE

# ── Tool Definitions ──
# Tool definitions remain the same

# ── Main Request Function ──

def llm_request(messages: List[Dict], tools: List[Dict] = None) -> Dict:
    """Send request to the appropriate endpoint based on detected backend."""
    detect_backend()  # Ensure backend is detected
    
    endpoint = "/v1/chat/completions"
    if BACKEND_TYPE == "ollama":
        endpoint = "/api/chat"
    elif BACKEND_TYPE == "lmstudio":
        endpoint = "/v1/chat/completions"
    elif BACKEND_TYPE == "openai":
        endpoint = "/v1/chat/completions"
    
    url = LLAMA_URL + endpoint
    payload = {
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1024,
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404 and BACKEND_TYPE == "ollama":
            # Fallback to openai-compatible endpoint for ollama
            endpoint = "/v1/chat/completions"
            url = LLAMA_URL + endpoint
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        else:
            raise