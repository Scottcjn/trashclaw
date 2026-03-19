# Proposed Fix for #67

```diff
--- a/trashclaw.py
+++ b/trashclaw.py
@@ -256,6 +256,80 @@ def _load_project_instructions() -> str:
             pass
 
+    # Append extra system prompt from project config (.trashclaw.toml / .trashclaw.json)
+    if EXTRA_SYSTEM_PROMPT:
+        result += f"\n\n--- Project System Prompt ---\n{EXTRA_SYSTEM_PROMPT}"
+
     return result
 
 
+def _load_project_config() -> Dict:
+    """Load project config from .trashclaw.toml or .trashclaw.json in CWD.
+
+    Supports fields:
+      context_files = ["src/main.py", "README.md"]  — auto-loaded into conversation
+      system_prompt = "You are a Rust expert"        — appended to system prompt
+      model = "codestral"                            — override model name
+      auto_shell = true                              — skip shell approval
+
+    Uses stdlib tomllib (Python 3.11+) with JSON fallback for older Python.
+    """
+    global MODEL_NAME, APPROVE_SHELL, EXTRA_SYSTEM_PROMPT
+
+    config = {}
+
+    toml_path = os.path.join(CWD, ".trashclaw.toml")
+    json_path = os.path.join(CWD, ".trashclaw.json")
+
+    # Try TOML first
+    if os.path.exists(toml_path):
+        try:
+            import tomllib
+            with open(toml_path, "rb") as f:
+                config = tomllib.load(f)
+        except ImportError:
+            # Python < 3.11: try third-party tomli, then give up on TOML
+            try:
+                import tomli as tomllib  # type: ignore
+                with open(toml_path, "rb") as f:
+                    config = tomllib.load(f)
+            except ImportError:
+                print("  \033[33m[config]\033[0m .trashclaw.toml found but tomllib unavailable (needs Python 3.11+). Trying .trashclaw.json fallback.")
+        except Exception as e:
+            print(f"  \033[33m[config]\033[0m Error reading .trashclaw.toml: {e}")
+
+    # Fall back to JSON
+    if not config and os.path.exists(json_path):
+        try:
+            with open(json_path, "r") as f:
+                config = json.load(f)
+        except Exception as e:
+            print(f"  \033[33m[config]\033[0m Error reading .trashclaw.json: {e}")
+
+    if not config:
+        return config
+
+    # Apply model override
+    if "model" in config:
+        MODEL_NAME = str(config["model"])
+        print(f"  \033[32m[config]\033[0m Model: {MODEL_NAME}")
+
+    # Apply auto_shell
+    if "auto_shell" in config:
+        APPROVE_SHELL = not bool(config["auto_shell"])
+        if config["auto_shell"]:
+            print("  \033[32m[config]\033[0m Auto-shell: enabled")
+
+    # Apply system_prompt
+    if "system_prompt" in config:
+        EXTRA_SYSTEM_PROMPT = str(config["system_prompt"])
+        print(f"  \033[32m[config]\033[0m System prompt appended ({len(EXTRA_SYSTEM_PROMPT)} chars)")
+
+    # Auto-load context files into conversation history
+    if "context_files" in config:
+        loaded = 0
+        for fpath in config["context_files"]:
+            resolved = _resolve_path(str(fpath))
+            if os.path.exists(resolved):
+                try:
+                    with open(resolved, "r", errors="replace") as f:
+                        content = f.read(8000)
+                    HISTORY.append({
+                        "role": "user",
+                        "content": f"[Auto-loaded context from {fpath}]\n\n{content}"
+                    })
+                    HISTORY.append({
+                        "role": "assistant",
+                        "content": f"I've loaded {fpath} into context. I'll reference it as needed."
+                    })
+                    loaded += 1
+                except Exception as e:
+                    print(f"  \033[33m[config]\033[0m Failed to load {fpath}: {e}")
+            else:
+                print(f"  \033[33m[config]\033[0m Context file not found: {fpath}")
+        if loaded:
+            print(f"  \033[32m[config]\033[0m Loaded {loaded} context file{'s' if loaded != 1 else ''}")
+
+    return config
+
+
 SLASH_COMMANDS = ["/about", "/achievements", "/add", "/cd", "/clear", "/compact",
@@ -263,6 +337,10 @@ SLASH_COMMANDS = ["/about", "/achievements", "/add", "/cd", "/clear", "/compact"
                   "/config", "/diff", "/exit", "/export", "/help", "/load", "/model",
                   "/plugins", "/quit", "/remember", "/save", "/sessions", "/status", "/undo"]
 
+# ── Load project config on import (before main loop) ──
+_PROJECT_CONFIG = _load_project_config()
+
 
 def _setup_tab_completion():
     """Set up tab completion for slash commands and file paths."""
```

The key design decisions:

1. **TOML-first with JSON fallback**: Tries `tomllib` (stdlib in 3.11+), then `tomli` (third-party backport), then falls back to `.trashclaw.json` — exactly as the issue specifies.

2. **Context files as conversation pairs**: Each auto-loaded file becomes a user message + assistant acknowledgment in `HISTORY`. This ensures the LLM sees the content as pre-existing context rather than a system instruction, which gives better results for code reference.

3. **System prompt via existing path**: The `EXTRA_SYSTEM_PROMPT` global is set by the config loader, and `_load_project_instructions()` is extended to emit it. This means the extra prompt flows through the same assembly path that already handles `.trashclaw.md` — no new plumbing needed.

4. **Module-level execution**: `_load_project_config()` runs at import time (after all globals are defined), so config is applied before the main loop starts. The result is stored in `_PROJECT_CONFIG` for potential later reference.

5. **Defensive typing**: All config values are cast with `str()` / `bool()` to handle unexpected TOML/JSON types gracefully.