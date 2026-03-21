#!/bin/bash
# Apply Metal fix for discrete AMD GPUs to llama.cpp
# Reference: https://github.com/ggml-org/llama.cpp/pull/20615
#
# This script applies the StorageModeManaged fix that was rejected by llama.cpp
# but is required for discrete AMD GPUs on macOS (Mac Pro 2013, iMac 2014-2019, etc.)

set -e

echo "🔧 Applying Metal fix for discrete AMD GPUs..."

# Check if we're on macOS
if [[ "$(uname)" != "Darwin" ]]; then
    echo "❌ This fix is only for macOS systems"
    exit 1
fi

# Find llama.cpp directory
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$HOME/llama.cpp}"

if [ ! -d "$LLAMA_CPP_DIR" ]; then
    echo "❌ llama.cpp not found at $LLAMA_CPP_DIR"
    echo "   Set LLAMA_CPP_DIR or install llama.cpp first"
    exit 1
fi

echo "📁 Found llama.cpp at: $LLAMA_CPP_DIR"

# The 3-line fix for StorageModeManaged
# This changes the memory type from MTLResourceStorageModePrivate to MTLResourceStorageModeManaged
# for discrete GPUs, which don't have unified memory

PATCH_FILE=$(mktemp)
cat > "$PATCH_FILE" << 'EOF'
--- a/ggml-metal.m
+++ b/ggml-metal.m
@@ -442,7 +442,11 @@ static enum ggml_status ggml_metal_graph_compute(
         // for unified memory (integrated GPUs), MTLResourceStorageModeShared is optimal
         // for discrete GPUs, we need MTLResourceStorageModeManaged because they don't have
         // direct access to system memory
+#if defined(__MAC_10_15) && __MAC_OS_X_VERSION_MAX_ALLOWED >= __MAC_10_15
         const MTLResourceOptions options = MTLResourceStorageModeShared;
+        if ([device supportsFamily:MTLGPUFamilyMac2]) {
+            options = MTLResourceStorageModeManaged;
+        }
+#else
+        const MTLResourceOptions options = MTLResourceStorageModeShared;
+#endif
EOF

# Apply the patch
cd "$LLAMA_CPP_DIR"

if patch -p1 --dry-run < "$PATCH_FILE" > /dev/null 2>&1; then
    echo "✅ Patch can be applied"
    patch -p1 < "$PATCH_FILE"
    echo "✅ Metal fix applied successfully!"
    echo ""
    echo "📝 Next steps:"
    echo "   1. cd $LLAMA_CPP_DIR"
    echo "   2. make clean"
    echo "   3. make -j$(sysctl -n hw.ncpu)"
    echo "   4. ./bin/llama-server -m your-model.gguf"
else
    echo "⚠️  Patch may already be applied or conflicts exist"
    echo "   Check $LLAMA_CPP_DIR/ggml-metal.m manually"
fi

rm -f "$PATCH_FILE"
