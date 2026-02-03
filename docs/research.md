# Research & Implementation Notes

## Voice Pipeline Research

### openWakeWord
- GitHub: https://github.com/dscripka/openWakeWord
- Custom wake word training possible
- Low resource usage, runs on CPU
- Pre-trained models available, custom "Hey Jett" needs training data

### Silero VAD
- GitHub: https://github.com/snakers4/silero-vad
- PyTorch-based, runs on CPU
- Detects speech start/end with high accuracy
- Configurable silence threshold

### faster-whisper
- GitHub: https://github.com/SYSTRAN/faster-whisper
- CTranslate2 backend — 4x faster than original Whisper
- distil-large-v3 with INT8: ~1.5 GB VRAM
- Supports streaming transcription

### Kokoro TTS
- 82M parameter model, very lightweight
- Natural-sounding voice output
- ~0.2 GB VRAM
- Supports streaming synthesis

## LLM Research

### Ollama
- Model serving with OpenAI-compatible API
- Easy model management (pull, run, quantize)
- Supports concurrent requests
- Endpoint: `http://localhost:11434/v1/chat/completions`

### Qwen3 8B
- Strong instruction following
- Q4_K_M quantization: ~4.5 GB VRAM
- Good performance on reasoning benchmarks
- `ollama pull qwen3:8b-q4_K_M`

## VPS Research

### Hostinger VPS
- Ubuntu 22.04+
- Docker + Docker Compose pre-installed or easy to install
- Sufficient for n8n + PostgreSQL + Qdrant + Portainer

### WireGuard Setup
- VPS: `apt install wireguard`
- Generate keys: `wg genkey | tee privatekey | wg pubkey > publickey`
- Configure tunnel on both ends
- Test with `ping 10.0.0.1` from local

### Docker Compose Stack
```yaml
version: "3.8"
services:
  n8n:
    image: n8nio/n8n
    restart: unless-stopped
    ports:
      - "127.0.0.1:5678:5678"
    volumes:
      - n8n_data:/home/node/.n8n

  postgres:
    image: postgres:16
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant
    restart: unless-stopped
    ports:
      - "127.0.0.1:6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  portainer:
    image: portainer/portainer-ce
    restart: unless-stopped
    ports:
      - "127.0.0.1:9443:9443"
    volumes:
      - portainer_data:/data

volumes:
  n8n_data:
  postgres_data:
  qdrant_data:
  portainer_data:
```

## Latency Budget

| Stage | Target | Notes |
|---|---|---|
| Wake word detection | ~50ms | CPU, very fast |
| VAD (speech end detection) | ~500ms silence | Configurable threshold |
| STT (transcription) | < 200ms | GPU, depends on utterance length |
| LLM (local, first token) | < 300ms | GPU, Ollama streaming |
| TTS (first audio) | < 100ms | GPU, streaming synthesis |
| **Total (excl. VAD wait)** | **< 500ms** | 
