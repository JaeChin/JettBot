"""
Jett Wake Word Detector — openWakeWord Integration

Listens for "Hey Jett" (using the built-in "hey_jarvis" model) and
triggers a callback when detected. Runs on CPU with ~1% usage.

The detector manages its own audio stream (16kHz, mono, 1280-sample chunks)
and runs independently of the main pipeline recording stream.

Usage:
    from src.voice.wake_word import WakeWordDetector

    def on_wake():
        print("Wake word detected!")

    detector = WakeWordDetector()
    detector.start(on_wake)
    # ... later ...
    detector.stop()
"""

import threading
import time
from typing import Callable, Optional

import numpy as np
import sounddevice as sd


class WakeWordDetector:
    """
    Wake word detector using openWakeWord.

    Manages its own audio stream and calls on_wake() when the wake word
    is detected with sufficient confidence.
    """

    # openWakeWord expects 16kHz mono audio in 1280-sample chunks
    SAMPLE_RATE = 16000
    CHANNELS = 1
    CHUNK_SIZE = 1280

    # Detection parameters
    DEFAULT_THRESHOLD = 0.5
    COOLDOWN_SECONDS = 2.0

    def __init__(
        self,
        model_name: str = "hey_jarvis",
        threshold: float = DEFAULT_THRESHOLD,
        debug: bool = False,
    ):
        self.model_name = model_name
        self.threshold = threshold
        self.debug = debug

        self._model = None
        self._stream: Optional[sd.InputStream] = None
        self._on_wake: Optional[Callable] = None
        self._running = False

        # Pause flag — when cleared, audio callback skips prediction
        self._active = threading.Event()
        self._active.set()  # Start active (not paused)

        # Cooldown tracking
        self._last_trigger_time = 0.0

        # Debug: throttle score printing to ~1 per second
        self._last_debug_print = 0.0
        self._debug_print_interval = 1.0
        self._debug_audio_info_printed = False

    def _load_model(self) -> None:
        """Load the openWakeWord model."""
        import openwakeword
        from openwakeword.model import Model

        # Download default models if not present
        openwakeword.utils.download_models()

        self._model = Model(
            wakeword_models=[self.model_name],
            inference_framework="onnx",
        )

        if self.debug:
            print(f"[Wake] Loaded model: {self.model_name}")
            print(f"[Wake] Model keys: {list(self._model.models.keys())}")

    def _audio_callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        """Audio stream callback — feeds chunks to the wake word model."""
        if not self._active.is_set():
            return

        if self._model is None:
            return

        # Convert float32 [-1, 1] to int16 [-32768, 32767] — openWakeWord expects int16
        audio_f32 = indata[:, 0]  # mono
        audio_chunk = (audio_f32 * 32767).astype(np.int16)

        # Debug: print audio format once on first callback
        if self.debug and not self._debug_audio_info_printed:
            self._debug_audio_info_printed = True
            print(f"[Wake] Audio dtype={audio_chunk.dtype}, shape={audio_chunk.shape}, "
                  f"min={audio_chunk.min()}, max={audio_chunk.max()}")

        # Run prediction
        prediction = self._model.predict(audio_chunk)

        # Debug: print all scores periodically (~1/sec)
        if self.debug:
            now = time.monotonic()
            if now - self._last_debug_print >= self._debug_print_interval:
                self._last_debug_print = now
                rms = float(np.sqrt(np.mean(audio_f32 ** 2)))
                scores = ", ".join(f"{k}: {v:.2f}" for k, v in prediction.items())
                print(f"[Wake] {scores}  (rms={rms:.4f})")

        # Check if wake word confidence exceeds threshold
        score = prediction.get(self.model_name, 0.0)

        if score > self.threshold:
            now = time.monotonic()
            if now - self._last_trigger_time < self.COOLDOWN_SECONDS:
                if self.debug:
                    print(f"[Wake] COOLDOWN: {self.model_name} score {score:.2f} > threshold {self.threshold} (ignored)")
                return

            self._last_trigger_time = now

            if self.debug:
                print(f"[Wake] TRIGGERED: {self.model_name} score {score:.2f} > threshold {self.threshold}")

            if self._on_wake:
                self._on_wake()

    def start(self, on_wake: Callable) -> None:
        """
        Start listening for the wake word.

        Args:
            on_wake: Callback invoked when wake word is detected.
        """
        if self._running:
            return

        self._on_wake = on_wake

        if self._model is None:
            self._load_model()

        self._running = True
        self._active.set()

        if self.debug:
            device_info = sd.query_devices(kind="input")
            print(f"[Wake] Audio device: {device_info['name']}")
            print(f"[Wake] Sample rate: {self.SAMPLE_RATE}Hz, Channels: {self.CHANNELS}, Chunk: {self.CHUNK_SIZE}")

        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNELS,
            blocksize=self.CHUNK_SIZE,
            dtype="float32",
            callback=self._audio_callback,
        )
        self._stream.start()

        if self.debug:
            print("[Wake] Stream started, listening...")

    def stop(self) -> None:
        """Stop listening and close the audio stream."""
        if not self._running:
            return

        self._running = False

        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if self.debug:
            print("[WakeWord] Stream stopped")

    def pause(self) -> None:
        """Pause detection (stream stays open but predictions are skipped)."""
        self._active.clear()
        if self.debug:
            print("[WakeWord] Paused")

    def resume(self) -> None:
        """Resume detection after pause."""
        # Reset model state to avoid stale predictions triggering false positives
        if self._model is not None:
            self._model.reset()
        self._active.set()
        if self.debug:
            print("[WakeWord] Resumed")


if __name__ == "__main__":
    # Standalone test — bypasses pipeline to isolate wake word detection
    # Run: python src/voice/wake_word.py
    import openwakeword
    from openwakeword.model import Model

    openwakeword.utils.download_models()
    model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")

    print(f"Model keys: {list(model.models.keys())}")
    print(f"Model outputs: {model.model_outputs}")
    print(f"Model inputs: {model.model_inputs}")

    device_info = sd.query_devices(kind="input")
    print(f"Audio device: {device_info['name']}")
    print()

    frame_count = 0
    last_print = 0.0

    def callback(indata, frames, time_info, status):
        global frame_count, last_print
        frame_count += 1
        audio_f32 = indata[:, 0]
        # Convert to int16 — openWakeWord expects int16 audio
        audio_int16 = (audio_f32 * 32767).astype(np.int16)

        prediction = model.predict(audio_int16)
        score = prediction.get("hey_jarvis", 0)
        rms = float(np.sqrt(np.mean(audio_f32 ** 2)))

        # Print every second OR when score is non-zero
        now = time.monotonic()
        if score > 0.001 or now - last_print >= 1.0:
            last_print = now
            buf_len = len(model.prediction_buffer.get("hey_jarvis", []))
            buf_last3 = list(model.prediction_buffer.get("hey_jarvis", []))[-3:]
            buf_str = ", ".join(f"{v:.4f}" for v in buf_last3)
            marker = " <<<" if score > 0.5 else ""
            print(f"  frame={frame_count:>5}  hey_jarvis={score:.4f}  "
                  f"rms={rms:.4f}  buf[{buf_len}]=[{buf_str}]{marker}")

    print("Listening... say 'Hey Jarvis'. Ctrl+C to stop.")
    print("Prints every 1s, or immediately when score > 0.001")
    print("-" * 65)
    with sd.InputStream(samplerate=16000, channels=1, blocksize=1280,
                        dtype="float32", callback=callback):
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nDone.")
