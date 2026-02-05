"""
Quick A/B comparison: Qwen3 8B vs 4B for time-to-first-token.

Usage: python benchmarks/llm_comparison.py
"""

import time
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"

PROMPTS = [
    "What time is it?",
    "Restart the n8n container",
    "How's the database doing?",
    "List all running containers",
    "What can you help me with?",
]

MODELS = ["jett-qwen3", "qwen3:4b"]


def warm_up_model(model: str):
    """Pre-load model into VRAM."""
    print(f"  Warming up {model}...", end=" ", flush=True)
    start = time.perf_counter()
    requests.post(OLLAMA_URL, json={
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "stream": False,
        "options": {"num_predict": 5}
    }, timeout=120)
    elapsed = time.perf_counter() - start
    print(f"done ({elapsed:.1f}s)")


def measure_first_token(model: str, prompt: str) -> tuple[float, str]:
    """Measure time to first token."""
    start = time.perf_counter()
    first_token_time = None
    response_text = ""

    response = requests.post(OLLAMA_URL, json={
        "model": model,
        "messages": [{"role": "user", "content": f"{prompt} /no_think"}],
        "stream": True
    }, stream=True, timeout=60)

    for line in response.iter_lines():
        if line:
            import json
            data = json.loads(line)
            if "message" in data and "content" in data["message"]:
                content = data["message"]["content"]
                # Skip thinking blocks
                if "<think>" in content or "</think>" in content:
                    continue
                if content.strip():
                    if first_token_time is None:
                        first_token_time = (time.perf_counter() - start) * 1000
                    response_text += content
            if data.get("done", False):
                break

    return first_token_time or 0, response_text[:50]


def main():
    print("\n" + "=" * 60)
    print("  LLM COMPARISON: Qwen3 8B vs 4B")
    print("=" * 60)

    results = {model: [] for model in MODELS}

    for model in MODELS:
        print(f"\nTesting: {model}")
        warm_up_model(model)

        for prompt in PROMPTS:
            ttft, preview = measure_first_token(model, prompt)
            results[model].append(ttft)
            print(f"  {prompt[:30]:<30} -> {ttft:>6.0f}ms")

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY: Time to First Token")
    print("=" * 60)
    print(f"{'Model':<20} {'Avg':>10} {'Min':>10} {'Max':>10}")
    print("-" * 60)

    for model in MODELS:
        times = results[model]
        avg = sum(times) / len(times)
        print(f"{model:<20} {avg:>8.0f}ms {min(times):>8.0f}ms {max(times):>8.0f}ms")

    # Recommendation
    print("\n" + "-" * 60)
    avg_8b = sum(results["jett-qwen3"]) / len(results["jett-qwen3"])
    avg_4b = sum(results["qwen3:4b"]) / len(results["qwen3:4b"])

    if avg_4b < avg_8b * 0.6:  # 40% faster
        print(f"RECOMMENDATION: Use qwen3:4b ({avg_8b/avg_4b:.1f}x faster)")
    else:
        print(f"RECOMMENDATION: Keep jett-qwen3 (only {avg_8b/avg_4b:.1f}x slower)")


if __name__ == "__main__":
    main()
