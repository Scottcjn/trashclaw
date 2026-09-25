# SPDX-License-Identifier: MIT
"""Regression tests: backend auto-detection must not produce /v1/v1/... URLs.

A stdlib http.server runs in a thread and records the request paths it sees.
"""

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trashclaw


def _make_server(backend):
    """Start a fake LM Studio ("lmstudio") or Ollama ("ollama") server."""
    paths = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            paths.append(("GET", self.path))
            if backend == "lmstudio" and self.path == "/v1/models":
                self._send(200, json.dumps({"data": [{"id": "test-model"}]}))
            elif backend == "ollama" and self.path == "/api/tags":
                self._send(200, json.dumps({"models": []}))
            else:
                self._send(404, "{}")

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            self.rfile.read(length)
            paths.append(("POST", self.path))
            if self.path != "/v1/chat/completions":
                self._send(404, "{}")
                return
            chunk = {"choices": [{"delta": {"content": "hi"}, "finish_reason": "stop"}]}
            self._send(200, "data: " + json.dumps(chunk) + "\n\ndata: [DONE]\n\n",
                       "text/event-stream")

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, paths


@pytest.fixture(autouse=True)
def _reset_stats(monkeypatch):
    monkeypatch.setattr(trashclaw, "LAST_GENERATION_STATS", {})
    monkeypatch.setattr(trashclaw, "SESSION_STATS",
                        {"total_tokens": 0, "total_seconds": 0.0, "turns": 0})


@pytest.mark.parametrize("backend,name", [("lmstudio", "LM Studio"), ("ollama", "Ollama")])
@pytest.mark.parametrize("suffix", ["", "/", "/v1", "/v1/"])
def test_detection_then_chat_posts_to_single_v1(monkeypatch, backend, name, suffix):
    server, paths = _make_server(backend)
    try:
        base = "http://127.0.0.1:%d" % server.server_address[1]
        monkeypatch.setattr(trashclaw, "LLAMA_URL", base + suffix)
        assert trashclaw._detect_backend() == name
        assert trashclaw.LLAMA_URL == base

        result = trashclaw.llm_request([{"role": "user", "content": "hello"}])
        assert "error" not in result, result
        assert result["choices"][0]["message"]["content"] == "hi"
        assert ("POST", "/v1/chat/completions") in paths
        assert not any("/v1/v1" in p for _, p in paths)
    finally:
        server.shutdown()
        server.server_close()


def test_api_url_builders(monkeypatch):
    for url in ("http://h:1", "http://h:1/", "http://h:1/v1", "http://h:1/v1/"):
        monkeypatch.setattr(trashclaw, "LLAMA_URL", url)
        assert trashclaw._server_base_url() == "http://h:1"
        assert trashclaw._api_url("/chat/completions") == "http://h:1/v1/chat/completions"
        assert trashclaw._api_url("/models") == "http://h:1/v1/models"
