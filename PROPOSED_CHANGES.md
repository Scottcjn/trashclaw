# Proposed Fix for #66

```diff
--- a/trashclaw.py
+++ b/trashclaw.py
@@ -223,8 +223,8 @@
 
 
 SLASH_COMMANDS = ["/about", "/achievements", "/add", "/cd", "/clear", "/compact",
-                  "/config", "/diff", "/exit", "/export", "/help", "/load", "/model",
-                  "/plugins", "/quit", "/remember", "/save", "/sessions", "/status", "/undo"]
+                  "/config", "/diff", "/exit", "/export", "/help", "/load", "/model", "/pipe",
+                  "/plugins", "/quit", "/remember", "/save", "/sessions", "/status", "/undo"]
 
 
 def _setup_tab_completion():
@@ -620,6 +620,43 @@
     return f"[Thought recorded, no side effects]"
 
 
+def _handle_pipe(args: str) -> None:
+    """Save the last assistant response to a file."""
+    # Find the last assistant message in HISTORY
+    last_response = None
+    for msg in reversed(HISTORY):
+        if msg.get("role") == "assistant" and msg.get("content"):
+            last_response = msg["content"]
+            break
+
+    if not last_response:
+        print("  \033[33mNo assistant response to save.\033[0m")
+        return
+
+    # Determine filename: use argument or generate timestamp-based name
+    filename = args.strip() if args.strip() else f"trashclaw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
+
+    # Resolve path relative to CWD
+    filepath = _resolve_path(filename)
+
+    try:
+        os.makedirs(os.path.dirname(filepath), exist_ok=True)
+        with open(filepath, "w") as f:
+            f.write(last_response)
+        size = os.path.getsize(filepath)
+        if size < 1024:
+            size_str = f"{size}B"
+        elif size < 1024 * 1024:
+            size_str = f"{size / 1024:.1f}KB"
+        else:
+            size_str = f"{size / (1024 * 1024):.1f}MB"
+        print(f"  \033[32mSaved to {filepath} ({size_str})\033[0m")
+    except Exception as e:
+        print(f"  \033[31mError saving: {e}\033[0m")
+
+
 # Tool dispatch
 TOOL_DISPATCH = {
     "read_file": lambda args: tool_read_file(args["path"], args.get("offset"), args.get("limit")),
```

Then, in the main input loop where other slash commands are dispatched (the section after the truncated SYSTEM_PROMPT, inside the `main()` function's input-processing `if/elif` chain):

```diff
+        elif user_input == "/pipe" or user_input.startswith("/pipe "):
+            pipe_args = user_input[5:].strip() if user_input.startswith("/pipe ") else ""
+            _handle_pipe(pipe_args)
+            continue
```

And in the `/help` text output section, add the `/pipe` description:

```diff
+            "  /pipe [file]     Save last response to file (default: timestamped name)\n"
```

**What changed and why:**

1. **`SLASH_COMMANDS` list** — Added `"/pipe"` in alphabetical order so tab-completion picks it up immediately with no extra wiring.

2. **`_handle_pipe(args)` function** — The core implementation:
   - Walks `HISTORY` in reverse to find the most recent message with `role == "assistant"` and non-empty `content`, which is exactly how the existing codebase stores LLM replies.
   - If no filename argument is given, generates `trashclaw_YYYYMMDD_HHMMSS.md` using the already-imported `datetime`.
   - Uses the existing `_resolve_path()` helper to resolve relative paths against `CWD`, consistent with all other file operations in the codebase.
   - Creates parent directories with `os.makedirs(..., exist_ok=True)` so paths like `output/script.py` work without manual `mkdir`.
   - Prints the absolute path and human-readable size (B/KB/MB) in green on success, yellow for "no response", red on error — matching the terminal color conventions used throughout the codebase.

3. **Main loop dispatch** — A simple `elif` branch that extracts the argument after `/pipe `, passes it to `_handle_pipe`, and `continue`s to skip sending the slash command to the LLM. This matches the exact pattern used by `/save`, `/export`, `/cd`, and every other slash command in the codebase.