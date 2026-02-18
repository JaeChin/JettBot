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

Phase 2 Features:
    - Wake word detection ("Hey Jett" via openWakeWord, CPU-only)
    - --no-wake flag for always-listening mode

Phase 3 Features:
    - Silero VAD for silence detection (replaces RMS energy)
    - Hybrid routing (local + cloud LLM)
    - --no-vad flag for RMS fallback
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Jett models need ~6.8 GB to load fully on GPU.
# If less is free, the LLM gets partially offloaded to CPU → 5-10x slower.
VRAM_REQUIRED_MB = 6800
VRAM_WARNING_MB = 7200

GPU_HEAVY_PROCESSES = {
    "chrome.exe": "Google Chrome (disable HW acceleration or close)",
    "firefox.exe": "Firefox (disable HW acceleration or close)",
    "msedge.exe": "Microsoft Edge (disable HW acceleration or close)",
    "discord.exe": "Discord (disable HW acceleration or close)",
    "obs64.exe": "OBS Studio",
    "nvidia broadcast.exe": "NVIDIA Broadcast",
    "wallpaper64.exe": "Wallpaper Engine",
    "steamwebhelper.exe": "Steam overlay",
}


def check_vram(verbose: bool = False) -> tuple[bool, int]:
    """
    Check if there's enough free VRAM to run Jett fully on GPU.

    Returns:
        (ok, free_mb)
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print("Warning: nvidia-smi failed, skipping VRAM check")
            return True, 0

        parts = result.stdout.strip().split(",")
        used_mb = int(parts[0].strip())
        total_mb = int(parts[1].strip())
        free_mb = int(parts[2].strip())
    except FileNotFoundError:
        print("Warning: nvidia-smi not found, skipping VRAM check")
        return True, 0

    # Get GPU processes
    processes = []
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        seen_pids = set()
        for line in result.stdout.strip().split("\n"):
            if line.strip() and "Insufficient Permissions" not in line:
                parts = line.split(",", 1)
                if len(parts) == 2:
                    pid = parts[0].strip()
                    if pid not in seen_pids:
                        seen_pids.add(pid)
                        processes.append({"pid": pid, "name": parts[1].strip()})
    except Exception:
        pass

    print(f"  GPU: {used_mb} MB used / {total_mb} MB total ({free_mb} MB free)")

    # Find heavy processes
    heavy = []
    for proc in processes:
        exe = Path(proc["name"]).name.lower()
        for pattern, desc in GPU_HEAVY_PROCESSES.items():
            if pattern in exe:
                heavy.append(desc)

    if verbose and processes:
        print(f"  GPU processes ({len(processes)}):")
        for proc in processes:
            print(f"    PID {proc['pid']:>6}  {Path(proc['name']).name}")

    if heavy:
        print(f"  GPU-heavy apps: {', '.join(sorted(set(heavy)))}")

    if free_mb >= VRAM_WARNING_MB:
        print(f"  VRAM: OK")
        return True, free_mb
    elif free_mb >= VRAM_REQUIRED_MB:
        print(f"  VRAM: OK (tight — {free_mb} MB free)")
        return True, free_mb
    else:
        deficit = VRAM_REQUIRED_MB - free_mb
        print(f"  VRAM: INSUFFICIENT ({free_mb} MB free < {VRAM_REQUIRED_MB} MB needed)")
        print(f"  Close GPU-heavy apps to free ~{deficit} MB, or use --force to start anyway.")
        if heavy:
            for desc in sorted(set(heavy)):
                print(f"    - {desc}")
        return False, free_mb


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
        "--force",
        action="store_true",
        help="Skip VRAM check and start anyway"
    )
    parser.add_argument(
        "--silence-threshold",
        type=float,
        default=None,
        help="Silence detection threshold (default: 0.5 for VAD, 0.01 for RMS)"
    )
    parser.add_argument(
        "--silence-duration",
        type=float,
        default=1.0,
        help="Seconds of silence to end recording (default: 1.0)"
    )
    parser.add_argument(
        "--no-vad",
        action="store_true",
        help="Disable Silero VAD, use RMS energy silence detection instead"
    )
    parser.add_argument(
        "--no-wake",
        action="store_true",
        help="Disable wake word detection (always listening)"
    )
    parser.add_argument(
        "--wake-debug",
        action="store_true",
        help="Print wake word detection scores every second"
    )
    parser.add_argument(
        "--router-mode",
        choices=["local", "cloud", "hybrid"],
        default="local",
        help="LLM routing mode (default: local)"
    )
    parser.add_argument(
        "--cloud-model",
        default="claude-sonnet-4-5-20250929",
        help="Claude model for cloud routing (default: claude-sonnet-4-5-20250929)"
    )
    args = parser.parse_args()

    print()
    print("=" * 40)
    print("  JETT VOICE ASSISTANT")
    print("=" * 40)
    print()

    # Check VRAM
    print("Checking GPU...")
    vram_ok, free_mb = check_vram(verbose=args.debug)
    if not vram_ok and not args.force:
        sys.exit(1)
    if not vram_ok and args.force:
        print("  --force: Starting despite low VRAM (LLM may be slow)")
    print()

    # Check Ollama
    print("Checking Ollama...")
    if not check_ollama():
        sys.exit(1)
    print("Ollama OK")
    print()

    # Import and run pipeline
    from src.voice.pipeline import VoicePipeline

    # Load .env for API keys
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    use_vad = not args.no_vad
    pipeline = VoicePipeline(
        debug=args.debug,
        use_wake_word=not args.no_wake,
        wake_debug=args.wake_debug,
        router_mode=args.router_mode,
        cloud_model=args.cloud_model,
        use_vad=use_vad,
    )

    # Auto-set silence threshold based on detection mode
    if args.silence_threshold is not None:
        pipeline.SILENCE_THRESHOLD = args.silence_threshold
    elif not use_vad:
        pipeline.SILENCE_THRESHOLD = 0.01  # RMS default

    pipeline.SILENCE_DURATION = args.silence_duration

    try:
        pipeline.run()
    except KeyboardInterrupt:
        pass

    print("Goodbye!")


if __name__ == "__main__":
    main()
