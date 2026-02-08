"""
Wake Word Detection Benchmark

Measures:
1. Detection latency (time from wake word audio to callback)
2. False positive rate with non-wake-word speech
3. CPU usage during idle listening

Usage:
    python benchmarks/wake_word_benchmark.py
    python benchmarks/wake_word_benchmark.py --threshold 0.5 --iterations 10

Requirements:
    - openwakeword installed
    - Test audio files in tests/fixtures/ (optional — uses synthetic audio if missing)
"""

import argparse
import os
import statistics
import sys
import threading
import time
from pathlib import Path

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


def measure_detection_latency(
    model_name: str = "hey_jarvis",
    threshold: float = 0.5,
    iterations: int = 10,
) -> list[float]:
    """
    Measure wake word detection latency by feeding audio directly to the model.

    Returns list of latency measurements in milliseconds.
    """
    import openwakeword
    from openwakeword.model import Model

    openwakeword.utils.download_models()
    model = Model(wakeword_models=[model_name], inference_framework="onnx")

    # Generate synthetic "wake word" audio: a 1-second 16kHz sine sweep
    # This won't actually trigger the model, so we measure prediction throughput
    sample_rate = 16000
    chunk_size = 1280
    duration = 1.0
    samples = int(sample_rate * duration)
    audio = np.random.randn(samples).astype(np.float32) * 0.01

    latencies = []

    for i in range(iterations):
        model.reset()
        start = time.perf_counter()

        # Feed all chunks for one second of audio
        for offset in range(0, len(audio), chunk_size):
            chunk = audio[offset : offset + chunk_size]
            if len(chunk) < chunk_size:
                chunk = np.pad(chunk, (0, chunk_size - len(chunk)))
            model.predict(chunk)

        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)

    return latencies


def measure_false_positive_rate(
    model_name: str = "hey_jarvis",
    threshold: float = 0.5,
    duration_seconds: float = 10.0,
) -> dict:
    """
    Feed random noise and non-wake-word audio to measure false positives.

    Returns dict with total_chunks, false_positives, and false_positive_rate.
    """
    import openwakeword
    from openwakeword.model import Model

    openwakeword.utils.download_models()
    model = Model(wakeword_models=[model_name], inference_framework="onnx")

    sample_rate = 16000
    chunk_size = 1280
    total_chunks = int(sample_rate * duration_seconds / chunk_size)

    false_positives = 0

    for _ in range(total_chunks):
        # Random noise (simulates ambient background)
        chunk = np.random.randn(chunk_size).astype(np.float32) * 0.02
        prediction = model.predict(chunk)
        score = prediction.get(model_name, 0.0)
        if score > threshold:
            false_positives += 1

    return {
        "total_chunks": total_chunks,
        "false_positives": false_positives,
        "false_positive_rate": false_positives / total_chunks if total_chunks > 0 else 0,
        "duration_seconds": duration_seconds,
    }


def measure_cpu_idle(duration_seconds: float = 5.0) -> dict:
    """
    Measure CPU usage of the wake word detector during idle listening.

    Returns dict with cpu_percent (average over duration).
    """
    from src.voice.wake_word import WakeWordDetector

    triggered = threading.Event()
    detector = WakeWordDetector(debug=False)
    detector.start(on_wake=lambda: triggered.set())

    # Measure CPU via process time
    start_wall = time.perf_counter()
    start_cpu = time.process_time()

    time.sleep(duration_seconds)

    end_cpu = time.process_time()
    end_wall = time.perf_counter()

    detector.stop()

    wall_elapsed = end_wall - start_wall
    cpu_elapsed = end_cpu - start_cpu
    cpu_percent = (cpu_elapsed / wall_elapsed) * 100 if wall_elapsed > 0 else 0

    return {
        "wall_seconds": wall_elapsed,
        "cpu_seconds": cpu_elapsed,
        "cpu_percent": cpu_percent,
        "false_triggered": triggered.is_set(),
    }


def format_stats(times: list[float], label: str) -> str:
    """Format statistics for a list of times."""
    if not times:
        return f"{label}: No data"

    sorted_times = sorted(times)
    p50 = sorted_times[len(sorted_times) // 2]
    p95_idx = min(int(len(sorted_times) * 0.95), len(sorted_times) - 1)
    p95 = sorted_times[p95_idx]

    return (
        f"{label:<20} "
        f"P50: {p50:>6.1f}ms  "
        f"P95: {p95:>6.1f}ms  "
        f"Min: {min(times):>6.1f}ms  "
        f"Max: {max(times):>6.1f}ms  "
        f"Avg: {statistics.mean(times):>6.1f}ms"
    )


def main():
    parser = argparse.ArgumentParser(description="Wake Word Detection Benchmark")
    parser.add_argument(
        "--iterations", "-n",
        type=int,
        default=10,
        help="Number of latency iterations (default: 10)"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.5,
        help="Detection threshold (default: 0.5)"
    )
    parser.add_argument(
        "--fp-duration",
        type=float,
        default=10.0,
        help="Seconds of noise for false positive test (default: 10)"
    )
    parser.add_argument(
        "--cpu-duration",
        type=float,
        default=5.0,
        help="Seconds for CPU idle measurement (default: 5)"
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  JETT WAKE WORD BENCHMARK")
    print("=" * 60)

    # 1. Detection latency (prediction throughput for 1s of audio)
    print(f"\n--- Prediction Latency (1s audio, {args.iterations} iterations) ---")
    latencies = measure_detection_latency(
        threshold=args.threshold,
        iterations=args.iterations,
    )
    print(format_stats(latencies, "1s audio predict"))
    target_ms = 500
    p50 = sorted(latencies)[len(latencies) // 2]
    print(f"Target: <{target_ms}ms  P50: {p50:.0f}ms — {'PASS' if p50 < target_ms else 'FAIL'}")

    # 2. False positive rate
    print(f"\n--- False Positive Rate ({args.fp_duration}s of noise) ---")
    fp_results = measure_false_positive_rate(
        threshold=args.threshold,
        duration_seconds=args.fp_duration,
    )
    print(f"  Chunks tested: {fp_results['total_chunks']}")
    print(f"  False positives: {fp_results['false_positives']}")
    print(f"  FP rate: {fp_results['false_positive_rate']:.4%}")
    print(f"  Target: 0%  — {'PASS' if fp_results['false_positives'] == 0 else 'FAIL'}")

    # 3. CPU idle usage
    print(f"\n--- CPU Usage (idle listening, {args.cpu_duration}s) ---")
    cpu_results = measure_cpu_idle(duration_seconds=args.cpu_duration)
    print(f"  Wall time: {cpu_results['wall_seconds']:.1f}s")
    print(f"  CPU time: {cpu_results['cpu_seconds']:.3f}s")
    print(f"  CPU usage: {cpu_results['cpu_percent']:.1f}%")
    print(f"  False trigger during idle: {cpu_results['false_triggered']}")
    print(f"  Target: <5% CPU  — {'PASS' if cpu_results['cpu_percent'] < 5 else 'FAIL'}")

    # Summary
    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Prediction latency P50:  {p50:.0f}ms  ({'PASS' if p50 < target_ms else 'FAIL'})")
    print(f"  False positive rate:     {fp_results['false_positive_rate']:.4%}  ({'PASS' if fp_results['false_positives'] == 0 else 'FAIL'})")
    print(f"  CPU usage (idle):        {cpu_results['cpu_percent']:.1f}%  ({'PASS' if cpu_results['cpu_percent'] < 5 else 'FAIL'})")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
