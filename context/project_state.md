# Project State

## Current Phase: Phase 1 — Voice Pipeline

### Status: In Progress

## What's Done
- [x] Project directory structure created
- [x] Context files initialized
- [x] Architecture documented
- [x] Security model defined
- [x] VRAM budget calculated
- [x] Python environment setup (venv + requirements.txt)
- [x] STT module scaffolded (faster-whisper integration)

## What's Next
- [ ] **Phase 1**: Voice pipeline (wake word → VAD → STT → TTS) ← **IN PROGRESS**
- [ ] **Phase 2**: Local LLM integration (Ollama + Qwen3 8B)
- [ ] **Phase 3**: Hybrid routing (local ↔ Claude)
- [ ] **Phase 4**: VPS infrastructure (WireGuard, Docker, n8n, PostgreSQL, Qdrant)
- [ ] **Phase 5**: Security hardening (allowlist, rate limiting, audit logging)
- [ ] **Phase 6**: Dashboard (Next.js control interface)
- [ ] **Phase 7**: Integration testing and latency optimization

## Blockers
- None currently

## Notes
- Target hardware: RTX 3070 (8 GB VRAM)
- All models must fit within VRAM budget (see `vram_budget.md`)
- Privacy-first: audio never leaves local machine
