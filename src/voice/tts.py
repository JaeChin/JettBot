"""
Text-to-speech module for Jett voice assistant.

Uses Kokoro-82M for fast, lightweight speech synthesis.
- VRAM: ~160-200 MB
- Latency: <300ms regardless of text length
- Sample rate: 24kHz
- License: Apache 2.0

Usage:
    from src.voice.tts import TTS

    tts = TTS()
    tts.load()
    audio = tts.synthesize("Hello, I'm Jett.")
    tts.play(audio)
"""

import os
import sys
import time
from pathlib import Path
from typing import Generator

import numpy as np
import sounddevice as sd
import soundfile as sf


class TTS:
    """Text-to-Speech engine using Kokoro-82M."""

    SAMPLE_RATE = 24000  # Kokoro outputs 24kHz audio

    def __init__(
        self,
        voice: str = "af_heart",
        device: str = "cuda",
        speed: float = 1.0
    ):
        """
        Initialize TTS engine.

        Args:
            voice: Voice preset (default: af_heart - American female)
            device: 'cuda' or 'cpu'
            speed: Speech speed multiplier (1.0 = normal)
        """
        self.voice = voice
        self.device = device
        self.speed = speed
        self.pipeline = None

    def load(self) -> float:
        """
        Load the Kokoro model.

        Returns:
            Load time in seconds.
        """
        # Suppress HuggingFace symlink warnings on Windows
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

        from kokoro import KPipeline

        print(f"Loading Kokoro TTS on {self.device}...")
        start = time.perf_counter()

        self.pipeline = KPipeline(
            lang_code="a",  # American English
            repo_id="hexgrad/Kokoro-82M",
            device=self.device
        )

        elapsed = time.perf_counter() - start
        print(f"TTS loaded in {elapsed:.1f}s")
        return elapsed

    def synthesize(self, text: str) -> np.ndarray:
        """
        Convert text to audio.

        Args:
            text: Text to synthesize

        Returns:
            Audio as numpy array (24kHz, float32)
        """
        if self.pipeline is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        audio_chunks = []
        for result in self.pipeline(text, voice=self.voice, speed=self.speed):
            # Convert torch tensor to numpy
            audio_chunks.append(result.audio.cpu().numpy())

        return np.concatenate(audio_chunks) if audio_chunks else np.array([])

    def synthesize_timed(self, text: str) -> tuple[np.ndarray, float, float]:
        """
        Synthesize with timing info.

        Returns:
            Tuple of (audio, time_to_first_chunk_ms, total_time_ms)
        """
        if self.pipeline is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        start = time.perf_counter()
        first_chunk_time = None
        audio_chunks = []

        for result in self.pipeline(text, voice=self.voice, speed=self.speed):
            if first_chunk_time is None:
                first_chunk_time = (time.perf_counter() - start) * 1000
            audio_chunks.append(result.audio.cpu().numpy())

        total_time = (time.perf_counter() - start) * 1000
        audio = np.concatenate(audio_chunks) if audio_chunks else np.array([])

        return audio, first_chunk_time or 0, total_time

    def stream_sentences(self, text: str) -> Generator[np.ndarray, None, None]:
        """
        Stream audio by sentence for lower latency.

        Splits text on sentence boundaries and yields audio chunks.

        Args:
            text: Text to synthesize

        Yields:
            Audio chunks as numpy arrays
        """
        if self.pipeline is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        for result in self.pipeline(text, voice=self.voice, speed=self.speed):
            yield result.audio.cpu().numpy()

    def play(self, audio: np.ndarray, blocking: bool = True) -> None:
        """
        Play audio through speakers.

        Args:
            audio: Audio data (numpy array)
            blocking: Wait for playback to complete
        """
        sd.play(audio, self.SAMPLE_RATE)
        if blocking:
            sd.wait()

    def synthesize_to_file(self, text: str, path: str) -> float:
        """
        Synthesize and save to WAV file.

        Args:
            text: Text to synthesize
            path: Output file path

        Returns:
            Audio duration in seconds
        """
        audio = self.synthesize(text)
        sf.write(path, audio, self.SAMPLE_RATE)
        return len(audio) / self.SAMPLE_RATE


def main():
    """Interactive test mode."""
    import argparse

    parser = argparse.ArgumentParser(description="Jett TTS Test")
    parser.add_argument("text", nargs="?", default="Hello, I'm Jett. How can I help you today?")
    parser.add_argument("--output", "-o", help="Save to WAV file")
    parser.add_argument("--voice", "-v", default="af_heart", help="Voice preset")
    parser.add_argument("--speed", "-s", type=float, default=1.0, help="Speed multiplier")
    args = parser.parse_args()

    tts = TTS(voice=args.voice, speed=args.speed)
    tts.load()

    print(f"\nSynthesizing: \"{args.text}\"")
    audio, first_chunk_ms, total_ms = tts.synthesize_timed(args.text)

    duration = len(audio) / TTS.SAMPLE_RATE
    print(f"Time to first chunk: {first_chunk_ms:.0f}ms")
    print(f"Total synthesis time: {total_ms:.0f}ms")
    print(f"Audio duration: {duration:.2f}s")

    if args.output:
        sf.write(args.output, audio, TTS.SAMPLE_RATE)
        print(f"Saved to: {args.output}")
    else:
        print("Playing audio...")
        tts.play(audio)

    print("\nCheck VRAM usage: nvidia-smi")


if __name__ == "__main__":
    main()
