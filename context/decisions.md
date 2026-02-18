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

---

## ADR-007: Explicit Allowlists Over Blocklists

**Status**: Accepted
**Date**: 2026-02-04

**Context**: Security wrapper needs to control which container operations the AI can perform.

**Options Considered**:
1. Blocklist (deny dangerous operations) — enumerate known-bad actions
2. Allowlist (permit safe operations only) — enumerate known-good actions

**Decision**: Use frozenset allowlists. Only explicitly permitted operations are allowed; everything else is denied by default.

**Rationale**:
- Allowlist = default deny. Can't forget to block something.
- Blocklist = default allow. One missed entry and the system is vulnerable.
- frozenset makes the allowlist immutable at runtime — no dynamic modification.

**Consequences**:
- Pro: Zero risk of forgetting to block a new dangerous operation
- Pro: Immutable at runtime — can't be modified by prompt injection
- Con: Less flexible — adding new operations requires code change
- Trade-off: Security > convenience

**Interview Framing**:
> "With blocklists you're playing whack-a-mole trying to anticipate every attack. With allowlists, if I didn't explicitly permit it, it's denied. The allowlist is a frozenset — immutable at runtime — so even if the AI is prompt-injected, it can't modify its own permissions."

---

## ADR-008: VPS Services WireGuard-Only Binding

**Status**: Accepted
**Date**: 2026-02-04

**Context**: VPS services (n8n, PostgreSQL, Qdrant, Portainer) need to be accessible from the local machine but not from the public internet.

**Options Considered**:
1. Public IP + UFW firewall — services on 0.0.0.0, firewall restricts access
2. Cloudflare Tunnel — route through Cloudflare's network
3. WireGuard-only binding — bind services to 10.0.0.2 (tunnel IP)

**Decision**: Bind all Docker services to `10.0.0.2` (WireGuard interface IP). No service listens on the public interface.

**Rationale**:
- Zero attack surface on the public internet — services are unreachable without the tunnel
- Defense-in-depth: even if UFW is misconfigured, services aren't listening publicly
- Simpler than Cloudflare Tunnel, no third-party dependency

**Consequences**:
- Pro: Nothing exposed on public interface, even with firewall misconfiguration
- Pro: No third-party dependency (Cloudflare)
- Con: Requires WireGuard setup on both local machine and VPS
- Con: If WireGuard tunnel drops, all services are unreachable

**Interview Framing**:
> "Nothing is exposed on the public interface. You'd have to compromise the WireGuard tunnel first, which requires the private key. Even if someone misconfigures the firewall, the services simply aren't listening on the public IP."

---

## ADR-009: Disable LLM Thinking Mode for Voice

**Status**: Accepted
**Date**: 2026-02-07

**Context**: Qwen3's chain-of-thought thinking mode adds ~1.5s and ~80 tokens of overhead per response. Voice assistant queries are predominantly simple commands.

**Options Considered**:
1. Keep thinking enabled — better reasoning, slower responses
2. Disable thinking — faster responses, slightly less reasoning depth
3. Conditional — think for complex queries only

**Decision**: Disable thinking mode (`think: false`) for all voice interactions.

**Rationale**:
- Voice assistants need speed over depth — 1.5s is significant when total perceived latency is 3.2s
- Most voice queries are simple commands where thinking provides no benefit
- Complex queries route to Claude via hybrid routing anyway
- Reduces wasted tokens (80 think tokens = ~1s generation time at 68 tok/s)

**Consequences**:
- Pro: 1.5s faster response time (4s → 2.15s first token)
- Pro: 80 fewer tokens per response — less GPU compute, lower power
- Con: May give worse answers on complex reasoning questions
- Mitigated: Complex queries route to Claude API via the hybrid router

**Interview Framing**:
> "I disabled the model's chain-of-thought for voice interactions because latency matters more than reasoning depth for simple commands. Complex queries route to Claude via hybrid routing, so local inference optimizes for speed."

---

## ADR-010: Keyword Heuristic Router Over ML Classifier

**Status**: Accepted
**Date**: 2026-02-18

**Context**: The hybrid router needs to decide whether a voice query should go to local Qwen3 (fast, limited reasoning) or cloud Claude (slower, better reasoning). Need a classification method.

