"""
Jett STT Module - faster-whisper integration

Speech-to-Text using faster-whisper with INT8 quantization.
Target: <200ms transcription latency, 1.5GB VRAM.

Usage:
    python -m src.voice.stt              # Interactive test
    python -m src.voice.stt test.wav     # Transcribe file
"""

import os
import sys

# Add NVIDIA DLL paths for CUDA support (must be before importing ctranslate2/faster_whisper)
def _setup_cuda_paths():
    """Add NVIDIA library paths for Windows CUDA support."""
    if sys.platform == "win32":
        site_packages = os.path.join(sys.prefix, "Lib", "site-packages")
        nvidia_bins = [
            os.path.join(site_packages, "nvidia", "cudnn", "bin"),
            os.path.join(site_packages, "nvidia", "cublas", "bin"),
        ]
        for path in nvidia_bins:
            if os.path.exists(path) and path not in os.environ.get("PATH", ""):
                os.environ["PATH"] = path + os.pathsep + os.environ.get("PATH", "")

_setup_cuda_paths()

import time
from pathlib import Path

from faster_whisper import WhisperModel


class STT:
    """Speech-to-Text engine using faster-whisper."""

    def __init__(
        self,
        model_size: str = "distil-large-v3",
        device: str = "cuda",
        compute_type: str = "int8"
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None

    def load(self) -> float:
        """
        Load the Whisper model.

        Returns:
            Load time in seconds.
        """
        print(f"Loading {self.model_size} ({self.compute_type}) on {self.device}...")
        start = time.perf_counter()

        self.model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type
        )

        elapsed = time.perf_counter() - start
        print(f"Model loaded in {elapsed:.1f}s")
        return elapsed

    def transcribe(self, audio_path: str) -> tuple[str, float]:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file (wav, mp3, etc.)

        Returns:
            Tuple of (transcribed text, latency in ms)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        start = time.perf_counter()

        segments, info = self.model.transcribe(
            audio_path,
            language="en",  # Force English to skip language detection (faster + avoids errors)
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500}
        )

        # Collect all segments into single string
        text = " ".join(segment.text.strip() for segment in segments)

        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"Transcribed in {elapsed_ms:.0f}ms | Language: {info.language} | Text length: {len(text)} chars")

        return text, elapsed_ms


def main():
    """Interactive test mode."""
    stt = STT()
    stt.load()

    # Check for audio file argument
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        if Path(audio_path).exists():
            text, latency = stt.transcribe(audio_path)
            print(f"\n--- Transcription ---\n{text}\n")
            return
        else:
            print(f"File not found: {audio_path}")

    # Interactive mode
    print("\n" + "="*50)
    print("JETT STT - Interactive Test Mode")
    print("="*50)
    print("\nModel loaded and ready.")
    print("Check VRAM usage: nvidia-smi")
    print("\nTo transcribe, run:")
    print("  python -m src.voice.stt <audio_file.wav>")
    print("\nPress Enter to exit...")
    input()


if __name__ == "__main__":
    main()
