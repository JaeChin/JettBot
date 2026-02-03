# Jett Voice Pipeline

Activate Voice Pipeline Agent for STT, TTS, and wake word work.

## Agent Identity

You are working on **Jett's voice subsystem** — the ears and mouth of the assistant.

Your goal: **Sub-500ms latency from voice input to first audio output.**

## Architecture Reference

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Microphone  │───▶│ Wake Word   │───▶│    VAD      │
│   Input     │    │(openWakeWord)│   │  (Silero)   │
└─────────────┘    └─────────────┘    └─────────────┘
                                             │
                                             ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Speaker   │◀───│    TTS      │◀───│    STT      │
│   Output    │    │ (Kokoro-82M)│    │(faster-whisper)
└─────────────┘    └─────────────┘    └─────────────┘
```

## Component Specifications

### STT: faster-whisper
- **Model:** `distil-large-v3` (INT8 quantization)
- **VRAM:** ~1.5 GB
- **Target:** 35x real-time transcription
- **Config:**
```python
from faster_whisper import WhisperModel

model = WhisperModel(
    "distil-large-v3",
    device="cuda",
    compute_type="int8"
)

segments, _ = model.transcribe(
    audio,
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 500}
)
```

### TTS: Kokoro-82M
- **VRAM:** ~160 MB
- **Latency:** <300ms regardless of text length
- **License:** Apache 2.0 (commercial OK)
- **Alternative:** Chatterbox for voice cloning (MIT, 2-4GB VRAM)

### Wake Word: openWakeWord
- **Training:** Synthetic speech via TTS → Colab notebook → ONNX export
- **Size:** <5 MB model file
- **CPU-only:** Negligible resource impact
- **License:** MIT

### VAD: Silero
- **Integration:** Built into faster-whisper with `vad_filter=True`
- **Purpose:** Detect speech boundaries, avoid processing silence

## Implementation Checklist

### Phase 1: STT
- [ ] Install faster-whisper: `pip install faster-whisper`
- [ ] Download distil-large-v3 model
- [ ] Test transcription accuracy
- [ ] Measure VRAM usage with `nvidia-smi`
- [ ] Benchmark: record 10s audio, measure transcription time

### Phase 2: TTS
- [ ] Install Kokoro-82M
- [ ] Test synthesis quality
- [ ] Implement streaming (sentence-level splitting)
- [ ] Measure time-to-first-audio

### Phase 3: Wake Word
- [ ] Set up openWakeWord
- [ ] Generate synthetic training data for "Jett"
- [ ] Train via Colab notebook
- [ ] Export ONNX model
- [ ] Integrate with always-listening daemon

### Phase 4: Integration
- [ ] Wire: wake word → VAD → STT → [LLM] → TTS → speaker
- [ ] Measure end-to-end latency
- [ ] Handle errors gracefully (mic disconnect, etc.)

## Latency Targets

| Stage | Target | Measurement |
|-------|--------|-------------|
| Wake word detection | <50ms | - |
| VAD + STT | <200ms | - |
| LLM inference | <300ms | - |
| TTS (first audio) | <300ms | - |
| **Total E2E** | **<500ms** | - |

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| High STT latency | Full-precision model | Use INT8 quantization |
| TTS stuttering | Waiting for full response | Stream sentence-by-sentence |
| False wake triggers | Undertrained model | More diverse training data |
| Whisper processing silence | No VAD | Enable `vad_filter=True` |

## Security Notes

- Audio is processed **locally only** — no cloud transcription
- No persistent audio storage (privacy-first)
- Wake word model runs in isolated process

## Next Step

After voice pipeline works: `/jett-llm` to integrate the language model
