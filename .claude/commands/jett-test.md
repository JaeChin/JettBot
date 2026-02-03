# Jett Testing & Benchmarking

Activate Test Agent for integration testing and performance validation.

## Agent Identity

You are working on **Jett's quality assurance** — proving the system works and performs well.

Your goal: **Measurable benchmarks, reproducible tests, interview-ready metrics.**

## Test Categories

### 1. Unit Tests
Individual component verification

### 2. Integration Tests
Component interaction verification

### 3. Latency Benchmarks
Performance against targets

### 4. Security Boundary Tests
Permission system verification

### 5. VRAM Validation
GPU memory tracking

---

## Latency Benchmark Suite

### Target: <500ms End-to-End

```python
# benchmarks/latency.py
import time
import statistics
from typing import List, Dict

class LatencyBenchmark:
    def __init__(self):
        self.results: Dict[str, List[float]] = {
            "wake_word": [],
            "vad": [],
            "stt": [],
            "llm": [],
            "tts": [],
            "e2e": []
        }
    
    def measure(self, stage: str, func, *args, **kwargs):
        """Measure execution time of a function"""
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        self.results[stage].append(elapsed)
        return result, elapsed
    
    def report(self):
        """Generate benchmark report"""
        print("\n" + "="*60)
        print("JETT LATENCY BENCHMARK REPORT")
        print("="*60)
        
        for stage, times in self.results.items():
            if times:
                print(f"\n{stage.upper()}")
                print(f"  Samples: {len(times)}")
                print(f"  Mean:    {statistics.mean(times):.1f}ms")
                print(f"  Median:  {statistics.median(times):.1f}ms")
                print(f"  P95:     {sorted(times)[int(len(times)*0.95)]:.1f}ms")
                print(f"  Min:     {min(times):.1f}ms")
                print(f"  Max:     {max(times):.1f}ms")
        
        print("\n" + "="*60)

# Usage
bench = LatencyBenchmark()

# Measure STT
transcription, stt_time = bench.measure("stt", transcribe, audio_data)
print(f"STT: {stt_time:.1f}ms")

# Measure LLM
response, llm_time = bench.measure("llm", generate, transcription)
print(f"LLM: {llm_time:.1f}ms")

# Measure TTS
audio, tts_time = bench.measure("tts", synthesize, response)
print(f"TTS: {tts_time:.1f}ms")

# Generate report
bench.report()
```

### Benchmark Targets

| Stage | Target | Acceptable | Fail |
|-------|--------|------------|------|
| Wake word | <50ms | <100ms | >100ms |
| VAD | <10ms | <20ms | >50ms |
| STT | <200ms | <300ms | >500ms |
| LLM | <300ms | <500ms | >1000ms |
| TTS (first audio) | <300ms | <400ms | >500ms |
| **E2E** | **<500ms** | **<800ms** | **>1000ms** |

---

## VRAM Validation

```python
# benchmarks/vram.py
import subprocess
import json

def get_vram_usage():
    """Get current VRAM usage via nvidia-smi"""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used,memory.total,memory.free", 
         "--format=csv,noheader,nounits"],
        capture_output=True, text=True
    )
    used, total, free = map(int, result.stdout.strip().split(", "))
    return {"used_mb": used, "total_mb": total, "free_mb": free}

def validate_vram_budget():
    """Validate VRAM stays within budget"""
    vram = get_vram_usage()
    
    BUDGET_MB = 7000  # 7GB target, leaving 1GB headroom
    
    print(f"\nVRAM Status:")
    print(f"  Used:  {vram['used_mb']} MB")
    print(f"  Free:  {vram['free_mb']} MB")
    print(f"  Total: {vram['total_mb']} MB")
    print(f"  Budget: {BUDGET_MB} MB")
    
    if vram['used_mb'] > BUDGET_MB:
        print(f"  ❌ OVER BUDGET by {vram['used_mb'] - BUDGET_MB} MB")
        return False
    else:
        print(f"  ✅ WITHIN BUDGET ({BUDGET_MB - vram['used_mb']} MB headroom)")
        return True

# Run after loading all models
validate_vram_budget()
```

---

## Security Boundary Tests

