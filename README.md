# Jett Voice Assistant

A local-first AI voice assistant built on RTX 3070 hardware with hybrid cloud routing.

## Features

- **Sub-500ms latency** — Local STT, LLM, and TTS processing
- **Hybrid routing** — Simple queries local, complex queries to Claude
- **Privacy-first** — Audio never leaves your machine
- **Secure container control** — Defense-in-depth for AI-controlled infrastructure

## Architecture

```
LOCAL (RTX 3070)                    VPS (Hostinger)
├── Wake Word (openWakeWord)        ├── n8n (automation)
├── VAD (Silero)                    ├── PostgreSQL (state)
├── STT (faster-whisper)            ├── Qdrant (vectors)
├── LLM (Ollama/Qwen3)             └── Portainer (management)
├── TTS (Kokoro-82M)
└── Dashboard (Next.js)
        │
        └──── WireGuard Tunnel ────────┘
```

## VRAM Budget (8GB RTX 3070)

| Component | Allocation |
|---|---|
| faster-whisper (distil-large-v3, INT8) | 1.5 GB |
| Qwen3 8B (Q4_K_M) | 4.5 GB |
| Kokoro-82M TTS | 0.2 GB |
| **Total** | **6.2 GB** |
| Headroom | 1.8 GB |

## Security Highlights

- Never expose Docker socket to AI
- Explicit allowlist for container operations
- Rate limiting on privileged actions
- Immutable audit logging
- WireGuard encryption for VPS communication

## Setup

See `docs/research.md` for detailed implementation guide.

## License

MIT
