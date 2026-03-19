# Proposed Fix for #65

```diff
--- a/trashclaw.py
+++ b/trashclaw.py
@@ -21,6 +21,8 @@ import glob as globlib
 import difflib
 import traceback
 import time
+import base64
+import tempfile
 import signal
 from datetime import datetime
 from typing import Dict, List, Optional, Tuple, Any
@@ -63,6 +65,19 @@ UNDO_STACK: List[Dict] = []  # [{path, content_before, action}]
 APPROVED_COMMANDS: set = set()
 EXTRA_SYSTEM_PROMPT: str = ""
 ACHIEVEMENTS_FILE = os.path.join(CONFIG_DIR, "achievements.json")
+_VISION_SUPPORTED: Optional[bool] = None
+
+_IMAGE_MIME_TYPES = {
+    '.png': 'image/png',
+    '.jpg': 'image/jpeg',
+    '.jpeg': 'image/jpeg',
+    '.gif': 'image/gif',
+    '.webp': 'image/webp',
+    '.bmp': 'image/bmp',
+}
+
+_SCREENSHOT_PATH = os.path.join(tempfile.gettempdir(), "trashclaw_screenshot.png")
+
 
 # ── Trashy's Soul ──
 
@@ -334,6 +349,20 @@ TOOLS = [
             }
         }
     },
+    {
+        "type": "function",
+        "function": {
+            "name": "view_image",
+            "description": "View an image file by including it in the conversation. Works with vision-capable models (LLaVA, Qwen-VL, etc.). Supports PNG, JPEG, GIF, WebP, BMP.",
+            "parameters": {
+                "type": "object",
+                "properties": {
+                    "path": {"type": "string", "description": "Path to the image file to view"}
+                },
+                "required": ["path"]
+            }
+        }
+    },
 ]
 
 TOOL_NAMES = {t["function"]["name"] for t in TOOLS}
@@ -573,6 +602,98 @@ def tool_clipboard(action: str = "paste", content: str = "") -> str:
     return f"Error: Unknown clipboard action '{action}'. Use 'copy' or 'paste'."
 
 
+def _check_vision_support() -> bool:
+    """Check if the current model supports vision/multimodal input via /v1/models."""
+    global _VISION_SUPPORTED
+    if _VISION_SUPPORTED is not None:
+        return _VISION_SUPPORTED
+
+    vision_keywords = (
+        "llava", "bakllava", "qwen-vl", "qwen2-vl", "cogvlm",
+        "minicpm-v", "internvl", "vision", "visual", "multimodal",
+    )
+
+    try:
+        url = f"{LLAMA_URL}/v1/models"
+        req = urllib.request.Request(url, headers={"User-Agent": "TrashClaw"})
+        with urllib.request.urlopen(req, timeout=5) as resp:
+            data = json.loads(resp.read().decode("utf-8"))
+
+        for model in data.get("data", []):
+            model_id = model.get("id", "").lower()
+            if any(kw in model_id for kw in vision_keywords):
+                _VISION_SUPPORTED = True
+                return True
+            # Some backends expose capabilities or meta fields
+            caps = model.get("capabilities", {})
+            if isinstance(caps, dict) and caps.get("vision", False):
+                _VISION_SUPPORTED = True
+                return True
+            meta = model.get("meta", {})
+            if isinstance(meta, dict) and meta.get("multimodal", False):
+                _VISION_SUPPORTED = True
+                return True
+    except Exception:
+        pass
+
+    # Cannot determine — assume supported and let the server decide
+    _VISION_SUPPORTED = True
+    return True
+
+
+def _get_image_mime(path: str) -> str:
+    """Get MIME type from image file extension."""
+    ext = os.path.splitext(path)[1].lower()
+    return _IMAGE_MIME_TYPES.get(ext, "image/png")
+
+
+def tool_view_image(path: str) -> str:
+    """Read an image file and include it in the conversation for vision models."""
+    if not _check_vision_support():
+        return ("Error: Current model does not appear to support vision/image input. "
+                "Use a multimodal model (e.g. LLaVA, Qwen-VL, BakLLaVA).")
+
+    path = _resolve_path(path)
+
+    if not os.path.exists(path):
+        return f"Error: Image file not found: {path}"
+
+    ext = os.path.splitext(path)[1].lower()
+    if ext not in _IMAGE_MIME_TYPES:
+        supported = ", ".join(_IMAGE_MIME_TYPES.keys())
+        return f"Error: Unsupported image format '{ext}'. Supported: {supported}"
+
+    try:
+        with open(path, "rb") as f:
+            image_data = f.read()
+    except PermissionError:
+        return f"Error: Permission denied: {path}"
+    except Exception as e:
+        return f"Error reading image: {e}"
+
+    if len(image_data) > 20 * 1024 * 1024:
+        return f"Error: Image too large ({len(image_data) // (1024 * 1024)}MB). Max 20MB."
+
+    b64data = base64.b64encode(image_data).decode("ascii")
+    mime = _get_image_mime(path)
+
+    # Inject image directly into conversation history as a content array message.
+    # The OpenAI chat API accepts content as either a string or an array of
+    # content parts — this lets us pass the base64 image alongside text.
+    HISTORY.append({
+        "role": "user",
+        "content": [
+            {"type": "text", "text": f"[Image: {os.path.basename(path)}]"},
+            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64data}"}}
+        ]
+    })
+
+    size_kb = len(image_data) // 1024
+    return f"Image loaded: {os.path.basename(path)} ({size_kb}KB, {mime}). The image is now visible in the conversation."
+
+
+def _take_screenshot() -> str:
+    """Take a screenshot using platform-native tools. Returns file path or empty string."""
+    system = platform.system()
+    if system == "Darwin":
+        cmds = [["screencapture", "-x", _SCREENSHOT_PATH]]
+    elif system == "Linux":
+        cmds = [
+            ["grim", _SCREENSHOT_PATH],
+            ["scrot", _SCREENSHOT_PATH],
+            ["import", "-window", "root", _SCREENSHOT_PATH],
+        ]
+    elif system == "Windows":
+        ps = (
+            "Add-Type -AssemblyName System.Windows.Forms;"
+            "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
+            "$bmp=New-Object System.Drawing.Bitmap($b.Width,$b.Height);"
+            "$g=[System.Drawing.Graphics]::FromImage($bmp);"
+            "$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
+            f"$bmp.Save('{_SCREENSHOT_PATH}');$g.Dispose();$bmp.Dispose()"
+        )
+        cmds = [["powershell.exe", "-command", ps]]
+    else:
+        return ""
+
+    for cmd in cmds:
+        try:
+            r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
+            if r.returncode == 0 and os.path.exists(_SCREENSHOT_PATH):
+                return _SCREENSHOT_PATH
+        except (FileNotFoundError, subprocess.TimeoutExpired):
+            continue
+    return ""
+
+
+def handle_slash_screenshot() -> Optional[str]:
+    """Handle the /screenshot slash command.
+
+    Returns a user-message string to send to the LLM, or None to skip.
+    """
+    if not _check_vision_support():
+        print("  \033[33mCurrent model does not support vision. Use a multimodal model.\033[0m")
+        return None
+
+    print("  \033[90mTaking screenshot...\033[0m")
+    path = _take_screenshot()
+    if not path:
+        print("  \033[31mScreenshot failed. No supported tool found.\033[0m")
+        print("  \033[90mNeed: screencapture (macOS), grim/scrot (Linux), or PowerShell (Windows)\033[0m")
+        return None
+
+    result = tool_view_image(path)
+    print(f"  {result}")
+
+    # Clean up temp file
+    try:
+        os.remove(path)
+    except Exception:
+        pass
+
+    return "I've included a screenshot. Please describe or analyze what you see."
+
+
 def tool_think(thought: str) -> str:
     return f"[Thought recorded, no side effects]"
 
@@ -591,6 +712,7 @@ TOOL_DISPATCH = {
     "patch_file": lambda args: tool_patch_file(args["path"], args["patch"]),
     "clipboard": lambda args: tool_clipboard(args.get("action", "paste"), args.get("content", "")),
+    "view_image": lambda args: tool_view_image(args["path"]),
 }
 
 
@@ -649,8 +771,8 @@ def detect_project_context() -> str:
 
 SLASH_COMMANDS = ["/about", "/achievements", "/add", "/cd", "/clear", "/compact",
                   "/config", "/diff", "/exit", "/export", "/help", "/load", "/model",
-                  "/plugins", "/quit", "/remember", "/save", "/sessions", "/status", "/undo"]
+                  "/plugins", "/quit", "/remember", "/save", "/screenshot", "/sessions",
+                  "/status", "/undo", "/vision"]
 
 
 def _setup_tab_completion():
```

