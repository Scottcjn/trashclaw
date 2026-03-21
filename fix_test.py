with open("tests/test_extra_tools.py", "r") as f:
    text = f.read()

new_header = """import sys
from pathlib import Path
import json

# Ensure the repository root is on sys.path so trashclaw can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trashclaw import tool_word_count, tool_json_format, tool_timestamp
"""

text = text.replace("import pytest\nimport json\nfrom trashclaw import tool_word_count, tool_json_format, tool_timestamp\n", new_header)

with open("tests/test_extra_tools.py", "w") as f:
    f.write(text)