```python
# tests/test_security.py
import pytest
from portainer_wrapper import handle_container_action, PermissionError

class TestSecurityBoundaries:
    """Test that security boundaries are enforced"""
    
    def test_blocked_action_raises(self):
        """Blocked actions should raise PermissionError"""
        with pytest.raises(PermissionError) as exc:
            handle_container_action("delete", "postgres")
        assert "not in allowlist" in str(exc.value)
    
    def test_unknown_container_raises(self):
        """Unknown containers should raise PermissionError"""
        with pytest.raises(PermissionError) as exc:
            handle_container_action("start", "malicious_container")
        assert "not in allowlist" in str(exc.value)
    
    def test_rate_limit_enforced(self):
        """Rate limiting should kick in after threshold"""
        # Make 10 rapid requests (at limit)
        for _ in range(10):
            handle_container_action("status", "n8n")
        
        # 11th should fail
        with pytest.raises(PermissionError) as exc:
            handle_container_action("status", "n8n")
        assert "Rate limit" in str(exc.value)
    
    def test_allowed_action_succeeds(self):
        """Allowed actions should work"""
        result = handle_container_action("status", "n8n")
        assert result is not None
    
    def test_audit_log_written(self):
        """All actions should be logged"""
        import os
        log_path = "/var/log/jett/audit.log"
        
        # Get initial size
        initial_size = os.path.getsize(log_path) if os.path.exists(log_path) else 0
        
        # Perform action
        handle_container_action("status", "n8n")
        
        # Check log grew
        new_size = os.path.getsize(log_path)
        assert new_size > initial_size, "Audit log should have new entries"
    
    def test_audit_log_no_secrets(self):
        """Audit logs should not contain secrets"""
        with open("/var/log/jett/audit.log", "r") as f:
            content = f.read()
        
        # Check for common secret patterns
        assert "sk-ant-" not in content, "API keys in audit log!"
        assert "password" not in content.lower(), "Passwords in audit log!"
        assert "token" not in content.lower() or "PORTAINER_TOKEN" not in content
```

---

## Integration Test Suite

```python
# tests/test_integration.py
import pytest
import asyncio

class TestVoicePipeline:
    """End-to-end voice pipeline tests"""
    
    @pytest.fixture
    def sample_audio(self):
        """Load test audio file"""
        # 3-second audio saying "What time is it?"
        return load_audio("tests/fixtures/what_time_is_it.wav")
    
    def test_stt_accuracy(self, sample_audio):
        """STT should transcribe accurately"""
        result = transcribe(sample_audio)
        assert "time" in result.lower()
        assert "what" in result.lower()
    
    def test_llm_responds(self):
        """LLM should generate response"""
        response = generate("What time is it?")
        assert len(response) > 0
        assert "time" in response.lower() or ":" in response  # Contains time
    
    def test_tts_produces_audio(self):
        """TTS should produce audio bytes"""
        audio = synthesize("The time is 3:30 PM")
        assert len(audio) > 0
        assert isinstance(audio, bytes)
    
    @pytest.mark.asyncio
    async def test_e2e_latency(self, sample_audio):
        """End-to-end should complete under 500ms"""
        import time
        
        start = time.perf_counter()
        
        # Full pipeline
        transcript = transcribe(sample_audio)
        response = generate(transcript)
        audio = synthesize(response)
        
        elapsed = (time.perf_counter() - start) * 1000
        
        assert elapsed < 500, f"E2E took {elapsed:.0f}ms, target is <500ms"

class TestHybridRouting:
    """Test query routing logic"""
    
    def test_simple_routes_local(self):
        """Simple queries should route to local LLM"""
        queries = [
            "What time is it?",
            "Set a timer for 5 minutes",
            "Turn off the lights",
        ]
        for q in queries:
            route = classify_query(q)
            assert route == "local", f"'{q}' should route local, got {route}"
    
    def test_complex_routes_cloud(self):
        """Complex queries should route to cloud"""
        queries = [
            "Explain the theory of relativity in detail",
            "Help me debug this Python code with async issues",
            "Write a detailed business plan for a startup",
        ]
        for q in queries:
            route = classify_query(q)
            assert route == "cloud", f"'{q}' should route cloud, got {route}"
    
    def test_cached_returns_cache(self):
        """Previously answered queries should hit cache"""
        # First query
        response1, route1 = query_with_routing("What's the weather?")
        
        # Same query again
        response2, route2 = query_with_routing("What's the weather?")
        
        assert route2 == "cache", "Second identical query should hit cache"
```

---

## Test Fixtures

```
tests/
├── fixtures/
│   ├── what_time_is_it.wav       # Test audio
│   ├── turn_off_lights.wav
│   ├── complex_question.wav
│   └── wake_word_jett.wav
├── test_security.py
├── test_integration.py
├── test_voice.py
├── test_routing.py
└── conftest.py                    # pytest fixtures
```

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Security tests only
pytest tests/test_security.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Benchmarks (not pytest, standalone)
python benchmarks/latency.py
python benchmarks/vram.py
```

---

## CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Test Jett

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/ -v --ignore=tests/test_gpu.py
      
      # GPU tests run locally only
```

---

## Implementation Checklist

- [ ] Create `tests/` directory structure
- [ ] Create test fixtures (audio samples)
- [ ] Implement security boundary tests
- [ ] Implement latency benchmarks
- [ ] Implement VRAM validation
- [ ] Implement integration tests
- [ ] Set up pytest configuration
- [ ] Document benchmark results in context/

---

## Interview Metrics to Capture

| Metric | Target | Actual | Notes |
|--------|--------|--------|-------|
| E2E latency (P50) | <500ms | - | - |
| E2E latency (P95) | <800ms | - | - |
| VRAM usage | <7GB | - | - |
| Local routing % | 70% | - | - |
| Cache hit rate | 70% | - | - |
| Security test pass | 100% | - | - |

## Next Step

After tests pass: `/jett-security` for final security review before deployment
