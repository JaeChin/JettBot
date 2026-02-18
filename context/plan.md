# Hybrid Routing Implementation Plan

## Overview

Add intelligent routing that sends simple queries to local Qwen3 8B and complex queries to Claude API. The router is a lightweight complexity classifier that runs on CPU before LLM inference.

## Architecture

```
STT transcription
       ↓
  [Router] ──── simple ──→ Ollama/Qwen3 (local, ~500ms first token)
       │
       └─── complex ──→ Claude API (cloud, ~1-2s first token)
       │
       └─── fallback ──→ Ollama/Qwen3 (if cloud unavailable)
       ↓
  Generator[str] (same interface either way)
       ↓
  speak_streaming() (unchanged)
```

**Key constraint:** Both backends MUST return `Generator[str, None, None]` to preserve the existing `speak_streaming()` optimization that starts TTS during generation.

## Files to Create/Modify

### New Files
1. `src/llm/__init__.py` — Package init
2. `src/llm/router.py` — Complexity classifier + routing dispatch
3. `src/llm/cloud.py` — Claude API streaming wrapper
4. `.env.example` — Document ANTHROPIC_API_KEY variable

### Modified Files
5. `src/voice/pipeline.py` — Extract Ollama code, integrate router
6. `src/main.py` — Add CLI args (--router-mode, --cloud-model)
7. `requirements.txt` — Add `anthropic` SDK

## Implementation Steps

### Step 1: Create the complexity classifier (`src/llm/router.py`)

Keyword + heuristic based classifier. No ML model needed — keeps it simple and fast (<1ms).

**Routing logic:**
- **LOCAL** (simple): short queries, commands, greetings, factual lookups
  - Keywords: time, weather, timer, remind, play, stop, volume, what is, who is
  - Characteristics: < 15 words, imperative mood, single-intent
- **CLOUD** (complex): reasoning, multi-step, creative, analysis
  - Keywords: why, explain, compare, analyze, write, create, help me, what if, how would
  - Characteristics: > 30 words, multiple clauses, abstract concepts
- **FALLBACK**: If cloud is unavailable or API key missing, always route local

```python
class QueryRouter:
    def classify(self, text: str) -> str:  # Returns "local" or "cloud"
    def route(self, text: str) -> Generator[str, None, None]:
```

### Step 2: Create Claude API streaming wrapper (`src/llm/cloud.py`)

Thin wrapper around the Anthropic Python SDK with streaming support.

```python
class CloudLLM:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
    def stream(self, prompt: str, system: str = None) -> Generator[str, None, None]:
```

- Uses `anthropic` SDK with `client.messages.stream()`
- Yields tokens one at a time (same interface as Ollama streaming)
- Handles network errors gracefully → returns error message as text
- Default model: Claude Sonnet (fast + capable, cost-effective)

### Step 3: Refactor pipeline.py

Extract Ollama streaming into a method, add router dispatch:

- Extract existing Ollama code into `_stream_local(prompt)`
- Add `_stream_cloud(prompt)` that calls CloudLLM
- Replace `generate_response()` body with router dispatch
- Add `llm_backend` field to PipelineMetrics

### Step 4: Update main.py with CLI args

```
--router-mode {local,cloud,hybrid}  (default: local — backward compatible)
--cloud-model TEXT                   (default: claude-sonnet-4-5-20250929)
```

API key loaded from `ANTHROPIC_API_KEY` env var (not a CLI arg — security).

### Step 5: Update context files

- Update `project_state.md` — mark hybrid routing complete
- Update `architecture.md` — add router to component map
- Add `ADR-010` to `decisions.md` — routing strategy rationale
- Update `vram_budget.md` — router adds 0 VRAM (CPU-only keyword matching)

## What This Does NOT Include

- Conversation history / multi-turn — current pipeline is single-turn, keeping it that way
- Semantic embeddings for classification — overkill, keyword heuristics are fine for v1
- Cost tracking / usage dashboard — future enhancement
- Automatic threshold tuning — manual for now, can iterate

## Testing Plan

- Unit test the classifier with sample queries (simple vs complex)
- Integration test: local-only mode still works identically
- Integration test: cloud mode streams correctly
- Integration test: hybrid mode routes as expected
- Fallback test: cloud unavailable → graceful local fallback
