# Jett Project State

> Last updated: 2026-02-07
> Updated by: Opus

---

## Current Phase: Phase 3 — Hybrid Routing & Custom Wake Word

---

## Phase 1: Core Voice Loop — ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| Python environment | ✅ | 3.11, CUDA working |
| faster-whisper STT | ✅ | 1.08 GB VRAM, distil-large-v3 INT8 |
| Security wrapper | ✅ | 30/30 tests, explicit allowlists |
| VPS docker-compose | ✅ | Hardened, WireGuard-bound |
| Ollama + Qwen3 8B | ✅ | 5.28 GB VRAM, 100% GPU |
| Kokoro TTS | ✅ | 0.36 GB VRAM |
| VRAM validation | ✅ | 7.38 GB total (0.81 GB headroom) |
| E2E voice pipeline | ✅ | Working, state machine, no echo |
| Latency optimization | ✅ | 3.2s perceived latency |
| VRAM-aware startup | ✅ | Checks GPU memory before loading |

### Phase 1 Final Metrics

| Metric | Value |
|--------|-------|
| STT latency | 670ms |
| LLM first token | 2.15s |
| LLM total (11 tok) | 2.6s |
| TTS first audio | 325ms |
| User-perceived latency | **3.2s** |
| E2E (incl. playback) | 6.7s |
| Response length | 11 tokens avg |

---

## Phase 2: Wake Word & VAD — ✅ COMPLETE

| Task | Status | Notes |
|------|--------|-------|
| openWakeWord setup | ✅ | Working with hey_jarvis, 0.99+ confidence |
| Silero VAD integration | ✅ | Using openWakeWord's built-in VAD |
| Always-listening daemon | ✅ | Wake word detector runs continuously on CPU |
| Custom "Hey Jett" model | ⬜ | Future (currently using hey_jarvis) |

### Phase 2 Final Metrics

| Metric | Value |
|--------|-------|
| Wake word confidence | 0.99+ |
| LLM first token | ~2.2s |
| E2E (incl. playback) | 6-9s |
| Wake word CPU usage | ~1% |
| VRAM impact | 0 (CPU-only) |

---

## Phase 3: Hybrid Routing & Custom Wake Word — NOT STARTED

| Task | Status | Notes |
|------|--------|-------|
| Custom "Hey Jett" wake word | ⬜ | Train custom openWakeWord model |
| Silero VAD for silence detection | ⬜ | Replace energy-based silence detection |
| Hybrid routing (local + cloud LLM) | ⬜ | Route complex queries to cloud |

---

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
- [x] STT VRAM verified: 1.08GB (better than 1.5GB estimate)
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
- [x] **E2E Voice Pipeline** (src/voice/pipeline.py) — STT → LLM → TTS working
- [x] Main entry point (src/main.py) — `python -m src.main`
- [x] E2E benchmark (benchmarks/e2e_benchmark.py)
- [x] VRAM-aware startup (src/main.py, scripts/start_jett.py) — checks free GPU memory before loading
- [x] Disabled Qwen3 thinking mode — 1.5s faster, 80 fewer tokens per response
- [x] Brevity system prompt — 1-2 sentence max responses
- [x] Detailed pipeline metrics — full component timing breakdown

## Blockers

- None currently

## Notes

- Target hardware: RTX 3070 (8 GB VRAM)
- All models must fit within VRAM budget (see `vram_budget.md`)
- Privacy-first: audio never leaves local machine
- **VRAM contention**: Close GPU-heavy apps (Chrome, Discord, NVIDIA Broadcast) before running on dev machine. Models need ~6.8 GB free to load fully on GPU. Partial CPU offload causes 5-10x LLM latency.

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

**E2E Voice Pipeline Complete:**
- Created VoicePipeline class (src/voice/pipeline.py)
  - Mic input with silence-based speech detection
  - STT transcription (faster-whisper)
  - LLM response generation (Ollama streaming)
  - TTS synthesis sentence-by-sentence
  - Speaker playback with threading
- Main entry point: `python -m src.main`
- E2E benchmark with pre-recorded audio

**Latency Optimization (after tuning):**
| Stage | Before | After | Target |
|-------|--------|-------|--------|
| STT | 750ms | 655ms | <300ms |
| LLM first token | 6000ms | 2200ms* | <500ms |
| TTS first audio | 450ms | 255ms | <100ms |
| E2E (short prompts) | 18s | ~3.1s | <3s |

*LLM with short prompts. Longer prompts = longer prefill time.

**Optimizations applied:**
- Switched to /api/chat endpoint (cached system prompt)
- Added keep_alive=-1 to prevent model unloading
- Reduced silence detection from 1.0s to 0.4s
- Optimized TTS chunking (start on comma/20 chars)
- Pre-warm LLM and TTS on startup

**PHASE 1 COMPLETE** — Core voice loop functional, ~3s latency for short prompts.

### 2026-02-07 (Desktop — RTX 3070)
- Fixed LLM CPU offloading (was 85% CPU, now 100% GPU)
- Created VRAM-aware startup check in `src/main.py`
  - Queries nvidia-smi for free VRAM before loading models
  - Warns about GPU-heavy processes (Chrome, Discord, Broadcast, etc.)
  - Refuses to start if <6800 MB free (use --force to override)
- Created standalone startup script `scripts/start_jett.py` (--check mode for VRAM-only)
- Disabled Qwen3 thinking mode (`think: false`) — saves 1.5s per response
- Capped responses at 80 tokens — concise 1-2 sentence replies
- Added detailed component timing to pipeline metrics
- Final Phase 1 metrics: 3.2s perceived latency, 6.7s E2E
- **Phase 1 COMPLETE — Transitioning to Phase 2**

### 2026-02-07 (Continued)
- Implemented openWakeWord wake word detection (src/voice/wake_word.py)
- Fixed wake word: audio format was float32, needed int16
- Added --wake-debug flag for score logging, --no-wake for Phase 1 behavior
- Wake word detection working with 0.99+ confidence
- State machine: WAITING → LISTENING → PROCESSING → SPEAKING → WAITING
- Wake word paused during playback (no self-triggering)
- Full pipeline: wake word → STT → LLM → TTS → back to wake word
- **Phase 2 COMPLETE**
