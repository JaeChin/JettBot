# Jett Phase 2 Handoff — Wake Word Complete

> Created: 2025-02-08
> For: Continuing to custom wake word training and Phase 3

---

## Current State: Phase 2 COMPLETE

Jett is a working voice assistant with wake word detection.

### What Works
- **Wake word:** "Hey Jarvis" triggers with 0.99+ confidence
- **Voice pipeline:** STT (faster-whisper) → LLM (Qwen3 8B) → TTS (Kokoro)
- **State machine:** WAITING → LISTENING → PROCESSING → SPEAKING → WAITING
- **Security wrapper:** 30/30 tests, explicit allowlists, audit logging
- **VPS config:** docker-compose.yml ready (hardened, WireGuard-bound)

### Performance Metrics
| Metric | Value |
|--------|-------|
| Wake word confidence | 0.99+ |
| STT latency | 650-1500ms |
| LLM first token | ~2.2s |
| User-perceived latency | ~3s |
| E2E with playback | 6-9s |
| VRAM usage | 7.38 GB / 8 GB |

### Key Files
- `src/voice/wake_word.py` — WakeWordDetector class (int16 audio fix applied)
- `src/voice/pipeline.py` — VoicePipeline with WAITING state
- `src/voice/stt.py` — faster-whisper integration
- `src/voice/tts.py` — Kokoro-82M integration
- `src/security/wrapper.py` — ContainerController with allowlists
- `models/Modelfile.jett-qwen3` — Custom Ollama model (no thinking, concise)
- `docker/docker-compose.yml` — VPS services (n8n, postgres, qdrant, portainer)

### Critical Discoveries
1. **VRAM contention:** Ollama loads model with whatever VRAM is free at load time. Must ensure clean VRAM before starting, or model runs 85% CPU (10x slower).
2. **Audio format:** openWakeWord expects int16 [-32768, 32767], not float32 [-1, 1]. Fixed in wake_word.py.
3. **Thinking mode:** Disabled (`think: false`) saves 1.5s per response.
4. **Token cap:** `num_predict: 80` keeps responses concise for voice.

---

## Next Steps

### Immediate: Custom Wake Word "Hey Jett"
1. Generate synthetic training audio using Kokoro TTS
2. Train via openWakeWord Colab notebook (~1 hour)
3. Export ONNX model (<5MB)
4. Swap into WakeWordDetector

### Then: Phase 3 — Hybrid Routing
1. Install RouteLLM
2. Configure Claude API fallback
3. Implement query complexity classification
4. Add semantic caching (Qdrant)
5. Cost tracking dashboard

### Then: Phase 4-6
- VPS deployment (WireGuard, docker-compose up)
- Dashboard (Next.js, already scaffolded)
- Security hardening review

---

## Commands Reference
```bash
# Run Jett (with wake word)
python -m src.main --force

# Run without wake word (always listening)
python -m src.main --no-wake --force

# Debug wake word scores
python -m src.main --wake-debug --force

# Test wake word standalone
python src/voice/wake_word.py

# Run security tests
pytest tests/test_security.py -v

# Check VRAM
nvidia-smi

# Verify Ollama model is 100% GPU
ollama ps
```

---

## Architecture
```
[Always Running - CPU]
Wake Word (openWakeWord, "hey_jarvis")
        | triggered
[GPU Pipeline]
LISTENING -> STT (1.08GB) -> LLM (5.28GB) -> TTS (0.36GB) -> SPEAKING
        | complete
[Back to CPU]
Wake Word (waiting)
```

---

## Interview Talking Points

1. **Wake word:** "I fixed an audio format bug — openWakeWord expects int16 but sounddevice outputs float32. The model was seeing near-zero values and treating all audio as silence."

2. **VRAM management:** "Ollama loads models into whatever VRAM is available at startup. If background apps use GPU memory, the model splits across CPU/GPU and runs 10x slower. I added a startup check that warns about GPU-heavy processes."

3. **Latency optimization:** "I disabled the model's chain-of-thought reasoning for voice because speed matters more than depth for simple commands. Complex queries route to Claude anyway."

---

## Project Structure
```
jett/
├── src/
│   ├── voice/
│   │   ├── wake_word.py    # openWakeWord detector
│   │   ├── pipeline.py     # Main voice loop
│   │   ├── stt.py          # faster-whisper
│   │   └── tts.py          # Kokoro-82M
│   ├── security/
│   │   ├── wrapper.py      # ContainerController
│   │   ├── allowlist.py    # Explicit allowlists
│   │   ├── audit.py        # Immutable audit log
│   │   └── exceptions.py   # Security exceptions
│   └── main.py             # Entry point (VRAM check, CLI args)
├── models/
│   └── Modelfile.jett-qwen3  # Custom Ollama model
├── docker/
│   └── docker-compose.yml  # VPS services (n8n, postgres, qdrant)
├── dashboard/              # Next.js 14 + shadcn/ui (scaffolded)
├── benchmarks/
│   ├── e2e_benchmark.py
│   ├── llm_benchmark.py
│   ├── tts_benchmark.py
│   ├── vram_validation.py
│   └── wake_word_benchmark.py
├── tests/
│   └── test_security.py    # 30 tests
├── context/                # Architecture docs, decisions, state
├── scripts/
│   └── start_jett.py       # Standalone launcher with VRAM check
└── requirements.txt
```

---

## VRAM Budget (Actual Measured)
| Component | VRAM |
|-----------|------|
| System/CUDA overhead | 0.66 GB |
| Qwen3 8B Q4_K_M (ctx=2048) | 5.28 GB |
| faster-whisper distil-large-v3 INT8 | 1.08 GB |
| Kokoro-82M | 0.36 GB |
| **Total** | **7.38 GB** |
| Headroom | 0.81 GB |
| RTX 3070 capacity | 8.19 GB |
