# Jett Project State

> Last updated: 2026-02-04
> Updated by: Opus

---

## Current Phase

**Phase 1: Core Voice Loop — IN PROGRESS**

## Phase Progress

| Task | Status | Notes |
|------|--------|-------|
| Python environment setup | ✅ Complete | Python 3.14.2, venv configured |
| faster-whisper STT setup | ✅ Complete | CUDA working, 1.1GB VRAM, 755ms/3s audio |
| Security wrapper | ✅ Complete | Allowlist, rate limiting, audit logging, 30/30 tests |
| VPS docker-compose | ✅ Complete | Hardened, WireGuard-bound, 4 services |
| Ollama + Qwen3 8B installation | ✅ Complete | 5.8GB VRAM (ctx=2048), 68 tok/s |
| Kokoro-82M TTS integration | ⬜ Not started | Next up |
| End-to-end voice test | ⬜ Not started | After TTS |
| VRAM validation | 🟡 In progress | STT + LLM verified, TTS pending |

## What's Done

- [x] Project directory structure created
- [x] Context files initialized
- [x] Architecture documented
- [x] Security model defined
- [x] VRAM budget calculated
- [x] Two-machine deployment strategy documented
- [x] Git repo initialized, pushed to GitHub
- [x] Python 3.14.2 environment with venv
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
- [x] LLM VRAM verified: 5.8GB (with ctx=2048), 68 tok/s inference
- [x] LLM benchmark created (benchmarks/llm_benchmark.py)

## What's Next

1. **Integrate Kokoro-82M TTS** — Verify 0.2GB VRAM
2. **VRAM validation** — All three models loaded simultaneously (~7.1GB projected)
3. **End-to-end voice test** — Mic → STT → LLM → TTS → Speaker

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

Next up:
- Integrate Kokoro-82M TTS
- Load all three models simultaneously for VRAM validation
- End-to-end voice test
