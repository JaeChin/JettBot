# Jett VRAM Budget

> Two-environment model: Development (desktop) + Production (laptop appliance)
> Last updated: 2025-02-04 by Opus

---

## Environment Overview

| Environment | Machine | GPU | VRAM | RAM | Purpose |
|-------------|---------|-----|------|-----|---------|
| **Development** | Desktop PC | RTX 3070 | 8 GB | 32 GB | Iteration, testing, benchmarking |
| **Production** | Lenovo Legion Y740-17 | RTX 2070 Max-Q | 8 GB | 16 GB (→32 GB) | 24/7 headless appliance |

**Why two environments:** The desktop is the daily driver for gaming and other dev work — can't dedicate it 24/7. The Y740 runs Jett as a headless Ubuntu Server appliance on ethernet, always available. The 2070 Max-Q has the same 8 GB VRAM but ~60-65% of the 3070's compute throughput and thermal constraints under sustained load. Production config is right-sized for reliability, not maximum capability.

---

## Development Environment (RTX 3070 Desktop)

Use this for prompt engineering, model comparison, benchmarking, and feature development.

| Component | Model/Config | Allocated | Actual | Status |
|-----------|-------------|-----------|--------|--------|
| STT | faster-whisper distil-large-v3 (INT8) | 1.5 GB | - | Pending |
| LLM | Qwen3 8B Q4_K_M via Ollama | 5.8 GB | - | Pending |
| TTS | Kokoro-82M | 0.2 GB | - | Pending |
| **Total** | | **7.5 GB** | - | |
| **Headroom** | | **0.5 GB** | - | Tight — close background GPU apps |

> **Note:** Qwen3 8B measured at 5.8 GB with 2048 context (not 4.5 GB as originally projected). Usable for development sessions but not suitable for 24/7 operation. Kill GPU-using background apps (browsers with HW accel, Discord overlay, etc.) before loading all models.

### Dev Environment Rules
- Load models only during active development sessions
- Unload when gaming or doing other GPU work
- Use this environment for A/B testing local vs production model configs
- Benchmark latency here, then validate on production hardware

---

## Production Environment (RTX 2070 Max-Q Laptop)

Optimized for 24/7 reliability on thermally constrained hardware.

| Component | Model/Config | Allocated | Actual | Status |
|-----------|-------------|-----------|--------|--------|
| STT | faster-whisper distil-large-v3 (INT8) | 1.5 GB | - | Pending |
| LLM | **Qwen3 4B Q4_K_M** via Ollama | ~2.5 GB | - | Pending |
| TTS | Kokoro-82M | 0.2 GB | - | Pending |
| **Total** | | **~4.2 GB** | - | |
| **Headroom** | | **~3.8 GB** | - | Comfortable for 24/7 |

### Why Qwen3 4B for Production
- Same model family as 8B — inherits strong tool-calling architecture
- ~90 tokens/sec on 2070 Max-Q (faster than 8B on 3070)
- 3.8 GB headroom means no OOM risk during inference spikes
- Handles all simple commands (timers, device control, calendar, status queries) reliably
- Complex queries route to Claude anyway — the hybrid router is the safety net

### Production Hardware Constraints
- **Thermal:** 2070 Max-Q is power-limited (80-90W vs 220W desktop). Sustained inference will thermal throttle without proper cooling.
- **Cooling plan:** Laptop on elevated stand, lid open, external fan pad. Monitor temps via `nvidia-smi`.
- **RAM:** 16 GB is tight for Ubuntu Server + Docker + Python + models. **Upgrade to 32 GB before deployment** (~$30-50 for DDR4 SODIMMs). Verify Y740-17 has 2 SODIMM slots (most configs do).
- **OS:** Ubuntu Server 24.04 LTS (headless, no desktop environment consuming resources)
- **Network:** Ethernet to router + WireGuard tunnel to VPS

