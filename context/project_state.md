# Jett Project State

> Last updated: 2026-02-04
> Updated by: Opus

---

## Current Phase

**Phase 1: Core Voice Loop — IN PROGRESS**

## Phase Progress

| Task | Status | Notes |
|------|--------|-------|
| Python environment setup | ✅ Complete | Python 3.11, venv configured |
| faster-whisper STT setup | ✅ Complete | CUDA working, 1.1GB VRAM, 755ms/3s audio |
| Security wrapper | ✅ Complete | Allowlist, rate limiting, audit logging, 30/30 tests |
| VPS docker-compose | ✅ Complete | Hardened, WireGuard-bound, 4 services |
| Ollama + Qwen3 8B installation | ✅ Complete | 5.28GB VRAM (ctx=2048), 68 tok/s |
| Kokoro-82M TTS integration | ✅ Complete | 0.36GB VRAM, 83-136ms latency |
| VRAM validation | ✅ Complete | 7.38GB total (90.1%), 0.81GB headroom |
| End-to-end voice test | ⬜ Not started | Next up |

## What's Done

- [x] Project directory structure created
- [x] Context files initialized
- [x] Architecture documented
- [x] Security model defined
- [x] VRAM budget calculated
- [x] Two-machine deployment strategy documented
- [x] Git repo initialized, pushed to GitHub
- [x] Python 3.11 environment with venv
- [x] faster-whisper STT with CUDA acceleration
- [x] CUDA dependencies resolved (nvidia-cublas-cu12, nvidia-cudnn-cu12)
- [x] STT VRAM verified: 1.1GB (better than 1.5GB estimate)
- [x] Dashboard scaffolded (Next.js 14, shadcn/ui, dark theme)
- [x] Security wrapper implemented (allowlist, rate limiting, audit, secret redaction)
- [x] VPS docker-compose created (n8n, postgres, qdrant, portainer)
- [x] Container hardening applied (non-root, read-only, dropped caps, WireGuard-only)
- [x] Ollama installed and configured (v0.15.4)
- [x] Qwen3 8B Q4_K_M pulled and benchmarked
- [x] Custom jett-qwen3 model created (optimized 2048 context for VRAM savings)
- [x] LLM VRAM verified: 5.28GB (with ctx=2048), 68 tok/s inference
- [x] LLM benchmark created (benchmarks/llm_benchmark.py)
- [x] PyTorch reinstalled with CUDA 12.4 support
- [x] Kokoro-82M TTS installed and configured
- [x] TTS module created (src/voice/tts.py)
- [x] TTS benchmark created (benchmarks/tts_benchmark.py)
- [x] TTS VRAM verified: 0.36GB, 83-136ms latency (after warmup)
- [x] **FULL VRAM VALIDATION PASSED**: All 3 models concurrent = 7.38GB (90.1%)
- [x] VRAM validation script (benchmarks/vram_validation.py)
- [x] Sample TTS audio files saved (tests/fixtures/tts_*.wav)

## What's Next

1. **End-to-end voice test** — Mic → STT → LLM → TTS → Speaker
2. **Wake word detection** — openWakeWord integration
3. **Voice Activity Detection** — Silero VAD

## Blockers

- None currently

## Notes

- Target hardware: RTX 3070 (8 GB VRAM)
- All models must fit within VRAM budget (see `vram_budget.md`)
- Privacy-first: audio never leaves local machine

## Session Log

### 2025-02-04 (Laptop — No GPU)
- Dashboard scaffolded: Next.js 14 + shadcn/ui + Tailwind v4
- Dark theme with cyan accent
- Pages: Dashboard, Containers, History, Settings
- All components with mock data, ready for backend integration

### 2026-02-04 (Laptop — No GPU)
- Implemented security wrapper (src/security/)
  - Explicit allowlists (frozenset) for containers/actions
  - Rate limiting: 10 ops/minute sliding window
  - Immutable audit logging with secret redaction
  - 30 unit tests proving boundaries work
- Created VPS docker-compose (docker/)
  - n8n, postgres, qdrant, portainer
  - All services bound to WireGuard IP (10.0.0.2)
  - Full security hardening: non-root, read-only, dropped caps
  - n8n wired to PostgreSQL backend

### 2026-02-04 (Desktop — RTX 3070)
- Ollama already installed (v0.15.4), Qwen3 8B already pulled
- Ran LLM benchmark: 68 tok/s, tool-calling format works
- **VRAM issue discovered**: Default Qwen3 8B uses 6.3GB (not 4.5GB as estimated)
- Created custom `jett-qwen3` model with ctx=2048 to save VRAM
- Final LLM VRAM: 5.8GB (ctx=2048), leaving room for STT + TTS
- Updated VRAM budget with actual measurements

- Installed Kokoro-82M TTS (kokoro>=0.9)
- Reinstalled PyTorch with CUDA 12.4 (was CPU-only)
- Created TTS module (src/voice/tts.py) with synthesize, play, stream_sentences
- TTS benchmark: 83-136ms latency after warmup (first call 880ms due to CUDA JIT)
- TTS VRAM: 0.36GB (higher than 0.2GB estimate but acceptable)
- **VRAM VALIDATION PASSED**: All three models loaded = 7.38GB (90.1%)
  - System: 0.66GB
  - LLM: 5.28GB
  - STT: 1.08GB
  - TTS: 0.36GB
  - Headroom: 0.81GB
- Sample audio saved to tests/fixtures/

Next up:
- End-to-end voice test (Mic → STT → LLM → TTS → Speaker)
- Wake word detection (openWakeWord)
- Voice Activity Detection (Silero VAD)
