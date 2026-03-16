#!/bin/bash
# Wrapper script to run llama-server across dual AMD FirePro D500 GPUs on the 2013 Mac Pro
# Uses the RPC backend to split layers across the two GPUs (3GB VRAM each).
# Requires llama-rpc-server and llama-server to be built with RPC support.

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_model.gguf> [additional llama-server args...]"
    exit 1
fi

MODEL=$1
shift

# Default RPC port
RPC_PORT=50052

echo "=> Starting llama-rpc-server on GPU 1 (AMD FirePro D500 #2)..."
# Start RPC server in background, locking it to the second GPU if possible
# (Metal device selection can be forced via GGML_METAL_DEVICE_ID=1)
GGML_METAL_DEVICE_ID=1 llama-rpc-server -H 127.0.0.1 -p $RPC_PORT &
RPC_PID=$!

sleep 2 # wait for RPC server to start

echo "=> Starting llama-server on GPU 0 (AMD FirePro D500 #1) with RPC offload to GPU 1..."
# Start main server on GPU 0, offloading half the layers to the RPC server on GPU 1
GGML_METAL_DEVICE_ID=0 llama-server \
    -m "$MODEL" \
    --host 0.0.0.0 --port 8080 \
    --rpc 127.0.0.1:$RPC_PORT \
    -ngl 99 \
    -ts 1,1 \
    "$@"

# Cleanup RPC server on exit
kill $RPC_PID
