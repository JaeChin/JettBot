"""
Jett Voice Assistant — Main Entry Point

A local-first voice assistant with hybrid cloud routing.
All audio processing happens locally on your GPU.

Usage:
    python -m src.main           # Run interactively
    python -m src.main --debug   # Run with debug output

Requirements:
    - RTX 3070 or better (8GB VRAM)
    - Ollama running with jett-qwen3 model
    - Microphone and speakers

Phase 1 Features:
    - Speech-to-text (faster-whisper)
    - Local LLM (Qwen3 8B via Ollama)
    - Text-to-speech (Kokoro-82M)
    - Simple silence-based end-of-speech detection

Coming in Phase 2:
    - Wake word detection ("Hey Jett")
    - Voice Activity Detection (Silero VAD)
    - Hybrid routing (local + cloud LLM)
"""

import argparse
import sys


def check_ollama() -> bool:
    """Check if Ollama is running and jett-qwen3 is available."""
    import requests

    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = resp.json().get("models", [])
        model_names = [m.get("name", "") for m in models]

        if not any("jett-qwen3" in name for name in model_names):
            print("Error: jett-qwen3 model not found in Ollama.")
            print("Run: ollama create jett-qwen3 -f models/Modelfile.jett-qwen3")
            return False

        return True

    except requests.exceptions.ConnectionError:
        print("Error: Ollama is not running.")
        print("Start Ollama first: ollama serve")
        return False
    except Exception as e:
        print(f"Error checking Ollama: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Jett Voice Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug output"
    )
    parser.add_argument(
        "--silence-threshold",
        type=float,
        default=0.01,
        help="RMS threshold for silence detection (default: 0.01)"
    )
    parser.add_argument(
        "--silence-duration",
        type=float,
        default=1.0,
        help="Seconds of silence to end recording (default: 1.0)"
    )
    args = parser.parse_args()

    print()
    print("=" * 40)
    print("  JETT VOICE ASSISTANT")
    print("  Phase 1: Core Voice Loop")
    print("=" * 40)
    print()

    # Check Ollama
    print("Checking Ollama...")
    if not check_ollama():
        sys.exit(1)
    print("Ollama OK")
    print()

    # Import and run pipeline
    from src.voice.pipeline import VoicePipeline

    pipeline = VoicePipeline(debug=args.debug)
    pipeline.SILENCE_THRESHOLD = args.silence_threshold
    pipeline.SILENCE_DURATION = args.silence_duration

    try:
        pipeline.run()
    except KeyboardInterrupt:
        pass

    print("Goodbye!")


if __name__ == "__main__":
    main()
