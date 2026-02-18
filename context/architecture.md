# Architecture

## System Overview

Jett is a local-first voice assistant with hybrid cloud routing. The system is split between a local machine (RTX 3070 GPU) and a VPS (Hostinger).

```
LOCAL (RTX 3070)                         VPS (Hostinger)
┌─────────────────────────┐              ┌─────────────────────────┐
│  Mic → openWakeWord     │              │  n8n (automation)       │
│       → Silero VAD      │              │  PostgreSQL (state)     │
│       → faster-whisper   │              │  Qdrant (vectors)       │
│       → LLM Router      │◄─WireGuard──►│  Portainer (mgmt API)   │
│       → Kokoro TTS      │              │                         │
│       → Speaker          │              │  UFW firewall           │
│                          │              └─────────────────────────┘
│  Dashboard (Next.js)     │
└─────────────────────────┘
```

## Deployment Strategy

### Two-Machine Model

| Environment | Machine | GPU | Purpose |
|-------------|---------|-----|---------|
| **Development** | Main Desktop PC | RTX 3070 (8GB) | Build, test, debug with monitor/keyboard |
| **Production** | Lenovo Legion Y740-17 | RTX 2070 Max-Q (8GB) | 24/7 headless appliance |

### Why This Split

1. **Easier development** — Monitor and keyboard attached, full debugging tools
2. **Main PC stays clean** — No background VRAM usage when gaming/working
3. **Dedicated infrastructure** — Legion becomes a single-purpose appliance
4. **Real-world experience** — Mirrors production infrastructure engineering

### Production Machine Specs

- **Model:** Lenovo Legion Y740-17 Laptop
- **GPU:** RTX 2070 Max-Q (8GB VRAM)
- **RAM:** 16GB (upgrade to 32GB planned before deployment)
- **OS:** Ubuntu Server 24.04 LTS (fresh install when ready)
- **Network:** Ethernet to router, WireGuard tunnel to VPS

### Performance Comparison

| Metric | RTX 3070 (Dev) | RTX 2070 Max-Q (Prod) |
|--------|----------------|----------------------|
| LLM tokens/sec | 60-70 | 45-55 |
| VRAM | 8GB | 8GB |
| User perception | Instant | Instant (imperceptible difference) |

### VRAM Budget (Identical on Both)

| Component | VRAM |
|-----------|------|
| faster-whisper distil-large-v3 INT8 | 1.5 GB |
| Qwen3 8B Q4_K_M | 4.5 GB |
| Kokoro-82M TTS | 0.2 GB |
| **Total** | **6.2 GB** |
| **Headroom** | **1.8 GB** |

## Component Map

### Voice Pipeline (Local)
| Component | Technology | Runs On | VRAM |
|---|---|---|---|
| Wake Word | openWakeWord | CPU | 0 |
| VAD | Silero VAD | CPU | 0 |
| STT | faster-whisper (distil-large-v3, INT8) | GPU | 1.5 GB |
| TTS | Kokoro-82M | GPU | 0.2 GB |

### LLM Layer (Local + Cloud)
| Component | Technology | Runs On | VRAM | Status |
|---|---|---|---|---|
| Local LLM | Qwen3 8B (Q4_K_M) via Ollama | GPU | 5.28 GB | ✅ |
| Cloud LLM | Claude Sonnet via Anthropic SDK | Remote | 0 | ✅ |
| Router | QueryRouter — keyword heuristic classifier | CPU | 0 | ✅ |

**Router Modes:**
- `local` — All queries to Ollama (default, backward compatible)
- `cloud` — All queries to Claude API
- `hybrid` — Classify and route: simple → local, complex → cloud

### VPS Services (Remote)
| Service | Port | Purpose |
|---|---|---|
| WireGuard | 51820/UDP | VPN tunnel |
| n8n | 5678 | Workflow automation |
| PostgreSQL | 5432 | State + audit logs |
| Qdrant | 6333 | Vector search / RAG |
| Portainer | 9443 | Container management API |

### Dashboard (Local)
| Component | Technology | Port |
|---|---|---|
| Web UI | Next.js + Tailwind | 3000 |
| WebSocket | Real-time updates | 3001 |

## Data Flow

1. **Audio input** → Microphone captures audio
2. **Wake word** → openWakeWord detects "Hey Jett" (CPU)
3. **VAD** → Silero detects speech boundaries (CPU)
4. **STT** → faster-whisper transcribes audio (GPU, 1.5 GB)
5. **Router** → QueryRouter classifies query complexity via keyword heuristics (CPU, <1ms)
6. **LLM** → Local (Qwen3 via Ollama) or cloud (Claude via Anthropic SDK) generates streaming response
7. **TTS** → Kokoro synthesizes speech (GPU, 0.2 GB)
8. **Audio output** → Speaker plays response

## Communication Protocols

- **Voice pipeline**: Python asyncio, inter-process via IPC
- **Dashboard ↔ Backend**: WebSocket for real-time, REST for config
- **Local ↔ VPS**: WireGuard tunnel, HTTPS over tunnel
- **LLM**: Ollama OpenAI-compatible API (local), Anthropic SDK (cloud)
