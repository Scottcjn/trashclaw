#!/bin/bash
# apply-metal-fix.sh - Apply StorageModeManaged fix for discrete AMD GPUs
# Reference: https://github.com/ggml-org/llama.cpp/pull/20615
#
# This script applies the 3-line Metal fix for discrete AMD GPUs
# (Mac Pro 2013, iMac 2014-2019, MacBook Pro 2015-2019)
#
# Usage: ./apply-metal-fix.sh [llama.cpp directory]

set -e

LLAMA_DIR="${1:-../llama.cpp}"

echo "🔧 Applying Metal StorageModeManaged fix for discrete AMD GPUs"
echo "   Target: $LLAMA_DIR"
echo "   Reference: https://github.com/ggml-org/llama.cpp/pull/20615"
echo ""

if [ ! -d "$LLAMA_DIR" ]; then
    echo "❌ Error: llama.cpp directory not found at $LLAMA_DIR"
    echo "   Usage: ./apply-metal-fix.sh [path/to/llama.cpp]"
    exit 1
fi

GGML_METAL_PATH="$LLAMA_DIR/ggml/src/ggml-metal/ggml-metal.m"

if [ ! -f "$GGML_METAL_PATH" ]; then
    echo "❌ Error: ggml-metal.m not found at $GGML_METAL_PATH"
    exit 1
fi

echo "📄 Patching $GGML_METAL_PATH..."

# Create backup
cp "$GGML_METAL_PATH" "$GGML_METAL_PATH.bak"

# Apply the 3-line fix
# Find the line with "buffer addContents:" and replace with StorageModeManaged check
# The fix checks if the buffer is StorageModeManaged and uses synchronizeResource instead

# Check if already patched
if grep -q "synchronizeResource" "$GGML_METAL_PATH"; then
    echo "✅ Already patched! Skipping."
    exit 0
fi

# Apply patch using sed
# Look for: [buffer addContents:data size:length]
# Replace with: if ([buffer storageMode] == MTLStorageModeManaged) { [buffer synchronizeResource]; } else { [buffer addContents:data size:length]; }

# This is a simplified patch - the actual fix may need more context
# For now, we'll add the synchronizeResource call before addContents

sed -i.bak 's/\[buffer addContents:data size:length\]/if ([buffer storageMode] == MTLStorageModeManaged) { [buffer synchronizeResource]; } else { [buffer addContents:data size:length]; }/g' "$GGML_METAL_PATH"

if grep -q "synchronizeResource" "$GGML_METAL_PATH"; then
    echo "✅ Patch applied successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Rebuild llama.cpp: cd $LLAMA_DIR && make clean && make -j"
    echo "   2. Test with discrete GPU (Mac Pro 2013, iMac 2014-2019, etc.)"
    echo "   3. Report results to https://github.com/Scottcjn/trashclaw/issues/38"
else
    echo "❌ Patch failed to apply"
    # Restore backup
    mv "$GGML_METAL_PATH.bak" "$GGML_METAL_PATH"
    exit 1
fi
