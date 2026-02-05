"""
End-to-End Voice Pipeline Benchmark

Runs the full STT → LLM → TTS pipeline using pre-recorded audio files.
Measures latency at each stage and reports P50, P95, min, max statistics.

Usage:
    python benchmarks/e2e_benchmark.py
    python benchmarks/e2e_benchmark.py --iterations 20
    python benchmarks/e2e_benchmark.py --audio path/to/custom.wav

Requirements:
    - Test audio files in tests/fixtures/ (or specify --audio)
    - Ollama running with jett-qwen3 model
"""

import argparse
import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


@dataclass
class BenchmarkResults:
    """Aggregated benchmark results."""
    stt_times: list[float] = field(default_factory=list)
    llm_first_times: list[float] = field(default_factory=list)
    tts_first_times: list[float] = field(default_factory=list)
    e2e_times: list[float] = field(default_factory=list)
    transcriptions: list[str] = field(default_factory=list)
    responses: list[str] = field(default_factory=list)


def percentile(data: list[float], p: int) -> float:
    """Calculate percentile of a list."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_data) else f
    return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)


def format_stats(times: list[float], label: str) -> str:
    """Format statistics for a list of times."""
    if not times:
        return f"{label}: No data"

    return (
        f"{label:<15} "
        f"P50: {percentile(times, 50):>6.0f}ms  "
        f"P95: {percentile(times, 95):>6.0f}ms  "
        f"Min: {min(times):>6.0f}ms  "
        f"Max: {max(times):>6.0f}ms  "
        f"Avg: {statistics.mean(times):>6.0f}ms"
    )


def find_test_audio() -> list[Path]:
    """Find test audio files."""
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"

    # Look for WAV files
    audio_files = list(fixtures_dir.glob("*.wav"))

    if not audio_files:
        print(f"No WAV files found in {fixtures_dir}")
        print("Run the TTS benchmark first to generate test files:")
        print("  python benchmarks/tts_benchmark.py")
        return []

    return audio_files


def create_test_audio() -> Optional[Path]:
    """Create a simple test audio file with speech."""
    try:
        from src.voice.tts import TTS

        print("Creating test audio file...")
        tts = TTS(device="cuda")
        tts.load()

        test_text = "What time is it right now?"
        fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
        fixtures_dir.mkdir(parents=True, exist_ok=True)

        output_path = fixtures_dir / "benchmark_query.wav"
        tts.synthesize_to_file(test_text, str(output_path))

        print(f"Created: {output_path}")
        return output_path

    except Exception as e:
        print(f"Failed to create test audio: {e}")
        return None


def run_benchmark(
    pipeline,
    audio_files: list[Path],
    iterations: int = 10,
    warmup: int = 2
) -> BenchmarkResults:
    """
    Run the benchmark.

    Args:
        pipeline: VoicePipeline instance
        audio_files: List of audio file paths
        iterations: Number of benchmark iterations
        warmup: Number of warmup iterations (not counted)

    Returns:
        BenchmarkResults with timing data
    """
    results = BenchmarkResults()

    total_runs = warmup + iterations

    print(f"\nRunning {warmup} warmup + {iterations} benchmark iterations...")
    print("-" * 60)

    for i in range(total_runs):
        is_warmup = i < warmup
        run_num = i + 1
        prefix = "[WARMUP]" if is_warmup else f"[{run_num - warmup}/{iterations}]"

        # Cycle through audio files
        audio_file = audio_files[i % len(audio_files)]

        print(f"{prefix} Processing: {audio_file.name}...", end=" ", flush=True)

        try:
            metrics = pipeline.process_file(str(audio_file))

            print(f"E2E: {metrics.e2e_ms:.0f}ms")

            if not is_warmup:
                results.stt_times.append(metrics.stt_ms)
                results.llm_first_times.append(metrics.llm_first_token_ms)
                results.tts_first_times.append(metrics.tts_first_audio_ms)
                results.e2e_times.append(metrics.e2e_ms)
                results.transcriptions.append(metrics.user_text)
                results.responses.append(metrics.jett_text)

        except Exception as e:
            print(f"ERROR: {e}")
            continue

    return results


def main():
    parser = argparse.ArgumentParser(description="E2E Voice Pipeline Benchmark")
    parser.add_argument(
        "--iterations", "-n",
        type=int,
        default=10,
        help="Number of benchmark iterations (default: 10)"
    )
    parser.add_argument(
        "--warmup", "-w",
        type=int,
        default=2,
        help="Number of warmup iterations (default: 2)"
    )
    parser.add_argument(
        "--audio", "-a",
        type=str,
        help="Path to custom audio file (optional)"
    )
    parser.add_argument(
        "--create-audio",
        action="store_true",
        help="Create test audio using TTS"
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  JETT E2E PIPELINE BENCHMARK")
    print("=" * 60)

    # Find or create audio files
    if args.audio:
        audio_files = [Path(args.audio)]
        if not audio_files[0].exists():
            print(f"Error: Audio file not found: {args.audio}")
            sys.exit(1)
    else:
        audio_files = find_test_audio()

        if not audio_files and args.create_audio:
            created = create_test_audio()
            if created:
                audio_files = [created]

        if not audio_files:
            print("\nNo audio files available. Options:")
            print("  1. Run TTS benchmark first: python benchmarks/tts_benchmark.py")
            print("  2. Create test audio: python benchmarks/e2e_benchmark.py --create-audio")
            print("  3. Specify custom audio: python benchmarks/e2e_benchmark.py --audio file.wav")
            sys.exit(1)

    print(f"\nUsing audio files:")
    for f in audio_files:
        print(f"  - {f.name}")

    # Initialize pipeline
    print("\nInitializing pipeline...")
    from src.voice.pipeline import VoicePipeline
    pipeline = VoicePipeline()
    pipeline.load_models()

    # Run benchmark
    results = run_benchmark(
        pipeline,
        audio_files,
        iterations=args.iterations,
        warmup=args.warmup
    )

    # Print results
    print()
    print("=" * 60)
    print("  BENCHMARK RESULTS")
    print("=" * 60)
    print()
    print(format_stats(results.stt_times, "STT"))
    print(format_stats(results.llm_first_times, "LLM (first)"))
    print(format_stats(results.tts_first_times, "TTS (first)"))
    print(format_stats(results.e2e_times, "E2E Total"))
    print()

    # Target check
    target_e2e = 500  # ms
    p50_e2e = percentile(results.e2e_times, 50)
    p95_e2e = percentile(results.e2e_times, 95)

    print("-" * 60)
    print(f"Target E2E latency: <{target_e2e}ms")
    print(f"P50 E2E: {p50_e2e:.0f}ms - {'PASS' if p50_e2e < target_e2e else 'FAIL'}")
    print(f"P95 E2E: {p95_e2e:.0f}ms - {'PASS' if p95_e2e < target_e2e * 2 else 'FAIL'}")
    print("-" * 60)

    # Sample interactions
    print("\nSample Interactions:")
    for i, (trans, resp) in enumerate(zip(results.transcriptions[:3], results.responses[:3])):
        print(f"\n  [{i+1}] User: \"{trans}\"")
        print(f"      Jett: \"{resp[:80]}{'...' if len(resp) > 80 else ''}\"")

    print()
    print("Benchmark complete.")


if __name__ == "__main__":
    main()
