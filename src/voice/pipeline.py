"""
Jett Voice Pipeline - End-to-End STT → LLM → TTS

This module wires together the complete voice interaction loop:
1. Listen for audio from microphone
2. Detect end of speech (simple silence detection)
3. Transcribe with faster-whisper
4. Generate response with Ollama (jett-qwen3)
5. Synthesize and play audio with Kokoro

Usage:
    from src.voice.pipeline import VoicePipeline

    pipeline = VoicePipeline()
    pipeline.run()  # Blocking loop
"""

import io
import os
import queue
import re
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional

import numpy as np
import requests
import sounddevice as sd
import soundfile as sf

# Suppress warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


@dataclass
class PipelineMetrics:
    """Timing metrics for a single interaction."""
    stt_ms: float = 0.0
    llm_first_token_ms: float = 0.0
    tts_first_audio_ms: float = 0.0
    e2e_ms: float = 0.0
    user_text: str = ""
    jett_text: str = ""


class VoicePipeline:
    """
    End-to-end voice assistant pipeline.

    Listens for speech, transcribes, generates response, and speaks back.
    """

    # Audio recording parameters
    SAMPLE_RATE = 16000  # Whisper expects 16kHz
    CHANNELS = 1
    BLOCK_SIZE = 1024

    # Silence detection parameters
    SILENCE_THRESHOLD = 0.01  # RMS threshold for silence
    SILENCE_DURATION = 1.0    # Seconds of silence to end recording
    MAX_RECORD_SECONDS = 30   # Maximum recording length

    # TTS sample rate
    TTS_SAMPLE_RATE = 24000

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "jett-qwen3",
        stt_model: str = "distil-large-v3",
        tts_voice: str = "af_heart",
        debug: bool = False
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.stt_model = stt_model
        self.tts_voice = tts_voice
        self.debug = debug

        self.stt = None
        self.tts = None
        self._running = False
        self._audio_queue = queue.Queue()

    def load_models(self) -> None:
        """Load STT and TTS models."""
        print("Loading models...")

        # Load STT
        from src.voice.stt import STT
        self.stt = STT(model_size=self.stt_model, device="cuda", compute_type="int8")
        self.stt.load()

        # Load TTS
        from src.voice.tts import TTS
        self.tts = TTS(voice=self.tts_voice, device="cuda")
        self.tts.load()

        # Warm up TTS (first call is slow due to CUDA JIT)
        print("Warming up TTS...")
        _ = self.tts.synthesize("Ready.")

        print("Models loaded and ready.")

    def _calculate_rms(self, audio: np.ndarray) -> float:
        """Calculate RMS (volume level) of audio."""
        return float(np.sqrt(np.mean(audio ** 2)))

    def record_audio(self) -> Optional[np.ndarray]:
        """
        Record audio from microphone until silence is detected.

        Returns:
            Audio as numpy array, or None if no speech detected.
        """
        print("Listening...", end="", flush=True)

        audio_chunks = []
        silence_chunks = 0
        chunks_per_second = self.SAMPLE_RATE / self.BLOCK_SIZE
        silence_chunks_needed = int(self.SILENCE_DURATION * chunks_per_second)
        max_chunks = int(self.MAX_RECORD_SECONDS * chunks_per_second)

        has_speech = False

        def audio_callback(indata, frames, time_info, status):
            self._audio_queue.put(indata.copy())

        with sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            blocksize=self.BLOCK_SIZE,
            callback=audio_callback
        ):
            chunk_count = 0
            while chunk_count < max_chunks:
                try:
                    chunk = self._audio_queue.get(timeout=0.5)
                    audio_chunks.append(chunk)
                    chunk_count += 1

                    rms = self._calculate_rms(chunk)

                    if rms > self.SILENCE_THRESHOLD:
                        has_speech = True
                        silence_chunks = 0
                        if self.debug:
                            print(".", end="", flush=True)
                    else:
                        silence_chunks += 1

                    # End recording after enough silence (only if we've heard speech)
                    if has_speech and silence_chunks >= silence_chunks_needed:
                        break

                except queue.Empty:
                    continue

        print()  # New line after "Listening..."

        if not has_speech or len(audio_chunks) < 5:
            return None

        return np.concatenate(audio_chunks).flatten()

    def transcribe(self, audio: np.ndarray) -> tuple[str, float]:
        """
        Transcribe audio to text.

        Returns:
            Tuple of (text, latency_ms)
        """
        # Save to temp file (faster-whisper needs file path)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            sf.write(f.name, audio, self.SAMPLE_RATE)
            temp_path = f.name

        try:
            text, latency_ms = self.stt.transcribe(temp_path)
            return text.strip(), latency_ms
        finally:
            os.unlink(temp_path)

    def generate_response(self, prompt: str) -> Generator[str, None, None]:
        """
        Generate LLM response, streaming tokens.

        Yields:
            Response text chunks.
        """
        # Add /no_think suffix to disable Qwen3's thinking mode for faster responses
        prompt_with_no_think = f"{prompt} /no_think"

        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt_with_no_think,
                "stream": True
            },
            stream=True,
            timeout=60
        )

        in_think_block = False
        for line in response.iter_lines():
            if line:
                import json
                data = json.loads(line)
                if "response" in data:
                    chunk = data["response"]

                    # Filter out <think> blocks from Qwen3
                    if "<think>" in chunk:
                        in_think_block = True
                    if in_think_block:
                        if "</think>" in chunk:
                            in_think_block = False
                            # Get text after </think>
                            chunk = chunk.split("</think>", 1)[-1]
                        else:
                            continue  # Skip this chunk entirely

                    if chunk:
                        yield chunk
                if data.get("done", False):
                    break

    def split_sentences(self, text: str) -> list[str]:
        """Split text into sentences for TTS."""
        # Split on sentence endings, keeping the punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def speak_streaming(self, text_generator: Generator[str, None, None]) -> tuple[str, float, float]:
        """
        Synthesize and play speech as text streams in.

        Returns:
            Tuple of (full_text, first_token_ms, first_audio_ms)
        """
        buffer = ""
        full_text = ""
        first_token_time = None
        first_audio_time = None
        start_time = time.perf_counter()

        # Queue for audio chunks to play
        audio_queue = queue.Queue()
        playback_done = threading.Event()

        def playback_worker():
            """Play audio chunks from queue."""
            while True:
                item = audio_queue.get()
                if item is None:  # Sentinel to stop
                    break
                sd.play(item, self.TTS_SAMPLE_RATE)
                sd.wait()
            playback_done.set()

        # Start playback thread
        playback_thread = threading.Thread(target=playback_worker, daemon=True)
        playback_thread.start()

        try:
            for chunk in text_generator:
                if first_token_time is None:
                    first_token_time = (time.perf_counter() - start_time) * 1000

                buffer += chunk
                full_text += chunk

                # Check if we have a complete sentence
                sentences = self.split_sentences(buffer)
                if len(sentences) > 1:
                    # Synthesize all complete sentences
                    for sentence in sentences[:-1]:
                        if sentence:
                            audio = self.tts.synthesize(sentence)
                            if first_audio_time is None:
                                first_audio_time = (time.perf_counter() - start_time) * 1000
                            audio_queue.put(audio)

                    # Keep incomplete sentence in buffer
                    buffer = sentences[-1]

            # Synthesize any remaining text
            if buffer.strip():
                audio = self.tts.synthesize(buffer.strip())
                if first_audio_time is None:
                    first_audio_time = (time.perf_counter() - start_time) * 1000
                audio_queue.put(audio)

        finally:
            # Signal playback to stop and wait
            audio_queue.put(None)
            playback_done.wait(timeout=30)

        return (
            full_text.strip(),
            first_token_time or 0,
            first_audio_time or 0
        )

    def process_query(self, audio: np.ndarray) -> PipelineMetrics:
        """
        Process a single voice query through the full pipeline.

        Returns:
            PipelineMetrics with timing and text data.
        """
        metrics = PipelineMetrics()
        e2e_start = time.perf_counter()

        # STT
        stt_start = time.perf_counter()
        user_text, _ = self.transcribe(audio)
        metrics.stt_ms = (time.perf_counter() - stt_start) * 1000
        metrics.user_text = user_text

        if not user_text:
            return metrics

        # LLM + TTS (streaming)
        llm_start = time.perf_counter()
        response_generator = self.generate_response(user_text)

        jett_text, first_token_ms, first_audio_ms = self.speak_streaming(response_generator)

        metrics.llm_first_token_ms = first_token_ms
        metrics.tts_first_audio_ms = first_audio_ms - first_token_ms if first_audio_ms > first_token_ms else first_audio_ms
        metrics.jett_text = jett_text
        metrics.e2e_ms = (time.perf_counter() - e2e_start) * 1000

        return metrics

    def print_metrics(self, metrics: PipelineMetrics) -> None:
        """Print interaction metrics."""
        print()
        print("--- Jett Pipeline ---")
        print(f"  STT:          {metrics.stt_ms:.0f}ms")
        print(f"  LLM (first):  {metrics.llm_first_token_ms:.0f}ms")
        print(f"  TTS (first):  {metrics.tts_first_audio_ms:.0f}ms")
        print(f"  E2E:          {metrics.e2e_ms:.0f}ms")
        print(f"  User said:    \"{metrics.user_text}\"")
        print(f"  Jett said:    \"{metrics.jett_text[:100]}{'...' if len(metrics.jett_text) > 100 else ''}\"")
        print("---------------------")
        print()

    def run(self) -> None:
        """Run the voice pipeline in a loop."""
        if self.stt is None or self.tts is None:
            self.load_models()

        self._running = True
        print("\nJett is listening... (Ctrl+C to exit)\n")

        try:
            while self._running:
                # Record audio
                audio = self.record_audio()

                if audio is None:
                    continue

                # Process through pipeline
                try:
                    metrics = self.process_query(audio)

                    if metrics.user_text:
                        self.print_metrics(metrics)
                    else:
                        print("(No speech detected)")

                except Exception as e:
                    print(f"Error processing query: {e}")
                    if self.debug:
                        import traceback
                        traceback.print_exc()
                    continue

        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self._running = False

    def process_file(self, audio_path: str) -> PipelineMetrics:
        """
        Process a pre-recorded audio file through the pipeline.

        Useful for benchmarking without live mic input.
        """
        if self.stt is None or self.tts is None:
            self.load_models()

        # Load audio file
        audio, sr = sf.read(audio_path)

        # Resample if needed
        if sr != self.SAMPLE_RATE:
            import scipy.signal
            audio = scipy.signal.resample(
                audio,
                int(len(audio) * self.SAMPLE_RATE / sr)
            )

        # Ensure mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        return self.process_query(audio.astype(np.float32))


def main():
    """Test the pipeline interactively."""
    pipeline = VoicePipeline(debug=True)
    pipeline.run()


if __name__ == "__main__":
    main()
