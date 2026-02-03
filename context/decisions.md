# Architecture Decision Records (ADRs)

## ADR-001: Local-First Architecture

**Status**: Accepted
**Date**: 2026-02-02

**Context**: Need a voice assistant that respects privacy and achieves low latency.

**Decision**: Run STT, LLM, and TTS locally on RTX 3070. Only route complex queries to Claude API.

**Consequences**:
- Sub-500ms latency for local processing
- Limited by 8 GB VRAM — must carefully manage model sizes
- Audio never leaves the local machine
- Higher hardware requirements than cloud-only approach

---

## ADR-002: Qwen3 8B as Local LLM

**Status**: Accepted
**Date**: 2026-02-02

**Context**: Need a capable local LLM that fits within 4.5 GB VRAM budget.

**Decision**: Use Qwen3 8B with Q4_K_M quantization via Ollama.

**Alternatives Considered**:
- Llama 3.1 8B — Similar performance, Qwen3 has better instruction following
- Phi-3 — Smaller but less capable for complex queries
- Mistral 7B — Good option but Qwen3 benchmarks slightly better

**Consequences**:
- 4.5 GB VRAM usage fits budget with headroom
- Good instruction following for voice assistant use case
- Ollama provides easy model management and OpenAI-compatible API

---

## ADR-003: Portainer API Instead of Docker Socket

**Status**: Accepted
**Date**: 2026-02-02

**Context**: AI needs to manage VPS containers but direct Docker socket access is a security risk.

**Decision**: Use Portainer's REST API with token authentication instead of mounting Docker socket.

**Consequences**:
- Additional abstraction layer between AI and Docker
- Token-based auth enables fine-grained access control
- API calls can be logged, rate-limited, and filtered
- Slightly higher latency for container operations (acceptable)

---

## ADR-004: WireGuard for VPS Communication

**Status**: Accepted
**Date**: 2026-02-02

**Context**: Local machine needs secure communication with VPS services.

**Decision**: Use WireGuard VPN tunnel. All VPS services accessed only through tunnel.

**Consequences**:
- All traffic encrypted between local and VPS
- VPS firewall can block everything except WireGuard port
- Simple configuration with good performance
- Requires WireGuard setup on both ends

---

## ADR-005: Two-Machine Deployment Strategy

**Status**: Accepted
**Date**: 2026-02-02

**Context**: Need to decide where Jett runs — development and production environments.

**Options Considered**:
1. Single machine (desktop) — Dev and prod on same system
2. Single machine (laptop) — Dedicated but harder to develop
3. Two machines — Desktop for dev, laptop for prod
4. Cloud VM — Pay for GPU compute

**Decision**: Two-machine strategy (desktop dev → laptop prod)

**Rationale**:
- Development needs monitor/keyboard and debugging tools
- Main PC should stay clean for gaming/work
- Legion laptop becomes dedicated appliance (infrastructure mindset)
- Both have identical 8GB VRAM — code transfers directly
- Mirrors real infrastructure engineering practices

**Consequences**:
- Pro: Clean separation of concerns
- Pro: Main PC unaffected by 24/7 assistant
- Pro: Real deployment experience for portfolio
- Con: Need to maintain two environments
- Con: Laptop has ~15% slower inference (imperceptible)

**Interview Framing**:
> "I separated development and production environments — desktop for building where debugging is easy, then deploy to a dedicated laptop running Ubuntu Server as a headless appliance. This mirrors how real infrastructure teams operate: you don't develop on production hardware."

---

## ADR-006: faster-whisper for STT

**Status**: Accepted
**Date**: 2026-02-02

**Context**: Need fast, accurate speech-to-text that runs on GPU.

**Decision**: Use faster-whisper with distil-large-v3 model, INT8 quantization.

**Consequences**:
- 1.5 GB VRAM — fits budget
- CTranslate2 backend for optimized inference
- Good accuracy for English
- INT8 quantization reduces VRAM with minimal quality loss