**Options Considered**:
1. ML classifier (fine-tuned BERT/DistilBERT) — learned decision boundary
2. Embedding similarity (sentence-transformers) — compare against exemplar clusters
3. Keyword heuristic — regex pattern matching on known signals
4. LLM self-routing — ask the local LLM to classify itself

**Decision**: Keyword heuristic classifier with regex patterns.

**Rationale**:
- <1ms latency — adds zero perceptible delay to the pipeline
- Zero VRAM — runs on CPU, no model to load
- Transparent — decisions are explainable (matched pattern X)
- Good enough — voice queries have strong lexical signals ("explain X" vs "what time is it")
- Iteratable — easy to add/remove patterns based on observed misroutes

**Consequences**:
- Pro: Zero overhead, zero VRAM, instant decisions
- Pro: Fully explainable — debug mode shows which patterns matched
- Pro: Graceful fallback — if cloud is unavailable, everything routes local
- Con: Won't catch subtle complexity (e.g., a short but deep question)
- Con: Requires manual tuning of patterns
- Mitigated: v2 can use embedding similarity if keyword approach proves insufficient

**Interview Framing**:
> "I started with keyword heuristics for routing — regex patterns that detect complexity signals like 'explain', 'compare', 'write'. It adds <1ms latency and zero VRAM. The key insight is that voice queries have strong lexical signals — people say 'what time is it', not ambiguous prompts. If the heuristic proves insufficient, I can upgrade to embedding-based classification without changing the router interface."

---

## ADR-011: Claude Sonnet as Default Cloud Backend

**Status**: Accepted
**Date**: 2026-02-18

**Context**: Need to choose which Claude model to use for cloud-routed queries.

**Options Considered**:
1. Claude Opus — most capable, highest cost, slowest
2. Claude Sonnet — strong capability, moderate cost, fast
3. Claude Haiku — fastest, cheapest, less capable

**Decision**: Default to Claude Sonnet 4.5, configurable via `--cloud-model` flag.

**Rationale**:
- Best balance of capability and latency for voice use case
- Complex queries that route to cloud need good reasoning (rules out Haiku)
- Voice needs reasonable latency — Opus is overkill for most routed queries
- Configurable: power users can override to Opus for maximum quality or Haiku for cost savings

**Consequences**:
- Pro: Good reasoning for complex queries that local LLM can't handle
- Pro: Fast enough for voice (~1-2s first token)
- Pro: User can override via CLI flag
- Con: Higher cost than Haiku (~$3 vs $0.25 per million input tokens)
- Mitigated: Most queries still route local — cloud is the exception, not the rule

---

## ADR-012: Silero VAD Over RMS Energy Detection

**Status**: Accepted
**Date**: 2026-02-18

**Context**: The pipeline uses RMS energy thresholds to detect when a user stops speaking. This is unreliable — quiet speech gets cut off early, and loud background noise keeps recording going. Need a more robust end-of-speech detector.

**Options Considered**:
1. RMS energy threshold (current) — simple, no dependencies, unreliable
2. Silero VAD — neural speech classifier, returns probability per chunk
3. WebRTC VAD — C-based, fast, but less accurate than neural approaches
4. openWakeWord's built-in VAD — already in the project but tied to wake word lifecycle

**Decision**: Replace RMS with Silero VAD as the default silence detection method. Keep RMS as a `--no-vad` fallback.

**Rationale**:
- Neural classifier distinguishes speech from noise regardless of volume
- Runs on CPU with zero VRAM impact — critical for the 8GB VRAM budget
- ~2MB model loaded via `torch.hub.load` (PyTorch already installed)
- No new pip dependency — Silero downloads and caches via torch.hub
- Same `record_audio()` interface — returns Optional[np.ndarray]

**Consequences**:
- Pro: Reliable silence detection regardless of background noise or speech volume
- Pro: Zero VRAM — CPU-only inference
- Pro: No new pip dependency (uses existing PyTorch)
- Pro: RMS fallback preserved via --no-vad
- Con: Requires internet on first run to download model (~2MB, cached after)
- Con: Slightly higher CPU usage than RMS (negligible on modern hardware)

**Interview Framing**:
> "I replaced simple volume thresholds with Silero VAD — a neural speech classifier that returns a probability score per audio chunk. Volume-based detection cuts off quiet speech and gets confused by background noise. The neural model classifies actual speech patterns, runs on CPU with zero VRAM impact, and loads via PyTorch's hub system — no new dependency."
