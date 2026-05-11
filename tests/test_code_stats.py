"""Tests for the code_stats plugin."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugins"))
from code_stats import _is_binary, run


def test_is_binary_detects_text_binary_and_missing_files(tmp_path):
    text_file = tmp_path / "plain.py"
    text_file.write_text("print('hello')\n")

    binary_file = tmp_path / "compiled.py"
    binary_file.write_bytes(b"print\x00hidden")

    assert _is_binary(str(text_file)) is False
    assert _is_binary(str(binary_file)) is True
    assert _is_binary(str(tmp_path / "missing.py")) is True


def test_run_counts_languages_markers_and_skips_ignored_paths(tmp_path):
    (tmp_path / "app.py").write_text(
        "print('hello')\n"
        "# TODO: test marker\n"
        "# FIXME: fix marker\n"
        "# HACK: hack marker\n"
    )
    (tmp_path / "web.js").write_text("console.log('hi')\n")
    (tmp_path / "README.md").write_text("# Project\n")
    (tmp_path / "bundle.min.js").write_text("minified should be skipped\n")
    (tmp_path / "binary.py").write_bytes(b"ignored\x00binary\n")

    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "secret.py").write_text("print('skip hidden')\n")

    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "vendored.py").write_text("print('skip vendor')\n")

    result = run(path=str(tmp_path), top_n=5)

    assert "Total: 3 files, 6 lines" in result
    assert "Python" in result
    assert "JavaScript" in result
    assert "Markdown" in result
    assert "TODO:  1" in result
    assert "FIXME: 1" in result
    assert "HACK:  1" in result
    assert "app.py" in result
    assert "web.js" in result
    assert "README.md" in result
    assert "bundle.min.js" not in result
    assert "binary.py" not in result
    assert "secret.py" not in result
    assert "vendored.py" not in result


def test_run_reports_missing_directory_and_empty_source_tree(tmp_path):
    missing = tmp_path / "missing"
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "notes.txt").write_text("not a recognized source extension\n")

    assert "Error: Not a directory" in run(path=str(missing))
    assert "No recognized source files found" in run(path=str(empty))
