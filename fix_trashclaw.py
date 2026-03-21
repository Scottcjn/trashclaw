import re

with open("trashclaw.py", "r") as f:
    code = f.read()

# Fix 1: tool_timestamp timezone bug
old_ts = """            return str(int(dt.replace(tzinfo=timezone.utc).timestamp()))"""
new_ts = """            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return str(int(dt.timestamp()))"""
code = code.replace(old_ts, new_ts)

# Fix 2: System prompt TOOLS list
old_tools = """- clipboard: Read/write system clipboard
- think: Reason step by step before acting"""
new_tools = """- clipboard: Read/write system clipboard
- think: Reason step by step before acting
- word_count: Count words, lines, and characters in text or files
- json_format: Pretty-print or normalize JSON
- timestamp: Get the current timestamp in various formats"""
code = code.replace(old_tools, new_tools)

# Fix 3: /plugins count
old_plugins = """            builtin_count = 14  # built-in tools
            plugin_count = len(TOOLS) - builtin_count
            if not plugins:
                print(f"  Plugin directory exists but no plugins found.")
            else:
                print(f"  \\033[1mPlugins\\033[0m ({PLUGINS_DIR})")
                for p in sorted(plugins):
                    loaded = any(t["function"]["name"] == p[:-3] for t in TOOLS)
                    status = "\\033[32mloaded\\033[0m" if loaded else "\\033[31mfailed\\033[0m"
                    print(f"    {p} [{status}]")"""

new_plugins = """            plugin_count = 0
            if not plugins:
                print(f"  Plugin directory exists but no plugins found.")
            else:
                print(f"  \\033[1mPlugins\\033[0m ({PLUGINS_DIR})")
                for p in sorted(plugins):
                    loaded = any(t["function"]["name"] == p[:-3] for t in TOOLS)
                    if loaded:
                        plugin_count += 1
                    status = "\\033[32mloaded\\033[0m" if loaded else "\\033[31mfailed\\033[0m"
                    print(f"    {p} [{status}]")
            builtin_count = len(TOOLS) - plugin_count"""
code = code.replace(old_plugins.replace("\\\\", "\\"), new_plugins.replace("\\\\", "\\"))

with open("trashclaw.py", "w") as f:
    f.write(code)

