"""
LLM inference benchmark for Jett voice assistant.

Tests:
1. Simple query latency (what voice assistant handles most)
2. Tool-calling format (can it produce structured output?)
3. Tokens per second
4. VRAM usage during inference

Usage: python benchmarks/llm_benchmark.py
"""

import time
import json
import subprocess
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3:8b"

def get_vram_mb() -> int:
    """Get current VRAM usage in MB."""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True
    )
    return int(result.stdout.strip())


def benchmark_query(prompt: str, label: str) -> dict:
    """Benchmark a single query."""
    start = time.perf_counter()

    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    })

    elapsed_ms = (time.perf_counter() - start) * 1000
    data = response.json()

    tokens = data.get("eval_count", 0)
    eval_duration_ns = data.get("eval_duration", 1)
    tokens_per_sec = (tokens / eval_duration_ns) * 1e9 if eval_duration_ns else 0

    result = {
        "label": label,
        "latency_ms": round(elapsed_ms, 1),
        "tokens": tokens,
        "tokens_per_sec": round(tokens_per_sec, 1),
        "response_preview": data.get("response", "")[:100]
    }

    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"  Latency: {result['latency_ms']}ms")
    print(f"  Tokens: {result['tokens']}")
    print(f"  Speed: {result['tokens_per_sec']} tok/s")
    print(f"  Response: {result['response_preview']}...")

    return result


def main():
    print("\n LLM BENCHMARK")
    print(f"Model: {MODEL}")
    print(f"VRAM before: {get_vram_mb()} MB")

    results = []

    # Test 1: Simple query (most common for voice assistant)
    results.append(benchmark_query(
        "What time is it in Tokyo? Answer in one sentence.",
        "Simple Query"
    ))

    # Test 2: Command interpretation
    results.append(benchmark_query(
        "The user said: 'restart the database'. What container action should be taken? Reply with just the action and container name.",
        "Command Interpretation"
    ))

    # Test 3: Slightly complex
    results.append(benchmark_query(
        "Explain what Docker containers are in 2-3 sentences for someone new to infrastructure.",
        "Short Explanation"
    ))

    # Test 4: Tool calling format
    results.append(benchmark_query(
        'You have access to a function called container_action(action, container). The user says "restart n8n". Respond with ONLY the function call in JSON format: {"action": "...", "container": "..."}',
        "Tool Call Format"
    ))

    print(f"\n{'='*50}")
    print(f"  VRAM after: {get_vram_mb()} MB")
    print(f"{'='*50}")

    # Summary
    print("\n SUMMARY")
    print(f"{'Label':<25} {'Latency':>10} {'Tokens/s':>10}")
    print("-" * 50)
    for r in results:
        print(f"{r['label']:<25} {r['latency_ms']:>8.0f}ms {r['tokens_per_sec']:>8.1f}")

    print(f"\nVRAM Usage: {get_vram_mb()} MB")
    print(f"VRAM Budget: 4500 MB")
    budget_status = "WITHIN BUDGET" if get_vram_mb() < 6000 else "OVER BUDGET"
    print(f"Status: {budget_status}")


if __name__ == "__main__":
    main()
