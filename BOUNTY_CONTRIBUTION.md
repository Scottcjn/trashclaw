# Bounty Contribution

This addresses issue #2: Dual GPU support - use both FirePro D500s (50 RTC)

## Description
## Bounty: 50 RTC

Enable both AMD FirePro D500 GPUs (6GB total VRAM) for inference.

### Background
The 2013 Mac Pro has 2x FirePro D500 (3GB each). Currently llama.cpp uses MTLCreateSystemDefaultDevice() which only sees GPU 0. We need MTLCopyAllDevices() and tensor splitting across both devices.

### Requirements
- Split model layers across both D500s via Metal
- Or: pipeline parallelism (one GPU does early layers, other does late layers)
- Benchmark showing improvement over single GPU
- Must 

## Payment
0x4F666e7b4F63637223625FD4e9Ace6055fD6a847
