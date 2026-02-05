# VRAM Budget — RTX 3070 (8 GB)

## Current Allocation

| Component | Model | Quantization | VRAM | Status |
|---|---|---|---|---|
| STT | faster-whisper distil-large-v3 | INT8 | **1.1 GB** | Verified |
| LLM | Qwen3 8B | Q4_K_M (ctx=2048) | **5.3 GB** | Verified |
| TTS | Kokoro-82M | FP16 | 0.2 GB | Planned |
| System | CUDA/OS overhead | - | 0.7 GB | Measured |
| **Total** | | | **7.3 GB** | |
| **Headroom** | | | **0.7 GB** | |

> **Note:** VRAM is tighter than originally estimated. Using reduced context window (2048) for voice assistant use case where queries are short.

## LLM Context Window vs VRAM

Measured on RTX 3070 with Qwen3 8B Q4_K_M:

| Context | VRAM | Use Case |
|---------|------|----------|
| 512 | 5.7 GB | Minimal (single-turn only) |
| 1024 | 5.8 GB | Short conversations |
| 2048 | 6.0 GB | Voice assistant (recommended) |
| 4096 | 6.3 GB | Extended context (default) |

For Jett voice assistant, **2048 context** is recommended — sufficient for voice queries while leaving headroom.

## Budget Rules

1. **Total must not exceed 7.0 GB** — Keep 1.0 GB minimum headroom for CUDA overhead and OS
2. **Every model change must update this file** — No exceptions
3. **Measure actual VRAM, not estimates** — Use `nvidia-smi` to verify after loading
4. **Concurrent loading matters** — All three models loaded simultaneously during operation

## Measurement Commands

```bash
# Check current VRAM usage
nvidia-smi

# Detailed per-process VRAM
nvidia-smi --query-compute-apps=pid,name,used_memory --format=csv

# Monitor in real-time
watch -n 1 nvidia-smi
```

## Fallback Options

If VRAM budget is exceeded:

| Option | VRAM Saved | Trade-off |
|---|---|---|
| Qwen3 8B → Q3_K_M | ~0.5 GB | Reduced quality |
| distil-large-v3 → distil-medium | ~0.5 GB | Reduced accuracy |
| Qwen3 8B → Qwen3 4B | ~2.0 GB | Significantly reduced capability |
| Offload STT to CPU | 1.5 GB | Higher STT latency |

## Validation Checkpoints

- [x] STT loaded - VRAM: 1.1 GB
- [x] LLM loaded - VRAM: 5.3 GB (ctx=2048), 68 tok/s inference speed

## LLM Benchmark Results (2026-02-04)

| Test | Latency | Tokens/s |
|------|---------|----------|
| Simple Query | 6.5s | 68.5 |
| Command Interpretation | 6.5s | 67.8 |
| Short Explanation | 7.1s | 69.2 |
| Tool Call Format | 4.5s | 67.2 |

Tool calling works correctly — model produces valid JSON for function calls.

## Notes

- VRAM measurements are approximate — actual usage depends on batch size, context length, and CUDA allocator behavior
- Ollama may use slightly more VRAM than raw model size due to KV cache
- faster-whisper VRAM usage increases with audio length (beam search buffers)