### Production Stability Targets
- VRAM usage: **never exceed 5.5 GB** (leave 2.5 GB buffer for spikes + driver overhead)
- GPU temp: **sustained <80°C** (throttling typically starts at 83-87°C on Max-Q)
- Uptime target: 99%+ (reboot only for OS updates)

---

## Measurement Commands

```bash
# Check current VRAM usage
nvidia-smi --query-gpu=memory.used,memory.total,memory.free --format=csv

# Continuous monitoring (essential for production)
watch -n 1 nvidia-smi

# Temperature monitoring
nvidia-smi --query-gpu=temperature.gpu --format=csv -l 5

# Full dashboard (use this for benchmarking sessions)
nvidia-smi dmon -s pucvmet -d 1
```

---

## Routing Impact by Environment

The smaller production model shifts the local/cloud routing ratio:

| Metric | Development (8B) | Production (4B) |
|--------|-------------------|-------------------|
| Local routing % | ~70% | ~55-60% |
| Cloud routing % | ~30% | ~40-45% |
| Estimated monthly cloud cost | $5-15 | $15-25 |
| Tool-calling reliability | Excellent | Good |
| Complex reasoning (local) | Moderate | Limited (routes to cloud) |

This is by design. The production environment leans more on the hybrid router, which actually makes the routing architecture more important and demonstrable.

---

## Fallback Configurations

### If Production VRAM Is Still Too Tight

| Change | VRAM Saved | Trade-off |
|--------|-----------|-----------|
| STT → distil-medium.en | ~0.7 GB | English only, slightly lower accuracy |
| TTS → Piper (CPU only) | ~0.2 GB | Lower voice quality, uses CPU instead |
| LLM → Phi-3.5 Mini 3.8B | ~0 GB (similar) | Weaker tool-calling than Qwen3 |

### If Production Thermals Are Bad

| Change | Impact |
|--------|--------|
| Reduce LLM context to 1024 tokens | Less VRAM, less compute per query |
| Increase cloud routing threshold | More queries go to Claude, less GPU load |
| Add inference cooldown (100ms between queries) | Prevents thermal spikes during rapid interaction |

---

## Validation Checkpoints

### Development Environment (Desktop)
- [ ] STT loaded — VRAM: ___ MB
- [ ] LLM (Qwen3 8B) loaded — VRAM: ___ MB
- [ ] TTS loaded — VRAM: ___ MB
- [ ] All three simultaneous — VRAM: ___ MB
- [ ] Under 8 GB confirmed: YES / NO

### Production Environment (Laptop)
- [ ] STT loaded — VRAM: ___ MB
- [ ] LLM (Qwen3 4B) loaded — VRAM: ___ MB
- [ ] TTS loaded — VRAM: ___ MB
- [ ] All three simultaneous — VRAM: ___ MB
- [ ] Under 5.5 GB confirmed: YES / NO
- [ ] GPU temp under sustained load: ___ °C
- [ ] 1-hour stability test passed: YES / NO
- [ ] RAM usage (system total): ___ / 16 GB (or 32 GB after upgrade)

---

## Hardware Upgrade Tracker

| Upgrade | Cost | Priority | Status |
|---------|------|----------|--------|
| Y740 RAM → 32 GB (2x16 GB DDR4 SODIMM) | ~$30-50 | **High** (before deployment) | ⬜ Not purchased |
| Laptop cooling stand/fan pad | ~$20-30 | Medium (before 24/7 operation) | ⬜ Not purchased |
| Verify Y740 SODIMM slot count | $0 | **High** (before ordering RAM) | ⬜ Not checked |

---

## Notes

- Qwen3 8B measured at 5.8 GB with 2048 context — significantly over the original 4.5 GB projection
- The 2070 Max-Q has identical VRAM (8 GB) but lower compute bandwidth and thermal limits
- Ubuntu Server (headless) uses ~0 GPU VRAM vs Windows which reserves 300-500 MB for display
- Production headroom is intentionally generous — 24/7 appliances need reliability above all
- Both environments use identical STT and TTS configs — only the LLM differs
- Config files should use environment variables to switch between dev/prod LLM endpoints
