"""
TTS inference benchmark for Jett voice assistant.

Tests:
1. VRAM usage after loading Kokoro
2. Time-to-first-audio for short text
3. Time-to-first-audio for long text
4. Save sample audio files

Usage: python benchmarks/tts_benchmark.py
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_vram_mb() -> int:
    """Get current VRAM usage in MB."""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True, text=True
    )
    return int(result.stdout.strip())


def main():
    # Suppress warnings
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    print("\n TTS BENCHMARK")
    print("=" * 50)
    print(f"VRAM before loading: {get_vram_mb()} MB")

    # Import and load TTS
    from src.voice.tts import TTS

    tts = TTS(voice="af_heart", device="cuda")
    load_time = tts.load()

    vram_after_load = get_vram_mb()
    print(f"VRAM after loading: {vram_after_load} MB")
    print(f"Model load time: {load_time:.1f}s")
    print("=" * 50)

    # Test cases
    test_cases = [
        ("Short greeting", "Hello, I'm Jett."),
        ("Status update", "All systems are running normally."),
        ("Long response", "The database has been restarted successfully. Current uptime is 2 hours and 34 minutes. All health checks are passing."),
        ("Container action", "I've restarted the n8n container. It should be back online in a few seconds."),
    ]

    results = []

    for label, text in test_cases:
        audio, first_chunk_ms, total_ms = tts.synthesize_timed(text)
        duration = len(audio) / tts.SAMPLE_RATE

        result = {
            "label": label,
            "text_len": len(text),
            "first_chunk_ms": first_chunk_ms,
            "total_ms": total_ms,
            "duration_s": duration,
            "rtf": total_ms / 1000 / duration if duration > 0 else 0  # Real-time factor
        }
        results.append(result)

        print(f"\n{label}")
        print(f"  Text: \"{text[:50]}...\"" if len(text) > 50 else f"  Text: \"{text}\"")
        print(f"  First chunk: {first_chunk_ms:.0f}ms")
        print(f"  Total: {total_ms:.0f}ms")
        print(f"  Audio duration: {duration:.2f}s")
        print(f"  Real-time factor: {result['rtf']:.2f}x")

    # Summary
    print("\n" + "=" * 50)
    print(" SUMMARY")
    print("=" * 50)
    print(f"{'Test':<20} {'First Chunk':>12} {'Total':>10} {'RTF':>8}")
    print("-" * 50)
    for r in results:
        print(f"{r['label']:<20} {r['first_chunk_ms']:>10.0f}ms {r['total_ms']:>8.0f}ms {r['rtf']:>7.2f}x")

    avg_first_chunk = sum(r["first_chunk_ms"] for r in results) / len(results)
    avg_rtf = sum(r["rtf"] for r in results) / len(results)

    print("-" * 50)
    print(f"{'Average':<20} {avg_first_chunk:>10.0f}ms {'':>10} {avg_rtf:>7.2f}x")

    print(f"\nVRAM Usage: {vram_after_load} MB")
    print(f"VRAM Budget: 200 MB (for TTS component)")

    # Save sample audio files
    print("\n" + "=" * 50)
    print(" SAVING SAMPLE AUDIO")
    print("=" * 50)

    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    samples = [
        ("tts_hello.wav", "Hello, I'm Jett."),
        ("tts_status.wav", "All systems are running normally."),
        ("tts_long_response.wav", "The database has been restarted successfully. Current uptime is 2 hours and 34 minutes. All health checks are passing."),
    ]

    for filename, text in samples:
        path = fixtures_dir / filename
        duration = tts.synthesize_to_file(text, str(path))
        print(f"Saved: {path.name} ({duration:.2f}s)")

    print("\n BENCHMARK COMPLETE")
    print(f"Target first-chunk latency: <300ms")
    status = "PASS" if avg_first_chunk < 300 else "FAIL"
    print(f"Average first-chunk: {avg_first_chunk:.0f}ms - {status}")


if __name__ == "__main__":
    main()
