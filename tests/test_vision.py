# SPDX-License-Identifier: MIT
"""Tests for vision support: view_image tool, PENDING_IMAGE, vision detection.

Covers:
- tool_view_image: valid image, missing file, unsupported format, oversized
- _check_vision_support: keyword detection in MODEL_NAME
- _get_media_type: extension to MIME mapping
- PENDING_IMAGE lifecycle
"""

import base64
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trashclaw


@pytest.fixture(autouse=True)
def reset_vision(monkeypatch):
    """Reset vision globals before each test."""
    monkeypatch.setattr(trashclaw, "PENDING_IMAGE", None)
    monkeypatch.setattr(trashclaw, "VISION_SUPPORTED", None)


@pytest.fixture
def sample_png(tmp_path, monkeypatch):
    """Create a minimal valid PNG file."""
    monkeypatch.setattr(trashclaw, "CWD", str(tmp_path))
    # Minimal 1x1 red PNG (67 bytes)
    png_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
        "2mP8/58BAwAI/AL+hc2rNAAAAABJRU5ErkJggg=="
    )
    img_path = tmp_path / "test.png"
    img_path.write_bytes(png_data)
    return str(img_path)


@pytest.fixture
def sample_jpg(tmp_path, monkeypatch):
    """Create a minimal JPEG file."""
    monkeypatch.setattr(trashclaw, "CWD", str(tmp_path))
    # Minimal JPEG (just header bytes for testing)
    jpg_data = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00,
        0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xD9
    ])
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(jpg_data)
    return str(img_path)


class TestViewImage:
    """Test tool_view_image function."""

    def test_load_png(self, sample_png):
        result = trashclaw.tool_view_image(sample_png)
        assert "Image loaded" in result
        assert "test.png" in result
        assert "image/png" in result
        assert trashclaw.PENDING_IMAGE is not None
        assert trashclaw.PENDING_IMAGE["media_type"] == "image/png"
        assert len(trashclaw.PENDING_IMAGE["base64"]) > 0

    def test_load_jpg(self, sample_jpg):
        result = trashclaw.tool_view_image(sample_jpg)
        assert "Image loaded" in result
        assert trashclaw.PENDING_IMAGE["media_type"] == "image/jpeg"

    def test_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(trashclaw, "CWD", str(tmp_path))
        result = trashclaw.tool_view_image("/nonexistent/image.png")
        assert "Error" in result
        assert "not found" in result.lower()
        assert trashclaw.PENDING_IMAGE is None

    def test_unsupported_format(self, tmp_path, monkeypatch):
        monkeypatch.setattr(trashclaw, "CWD", str(tmp_path))
        txt_file = tmp_path / "not_image.txt"
        txt_file.write_text("hello")
        result = trashclaw.tool_view_image(str(txt_file))
        assert "Error" in result
        assert "Unsupported" in result
        assert trashclaw.PENDING_IMAGE is None

    def test_relative_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(trashclaw, "CWD", str(tmp_path))
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
            "2mP8/58BAwAI/AL+hc2rNAAAAABJRU5ErkJggg=="
        )
        img_path = tmp_path / "relative.png"
        img_path.write_bytes(png_data)
        result = trashclaw.tool_view_image("relative.png")
        assert "Image loaded" in result


class TestMediaType:
    """Test _get_media_type function."""

    def test_png(self):
        assert trashclaw._get_media_type("photo.png") == "image/png"

    def test_jpg(self):
        assert trashclaw._get_media_type("photo.jpg") == "image/jpeg"

    def test_jpeg(self):
        assert trashclaw._get_media_type("photo.jpeg") == "image/jpeg"

    def test_gif(self):
        assert trashclaw._get_media_type("anim.gif") == "image/gif"

    def test_webp(self):
        assert trashclaw._get_media_type("photo.webp") == "image/webp"

    def test_bmp(self):
        assert trashclaw._get_media_type("old.bmp") == "image/bmp"

    def test_unknown_defaults_png(self):
        assert trashclaw._get_media_type("file.xyz") == "image/png"


class TestVisionDetection:
    """Test _check_vision_support based on MODEL_NAME."""

    def test_llava_detected(self, monkeypatch):
        monkeypatch.setattr(trashclaw, "MODEL_NAME", "llava-v1.6-34b")
        monkeypatch.setattr(trashclaw, "VISION_SUPPORTED", None)
        assert trashclaw._check_vision_support() is True

    def test_qwen_vl_detected(self, monkeypatch):
        monkeypatch.setattr(trashclaw, "MODEL_NAME", "Qwen2-VL-7B")
        monkeypatch.setattr(trashclaw, "VISION_SUPPORTED", None)
        assert trashclaw._check_vision_support() is True

    def test_plain_llama_not_detected(self, monkeypatch):
        monkeypatch.setattr(trashclaw, "MODEL_NAME", "llama-3.1-8b")
        monkeypatch.setattr(trashclaw, "VISION_SUPPORTED", None)
        # Will try /v1/models which will fail, so returns False
        assert trashclaw._check_vision_support() is False

    def test_cached_result(self, monkeypatch):
        monkeypatch.setattr(trashclaw, "VISION_SUPPORTED", True)
        # Should return cached value regardless of MODEL_NAME
        monkeypatch.setattr(trashclaw, "MODEL_NAME", "llama-3.1-8b")
        assert trashclaw._check_vision_support() is True

    def test_gpt4o_detected(self, monkeypatch):
        monkeypatch.setattr(trashclaw, "MODEL_NAME", "gpt-4o")
        monkeypatch.setattr(trashclaw, "VISION_SUPPORTED", None)
        assert trashclaw._check_vision_support() is True


class TestPendingImageLifecycle:
    """Test that PENDING_IMAGE is consumed correctly."""

    def test_starts_none(self):
        assert trashclaw.PENDING_IMAGE is None

    def test_set_after_view_image(self, sample_png):
        trashclaw.tool_view_image(sample_png)
        assert trashclaw.PENDING_IMAGE is not None
        assert "base64" in trashclaw.PENDING_IMAGE
        assert "media_type" in trashclaw.PENDING_IMAGE
        assert "path" in trashclaw.PENDING_IMAGE

    def test_overwrite_on_second_load(self, sample_png, sample_jpg):
        trashclaw.tool_view_image(sample_png)
        assert trashclaw.PENDING_IMAGE["media_type"] == "image/png"
        trashclaw.tool_view_image(sample_jpg)
        assert trashclaw.PENDING_IMAGE["media_type"] == "image/jpeg"
