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
import json
import os
import queue
import re
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Generator, Optional

import numpy as np
import requests
import sounddevice as sd
import soundfile as sf

# Suppress warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


class PipelineState(Enum):
    """State machine for voice pipeline to prevent feedback loops."""
    WAITING = auto()      # Wake word detection active (low power)
    LISTENING = auto()    # Recording from mic, waiting for speech
    PROCESSING = auto()   # STT + LLM generation (mic ignored)
    SPEAKING = auto()     # TTS playback (mic ignored)


@dataclass
class PipelineMetrics:
    """Timing metrics for a single interaction."""
    stt_ms: float = 0.0
    llm_first_token_ms: float = 0.0
    llm_total_ms: float = 0.0
    tts_first_audio_ms: float = 0.0
    tts_total_ms: float = 0.0
    playback_ms: float = 0.0
    e2e_ms: float = 0.0
    token_count: int = 0
    user_text: str = ""
    jett_text: str = ""
    llm_backend: str = "local"


class VoicePipeline:
    """
    End-to-end voice assistant pipeline.

    Listens for speech, transcribes, generates response, and speaks back.
    """

    # Audio recording parameters
    SAMPLE_RATE = 16000  # Whisper expects 16kHz
    CHANNELS = 1
    BLOCK_SIZE = 1024

    # Silence detection parameters (optimized for low latency)
    SILENCE_THRESHOLD = 0.005  # RMS threshold for silence (lowered for quiet mics)
    SILENCE_DURATION = 0.5     # Seconds of silence to end recording
    MAX_RECORD_SECONDS = 30    # Maximum recording length

    # TTS sample rate
    TTS_SAMPLE_RATE = 24000

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "jett-qwen3",
        stt_model: str = "distil-large-v3",
        tts_voice: str = "af_heart",
        debug: bool = False,
        use_wake_word: bool = True,
        wake_debug: bool = False,
        router_mode: str = "local",
        cloud_model: str = "claude-sonnet-4-5-20250929",
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.stt_model = stt_model
        self.tts_voice = tts_voice
        self.debug = debug
        self.use_wake_word = use_wake_word
        self.wake_debug = wake_debug
        self.router_mode = router_mode
        self.cloud_model = cloud_model

        self.stt = None
        self.tts = None
        self._running = False
        self._audio_queue = queue.Queue()
        self._state = PipelineState.LISTENING
        self._router = None
        self._cloud_llm = None

        # Wake word
        self.wake_word_detector = None
        self._wake_event = threading.Event()

    def _init_wake_word(self) -> None:
        """Initialize the wake word detector."""
        from src.voice.wake_word import WakeWordDetector

        print("Loading wake word model...")
        self.wake_word_detector = WakeWordDetector(
            debug=self.wake_debug or self.debug,
        )
        # Eagerly load the model so startup latency is paid upfront
        self.wake_word_detector._load_model()
        print("Wake word model loaded.")

    def _on_wake_detected(self) -> None:
        """Callback invoked by WakeWordDetector when wake word is heard."""
        self._wake_event.set()

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

        # Warm up LLM (load into VRAM if not already)
        print("Warming up LLM...")
        try:
            requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream": False,
                    "keep_alive": -1,  # Keep model loaded indefinitely
                    "options": {"num_predict": 5}  # Limit output for warmup
                },
                timeout=120
            )
        except Exception as e:
            print(f"LLM warmup warning: {e}")

        # Initialize router
        self._init_router()

        print("Models loaded and ready.")

    def _init_router(self) -> None:
        """Initialize the hybrid LLM router."""
        from src.llm.router import QueryRouter
        from src.llm.cloud import CloudLLM

        if self.router_mode in ("cloud", "hybrid"):
            self._cloud_llm = CloudLLM(model=self.cloud_model)
            if not self._cloud_llm.available:
                if self.router_mode == "cloud":
                    print("WARNING: Cloud mode selected but ANTHROPIC_API_KEY not set.")
                    print("  Set it in .env or as an environment variable.")
                    print("  Falling back to local mode.")
                    self.router_mode = "local"
                else:
                    print("Note: ANTHROPIC_API_KEY not set — hybrid mode will use local only.")

        cloud_fn = self._stream_cloud if self._cloud_llm and self._cloud_llm.available else None
        self._router = QueryRouter(
            mode=self.router_mode,
            local_fn=self._stream_local,
            cloud_fn=cloud_fn,
        )

        mode_label = {
            "local": "Local only (Ollama)",
            "cloud": "Cloud only (Claude API)",
            "hybrid": "Hybrid (local + cloud)",
        }
        print(f"Router: {mode_label.get(self.router_mode, self.router_mode)}")

    def _stream_local(self, prompt: str) -> Generator[str, None, None]:
        """Stream response from local Ollama/Qwen3."""
        response = requests.post(
            f"{self.ollama_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": True,
                "keep_alive": -1,
                "think": False,
                "options": {
                    "num_predict": 80,
                }
            },
            stream=True,
            timeout=60
        )

        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if "message" in data and "content" in data["message"]:
                    chunk = data["message"]["content"]
                    if chunk:
                        yield chunk
                if data.get("done", False):
                    break

    def _stream_cloud(self, prompt: str) -> Generator[str, None, None]:
        """Stream response from Claude API."""
        yield from self._cloud_llm.stream(prompt)

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

    def generate_response(self, prompt: str) -> tuple[Generator[str, None, None], str]:
        """
        Route and generate LLM response, streaming tokens.

        Returns:
            Tuple of (token generator, backend name).
            Backend is "local" or "cloud".
        """
        from src.llm.router import classify

        if self._router is None:
            # Fallback if router not initialized
            return self._stream_local(prompt), "local"

        backend = self._router._decide(prompt)

        if self.debug:
            info = self._router.explain(prompt)
            print(f"  [Router] → {backend} (signals: {info['cloud_signals'][:2]})")

        return self._router.route(prompt), backend

    def split_sentences(self, text: str) -> list[str]:
        """Split text into sentences for TTS."""
        # Split on sentence endings, keeping the punctuation
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def speak_streaming(self, text_generator: Generator[str, None, None]) -> dict:
        """
        Synthesize and play speech as text streams in.

        Optimized for low latency:
        - Starts TTS as soon as we have a sentence ending OR enough chars
        - Synthesizes in parallel with LLM generation

        Returns:
            Dict with full_text, first_token_ms, first_audio_ms,
            llm_total_ms, tts_total_ms, playback_ms, token_count.
        """
        buffer = ""
        full_text = ""
        first_token_time = None
        first_audio_time = None
        start_time = time.perf_counter()
        tts_total_ms = 0.0
        token_count = 0

        # Minimum chars before first synthesis (for fast first audio)
        MIN_FIRST_CHUNK = 20

        # Queue for audio chunks to play
        audio_queue = queue.Queue()
        playback_done = threading.Event()
        playback_total_ms = 0.0

        def playback_worker():
            nonlocal playback_total_ms
            """Play audio chunks from queue. Sets state to SPEAKING during playback."""
            while True:
                item = audio_queue.get()
                if item is None:  # Sentinel to stop
                    break
                # Set state to SPEAKING to mute mic during playback
                self._state = PipelineState.SPEAKING
                play_start = time.perf_counter()
                sd.play(item, self.TTS_SAMPLE_RATE)
                sd.wait()
                playback_total_ms += (time.perf_counter() - play_start) * 1000
            playback_done.set()

        # Start playback thread
        playback_thread = threading.Thread(target=playback_worker, daemon=True)
        playback_thread.start()

        first_chunk_sent = False
        llm_done_time = None

        def _synthesize_chunk(text_to_speak: str):
            nonlocal first_audio_time, tts_total_ms, first_chunk_sent
            tts_start = time.perf_counter()
            audio = self.tts.synthesize(text_to_speak)
            tts_total_ms += (time.perf_counter() - tts_start) * 1000
            if first_audio_time is None:
                first_audio_time = (time.perf_counter() - start_time) * 1000
            audio_queue.put(audio)
            first_chunk_sent = True

        try:
            for chunk in text_generator:
                token_count += 1
                if first_token_time is None:
                    first_token_time = (time.perf_counter() - start_time) * 1000

                buffer += chunk
                full_text += chunk

                # Check for sentence endings
                if re.search(r'[.!?]\s*$', buffer):
                    if buffer.strip():
                        _synthesize_chunk(buffer.strip())
                    buffer = ""

                # For first chunk, also trigger on comma or enough chars
                elif not first_chunk_sent and len(buffer) >= MIN_FIRST_CHUNK:
                    if ',' in buffer or len(buffer) >= 40:
                        split_idx = buffer.rfind(',')
                        if split_idx == -1 or split_idx < 10:
                            split_idx = len(buffer)

                        chunk_to_speak = buffer[:split_idx].strip()
                        if chunk_to_speak:
                            _synthesize_chunk(chunk_to_speak)
                            buffer = buffer[split_idx:].lstrip(',').strip()

            llm_done_time = (time.perf_counter() - start_time) * 1000

            # Synthesize any remaining text
            if buffer.strip():
                _synthesize_chunk(buffer.strip())

        finally:
            # Signal playback to stop and wait
            audio_queue.put(None)
            playback_done.wait(timeout=30)

        return {
            "full_text": full_text.strip(),
            "first_token_ms": first_token_time or 0,
            "first_audio_ms": first_audio_time or 0,
            "llm_total_ms": llm_done_time or 0,
            "tts_total_ms": tts_total_ms,
            "playback_ms": playback_total_ms,
            "token_count": token_count,
        }

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
        response_generator, backend = self.generate_response(user_text)
        metrics.llm_backend = backend
        result = self.speak_streaming(response_generator)

        metrics.llm_first_token_ms = result["first_token_ms"]
        metrics.llm_total_ms = result["llm_total_ms"]
        metrics.tts_first_audio_ms = result["first_audio_ms"] - result["first_token_ms"] if result["first_audio_ms"] > result["first_token_ms"] else result["first_audio_ms"]
        metrics.tts_total_ms = result["tts_total_ms"]
        metrics.playback_ms = result["playback_ms"]
        metrics.token_count = result["token_count"]
        metrics.jett_text = result["full_text"]
        metrics.e2e_ms = (time.perf_counter() - e2e_start) * 1000

        return metrics

    def print_metrics(self, metrics: PipelineMetrics) -> None:
        """Print interaction metrics with full component breakdown."""
        print()
        print("--- Jett Pipeline ---")
        backend_label = "local" if metrics.llm_backend == "local" else "cloud"
        print(f"  LLM backend:    {backend_label}")
        print(f"  STT:            {metrics.stt_ms:>6.0f}ms")
        print(f"  LLM first tok:  {metrics.llm_first_token_ms:>6.0f}ms")
        print(f"  LLM total:      {metrics.llm_total_ms:>6.0f}ms  ({metrics.token_count} tokens)")
        print(f"  TTS first:      {metrics.tts_first_audio_ms:>6.0f}ms")
        print(f"  TTS total:      {metrics.tts_total_ms:>6.0f}ms")
        print(f"  Playback:       {metrics.playback_ms:>6.0f}ms")
        print(f"  E2E:            {metrics.e2e_ms:>6.0f}ms")
        print(f"  User: \"{metrics.user_text}\"")
        print(f"  Jett: \"{metrics.jett_text[:120]}{'...' if len(metrics.jett_text) > 120 else ''}\"")
        print("---------------------")
        print()

    def run(self) -> None:
        """
        Run the voice pipeline in a loop.

        With wake word (default):
          WAITING → (wake detected) → LISTENING → PROCESSING → SPEAKING → WAITING

        Without wake word (--no-wake):
          LISTENING → PROCESSING → SPEAKING → LISTENING

        Mic input is only recorded during LISTENING state.
        """
        if self.stt is None or self.tts is None:
            self.load_models()

        self._running = True

        # Initialize wake word if enabled
        if self.use_wake_word:
            self._init_wake_word()
            self.wake_word_detector.start(self._on_wake_detected)
            self._state = PipelineState.WAITING
            print("\nWaiting for wake word... (say \"Hey Jarvis\", Ctrl+C to exit)\n")
        else:
            self._state = PipelineState.LISTENING
            print("\nJett is listening... (Ctrl+C to exit)\n")

        try:
            while self._running:
                # Wake word mode: wait for trigger
                if self._state == PipelineState.WAITING:
                    # Block with timeout so KeyboardInterrupt can fire
                    if self._wake_event.wait(timeout=0.5):
                        self._wake_event.clear()
                        # Pause wake word detection during interaction
                        self.wake_word_detector.pause()
                        self._state = PipelineState.LISTENING
                        print("Wake word detected! Listening...")
                        if self.debug:
                            print("[State: LISTENING]")
                    continue

                # Only record when in LISTENING state
                if self._state != PipelineState.LISTENING:
                    time.sleep(0.1)
                    continue

                # Record audio
                audio = self.record_audio()

                if audio is None:
                    # No speech — return to appropriate state
                    if self.use_wake_word:
                        self.wake_word_detector.resume()
                        self._state = PipelineState.WAITING
                        print("Waiting for wake word...")
                        if self.debug:
                            print("[State: WAITING]")
                    continue

                # Transition to PROCESSING (mic now ignored)
                self._state = PipelineState.PROCESSING
                if self.debug:
                    print("[State: PROCESSING]")

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

                finally:
                    if self.use_wake_word:
                        # Resume wake word detection, return to WAITING
                        self.wake_word_detector.resume()
                        self._state = PipelineState.WAITING
                        print("\nWaiting for wake word...")
                        if self.debug:
                            print("[State: WAITING]")
                    else:
                        self._state = PipelineState.LISTENING
                        if self.debug:
                            print("[State: LISTENING]")

        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self._running = False
            if self.wake_word_detector is not None:
                self.wake_word_detector.stop()

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
