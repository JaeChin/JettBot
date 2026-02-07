"""
Jett Startup Script — VRAM-Aware Launcher

Checks GPU memory before loading models to prevent partial CPU offload
(which causes 9-16s LLM latency instead of <3s).

Usage:
    python scripts/start_jett.py           # Normal start
    python scripts/start_jett.py --force   # Skip VRAM check
    python scripts/start_jett.py --debug   # Debug output
    python scripts/start_jett.py --check   # Check VRAM only, don't start

Requirements:
    - RTX 3070 (8 GB VRAM)
    - Close browsers, Discord, and other GPU-heavy apps first
    - Ollama running with jett-qwen3 model
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Jett models need ~6.8 GB to load fully on GPU.
# If less is free, the LLM gets partially offloaded to CPU → 5-10x slower.
VRAM_REQUIRED_MB = 6800
VRAM_WARNING_MB = 7200  # Warn if headroom is slim

# Known GPU-heavy processes to flag (lowercase exe names)
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


def get_gpu_memory() -> tuple[int, int, int]:
    """
    Query GPU memory via nvidia-smi.

    Returns:
        (used_mb, total_mb, free_mb)
    """
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
        print(f"ERROR: nvidia-smi failed: {result.stderr.strip()}")
        sys.exit(1)

    parts = result.stdout.strip().split(",")
    return int(parts[0].strip()), int(parts[1].strip()), int(parts[2].strip())


def get_gpu_processes() -> list[dict]:
    """
    Get list of processes using the GPU.

    Returns:
        List of dicts with 'pid', 'name' keys.
    """
    result = subprocess.run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,name",
            "--format=csv,noheader",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    processes = []
    seen_pids = set()
    for line in result.stdout.strip().split("\n"):
        if not line.strip() or "Insufficient Permissions" in line:
            continue
        parts = line.split(",", 1)
        if len(parts) == 2:
            pid = parts[0].strip()
            name = parts[1].strip()
            if pid not in seen_pids:
                seen_pids.add(pid)
                processes.append({"pid": pid, "name": name})

    return processes


def check_vram(verbose: bool = False) -> tuple[bool, int]:
    """
    Check if there's enough free VRAM to run Jett.

    Returns:
        (ok, free_mb)
    """
    used_mb, total_mb, free_mb = get_gpu_memory()
    processes = get_gpu_processes()

    print()
    print("=" * 50)
    print("  JETT VRAM CHECK")
    print("=" * 50)
    print()
    print(f"  GPU Memory: {used_mb} MB used / {total_mb} MB total")
    print(f"  Free:       {free_mb} MB")
    print(f"  Required:   {VRAM_REQUIRED_MB} MB (for STT + LLM + TTS)")
    print()

    # Identify heavy processes
    heavy_found = []
    for proc in processes:
        exe_name = Path(proc["name"]).name.lower()
        for pattern, description in GPU_HEAVY_PROCESSES.items():
            if pattern in exe_name:
                heavy_found.append(description)

    if heavy_found or verbose:
        print(f"  GPU Processes ({len(processes)} total):")
        if verbose:
            for proc in processes:
                exe = Path(proc["name"]).name
                print(f"    PID {proc['pid']:>6}  {exe}")
        if heavy_found:
            print()
            print("  ** GPU-heavy apps detected: **")
            for desc in sorted(set(heavy_found)):
                print(f"    - {desc}")
        print()

    # Evaluate
    if free_mb >= VRAM_WARNING_MB:
        print(f"  Status: OK ({free_mb} MB free >= {VRAM_WARNING_MB} MB)")
        print()
        return True, free_mb
    elif free_mb >= VRAM_REQUIRED_MB:
        print(f"  Status: WARNING - Tight headroom ({free_mb} MB free)")
        if heavy_found:
            print("  Tip: Close the GPU-heavy apps listed above for best performance.")
        print()
        return True, free_mb
    else:
        deficit = VRAM_REQUIRED_MB - free_mb
        print(f"  Status: INSUFFICIENT VRAM ({free_mb} MB free < {VRAM_REQUIRED_MB} MB needed)")
        print(f"  Need to free ~{deficit} MB.")
        print()
        if heavy_found:
            print("  Close these apps to free VRAM:")
            for desc in sorted(set(heavy_found)):
                print(f"    - {desc}")
        else:
            print("  Close GPU-heavy apps (browsers, Discord, etc.)")
        print()
        print("  Or run with --force to attempt loading anyway (may be slow).")
        print()
        return False, free_mb


def main():
    parser = argparse.ArgumentParser(
        description="Jett Voice Assistant — VRAM-aware launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--force", action="store_true", help="Skip VRAM check")
    parser.add_argument("--check", action="store_true", help="Check VRAM only, don't start")
    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug output")
    parser.add_argument(
        "--silence-threshold",
        type=float,
        default=0.01,
        help="RMS threshold for silence detection (default: 0.01)",
    )
    parser.add_argument(
        "--silence-duration",
        type=float,
        default=1.0,
        help="Seconds of silence to end recording (default: 1.0)",
    )
    args = parser.parse_args()

    # Step 1: VRAM check
    ok, free_mb = check_vram(verbose=args.debug)

    if args.check:
        sys.exit(0 if ok else 1)

    if not ok and not args.force:
        sys.exit(1)

    if not ok and args.force:
        print("  --force: Proceeding despite insufficient VRAM (expect slow LLM).")
        print()

    # Step 2: Check Ollama
    print("Checking Ollama...")
    # Import here to avoid import overhead on --check
    import requests

    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = resp.json().get("models", [])
        model_names = [m.get("name", "") for m in models]

        if not any("jett-qwen3" in name for name in model_names):
            print("ERROR: jett-qwen3 model not found in Ollama.")
            print("Run: ollama create jett-qwen3 -f models/Modelfile.jett-qwen3")
            sys.exit(1)
        print("Ollama OK")
    except requests.exceptions.ConnectionError:
        print("ERROR: Ollama is not running. Start it first: ollama serve")
        sys.exit(1)

    # Step 3: Load and run pipeline
    print()
    print("=" * 50)
    print("  JETT VOICE ASSISTANT")
    print("=" * 50)
    print()

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