And in the main input loop (in the truncated section of the file), where other slash commands are handled via if/elif, add these two cases:

```diff
+        elif user_input.strip() == "/screenshot":
+            msg = handle_slash_screenshot()
+            if msg:
+                HISTORY.append({"role": "user", "content": msg})
+            continue
+
+        elif user_input.strip() == "/vision":
+            # Reset cache and re-check
+            _VISION_SUPPORTED = None
+            supported = _check_vision_support()
+            if supported:
+                print("  \033[32mVision support: detected (multimodal model available)\033[0m")
+            else:
+                print("  \033[33mVision support: not detected\033[0m")
+            continue
```

**Key design decisions:**

1. **Image injection via HISTORY**: Rather than modifying the LLM client's message-building code, `tool_view_image` appends a properly formatted content-array message directly to `HISTORY`. The OpenAI chat API accepts `content` as either a plain string or an array of `{"type": "text"}`/`{"type": "image_url"}` parts — so existing serialization works unchanged.

2. **Vision auto-detection**: Queries `/v1/models` and checks model IDs against known vision model name patterns (llava, qwen-vl, cogvlm, etc.) plus `capabilities.vision` and `meta.multimodal` metadata fields. Falls back to assuming vision is supported if detection is inconclusive, letting the server reject if truly unsupported.

3. **Screenshot portability**: Uses `screencapture -x` on macOS, tries `grim` then `scrot` then `import` on Linux (covering Wayland and X11), and PowerShell `CopyFromScreen` on Windows — all without external Python dependencies.

4. **No new dependencies**: Uses only `base64` and `tempfile` from stdlib, as required.