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
| Ollama + Qwen3 8B installation | ⬜ Not started | Next up (needs GPU) |
| Kokoro-82M TTS integration | ⬜ Not started | Needs GPU |
| End-to-end voice test | ⬜ Not started | Needs GPU |
| VRAM validation | 🟡 In progress | STT verified, LLM/TTS pending |

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

## What's Next

1. **Install Ollama** — Local LLM runtime
2. **Pull Qwen3 8B** — Q4_K_M quantization, verify 4.5GB VRAM
3. **Integrate Kokoro-82M TTS** — Verify 0.2GB VRAM
4. **VRAM validation** — All three models loaded simultaneously
5. **End-to-end voice test** — Mic → STT → LLM → TTS → Speaker

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

Next session (GPU):
- Install Ollama + pull Qwen3 8B
- Test LLM inference, measure VRAM
- Install Kokoro-82M TTS
- Wire STT → LLM → TTS for end-to-end test
