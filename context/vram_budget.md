# VRAM Budget — RTX 3070 (8 GB)

## Current Allocation

| Component | Model | Quantization | VRAM | Status |
|---|---|---|---|---|
| STT | faster-whisper distil-large-v3 | INT8 | 1.5 GB | Planned |
| LLM | Qwen3 8B | Q4_K_M | 4.5 GB | Planned |
| TTS | Kokoro-82M | FP16 | 0.2 GB | Planned |
| **Total** | | | **6.2 GB** | |
| **Headroom** | | | **1.8 GB** | |

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

- [ ] STT loaded - VRAM: ~1.5 GB (estimated, Windows WDDM doesn't show per-process accurately)

## Notes

- VRAM measurements are approximate — actual usage depends on batch size, context length, and CUDA allocator behavior
- Ollama may use slightly more VRAM than raw model size due to KV cache
- faster-whisper VRAM usage increases with audio length (beam search buffers)
