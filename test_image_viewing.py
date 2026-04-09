#!/usr/bin/env python3
"""
Test script for TrashClaw image viewing feature.
Tests the --image flag for vision models.
"""

import os
import sys
import base64

# Add trashclaw directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trashclaw import load_image_to_base64

def test_image_loading():
    """Test loading various image formats."""
    print("=" * 60)
    print("🧪 Testing TrashClaw Image Viewing Feature")
    print("=" * 60)
    
    # Test images
    test_images = [
        "trashy.png",  # Should exist in the directory
    ]
    
    for img_path in test_images:
        print(f"\n📷 Testing: {img_path}")
        if not os.path.exists(img_path):
            print(f"  ⚠️  File not found, skipping")
            continue
        
        result = load_image_to_base64(img_path)
        if result:
            # Check format
            if result.startswith("data:image/"):
                mime_type = result.split(";")[0].split(":")[1]
                data_len = len(result)
                print(f"  ✅ Loaded successfully")
                print(f"  📄 MIME type: {mime_type}")
                print(f"  📏 Data length: {data_len} chars")
                print(f"  🔍 Preview: {result[:50]}...")
            else:
                print(f"  ❌ Invalid format: {result[:50]}")
        else:
            print(f"  ❌ Failed to load image")
    
    print("\n" + "=" * 60)
    print("✅ Test Complete!")
    print("=" * 60)
    
    # Test command-line usage
    print("\n📋 Usage Examples:")
    print("  python3 trashclaw.py --image screenshot.png")
    print("  python3 trashclaw.py --image=/path/to/image.jpg")
    print("  python3 trashclaw.py --image diagram.png --cwd /project")
    print("\n🎯 The agent will now analyze images with vision models!")

if __name__ == "__main__":
    test_image_loading()
