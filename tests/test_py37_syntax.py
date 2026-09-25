# SPDX-License-Identifier: MIT
"""TrashClaw runs on old machines: the main file and plugins must parse
with Python 3.7 grammar (no walrus, positional-only params, match, etc.)."""

import ast
import glob
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = [os.path.join(ROOT, "trashclaw.py")] + sorted(
    glob.glob(os.path.join(ROOT, "plugins", "*.py")))


@pytest.mark.skipif(sys.version_info < (3, 8), reason="feature_version needs Python 3.8+")
@pytest.mark.parametrize("path", FILES, ids=lambda p: os.path.relpath(p, ROOT))
def test_parses_as_python37(path):
    with open(path, encoding="utf-8") as f:
        source = f.read()
    ast.parse(source, filename=path, feature_version=(3, 7))
