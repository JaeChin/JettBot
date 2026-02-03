# Jett LLM & Routing

Activate LLM Agent for local inference and hybrid routing work.

## Agent Identity

You are working on **Jett's brain** — the reasoning core of the assistant.

Your goal: **Fast local inference for simple queries, smart routing to cloud for complex ones.**

## Architecture Reference

```
                    ┌─────────────────────┐
                    │   Query Classifier  │
                    │     (RouteLLM)      │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌──────────┐     ┌──────────┐     ┌──────────┐
       │  Cache   │     │  Local   │     │  Cloud   │
       │   Hit    │     │ (Qwen3)  │     │ (Claude) │
       └──────────┘     └──────────┘     └──────────┘
              │                │                │
              └────────────────┼────────────────┘
                               ▼
                    ┌─────────────────────┐
                    │   Response + Log    │
                    └─────────────────────┘
```

## Component Specifications

### Local LLM: Qwen3 8B
- **Quantization:** Q4_K_M (GGUF)
- **VRAM:** ~4.5 GB (including 8K context KV cache)
- **Speed:** 60-70 tokens/second on RTX 3070
- **Tool-calling F1:** 0.933 (best among open models)
- **Deployment:** Ollama

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull qwen3:8b

# Test
ollama run qwen3:8b "What time is it in Tokyo?"
```

### Hybrid Router: RouteLLM
- **Purpose:** Classify query complexity
- **Local threshold:** Simple commands, device control, basic Q&A
- **Cloud threshold:** Complex reasoning, multi-step tasks

```python
from routellm.controller import Controller

client = Controller(
    routers=["mf"],  # Matrix factorization router
    strong_model="claude-3-5-sonnet",
    weak_model="ollama/qwen3:8b"
)

response = client.chat.completions.create(
    model="router-mf-0.11593",  # Threshold controls routing
    messages=[{"role": "user", "content": query}]
)
```

### Semantic Cache
- **Purpose:** Avoid redundant API calls for similar queries
- **Threshold:** Cosine similarity > 0.85
- **Expected hit rate:** 70-90% for voice assistant patterns
- **Storage:** PostgreSQL with pgvector, or Qdrant

## Implementation Checklist

### Phase 1: Local LLM
- [ ] Install Ollama
- [ ] Pull Qwen3 8B model
- [ ] Test basic inference
- [ ] Measure VRAM usage
- [ ] Benchmark: tokens/second

### Phase 2: Tool Calling
- [ ] Define tool schema (device control, timers, etc.)
- [ ] Test tool invocation accuracy
- [ ] Handle tool errors gracefully

### Phase 3: Hybrid Routing
- [ ] Install RouteLLM
- [ ] Configure Claude API fallback
- [ ] Set routing threshold
- [ ] Test with query complexity examples

### Phase 4: Semantic Caching
- [ ] Set up vector storage (Qdrant or pgvector)
- [ ] Implement query embedding
- [ ] Cache hit/miss logging
- [ ] Cost savings tracking

## Cost Estimates

| Scenario | Monthly Cost |
|----------|-------------|
| Cloud-only (200 queries/day) | $75-150 |
| Hybrid (50% local) | $15-30 |
| Hybrid + caching (70% hit rate) | $5-15 |

## Routing Decision Examples

| Query | Route | Reason |
|-------|-------|--------|
| "What time is it?" | Local | Simple, factual |
| "Turn off the lights" | Local | Device control |
| "Set a timer for 5 minutes" | Local | Basic command |
| "Explain quantum computing" | Cloud | Complex reasoning |
| "Help me debug this code" | Cloud | Multi-step analysis |
| "What's the weather?" | Local + API | Simple + external data |

## VRAM Validation

After setting up LLM, verify total usage:

```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

| Component | Expected | Actual |
|-----------|----------|--------|
| faster-whisper | 1.5 GB | - |
| Qwen3 8B | 4.5 GB | - |
| Kokoro-82M | 0.2 GB | - |
| **Total** | **6.2 GB** | - |
| **Headroom** | **1.8 GB** | - |

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| Slow inference | Wrong quantization | Use Q4_K_M specifically |
| High VRAM | Context too long | Reduce max_tokens or context |
| Poor tool calling | Wrong model | Qwen3 has best tool F1 |
| Routing too aggressive | Threshold too low | Increase router threshold |

## Security Notes

- API keys stored in `.env` (gitignored)
- Rate limiting on cloud API calls
- Cost caps to prevent runaway spending
- Query logging for audit (sanitize PII)

## Interview Framing

> "I chose hybrid routing because purely local has quality constraints for complex queries while purely cloud has privacy and cost concerns. The router scores query complexity to achieve 70% local processing while maintaining response quality — achieving 94% accuracy at 60% less cost."

## Next Step

After LLM integration works: `/jett-security` to implement container controls
