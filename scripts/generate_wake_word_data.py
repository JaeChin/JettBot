#!/usr/bin/env python
"""
Generate synthetic training data for custom "Hey Jett" wake word.

Uses Kokoro TTS (local GPU) and edge-tts (Microsoft Azure free API) to
produce diverse voice samples for openWakeWord fine-tuning.

Prerequisites:
    pip install edge-tts
    ffmpeg must be in PATH  (winget install Gyan.FFmpeg)

Usage:
    python scripts/generate_wake_word_data.py

Output:
    data/wake_word/positive/   — "Hey Jett" clips (500+)
    data/wake_word/negative/   — Similar-sounding phrases (200+)
    data/wake_word/manifest.csv
"""

import asyncio
import csv
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample as scipy_resample


# ─── Configuration ───────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "data" / "wake_word"
POSITIVE_DIR = OUTPUT_DIR / "positive"
NEGATIVE_DIR = OUTPUT_DIR / "negative"
MANIFEST_PATH = OUTPUT_DIR / "manifest.csv"

TARGET_SR = 16000       # openWakeWord expects 16kHz mono
KOKORO_SR = 24000       # Kokoro outputs 24kHz


# ─── Voices ──────────────────────────────────────────────────────────────────

# Kokoro voices: (lang_code, voice_id)
# Using all available English voices for maximum diversity
KOKORO_VOICES = [
    # American English — female
    ("a", "af_heart"), ("a", "af_bella"), ("a", "af_nicole"),
    ("a", "af_aoede"), ("a", "af_kore"), ("a", "af_sarah"),
    ("a", "af_alloy"), ("a", "af_nova"), ("a", "af_sky"),
    ("a", "af_jessica"), ("a", "af_river"),
    # American English — male
    ("a", "am_fenrir"), ("a", "am_michael"), ("a", "am_puck"),
    ("a", "am_echo"), ("a", "am_eric"), ("a", "am_liam"),
    ("a", "am_onyx"), ("a", "am_santa"), ("a", "am_adam"),
    # British English — female
    ("b", "bf_emma"), ("b", "bf_isabella"), ("b", "bf_alice"), ("b", "bf_lily"),
    # British English — male
    ("b", "bm_fable"), ("b", "bm_george"), ("b", "bm_lewis"), ("b", "bm_daniel"),
]

# edge-tts: diverse English accents (male + female, US/UK/AU/IN/IE/CA/SG/NZ/ZA/KE)
EDGE_VOICES = [
    "en-US-GuyNeural", "en-US-JennyNeural", "en-US-AriaNeural",
    "en-US-DavisNeural", "en-US-JaneNeural", "en-US-JasonNeural",
    "en-GB-SoniaNeural", "en-GB-RyanNeural",
    "en-AU-NatashaNeural", "en-AU-WilliamNeural",
    "en-IN-NeerjaNeural", "en-IN-PrabhatNeural",
    "en-IE-EmilyNeural", "en-IE-ConnorNeural",
    "en-CA-ClaraNeural", "en-CA-LiamNeural",
    "en-SG-LunaNeural", "en-NZ-MitchellNeural",
    "en-ZA-LeahNeural", "en-KE-AsiliaNeural",
]


# ─── Phrases ─────────────────────────────────────────────────────────────────

# Positive: the wake word with different prosody via punctuation
POSITIVE_PHRASES = [
    "Hey Jett",
    "Hey Jett.",
    "Hey, Jett!",
    "Hey Jett?",
]

# Negative: phonetically similar phrases that must NOT trigger
NEGATIVE_PHRASES = [
    "Hey Jeff", "Hey Jet", "Hey yet", "Hey Jed", "Hey Jack",
    "Hey there", "Hey check", "Get set", "Hey pet",
    "Jett", "Get it", "Forget", "Hey Brett", "Hey Bett", "Let's get",
]


# ─── Variation Configs ───────────────────────────────────────────────────────

# Kokoro: (label, speed, pitch_factor)
# pitch_factor >1.0 = higher pitch via resampling trick, <1.0 = lower
KOKORO_POS_VARIATIONS = [
    ("normal",     1.0,  1.0),
    ("fast",       1.15, 1.0),
    ("slow",       0.87, 1.0),
    ("pitch_up",   1.0,  1.05),
    ("pitch_down", 1.0,  0.95),
]

# edge-tts rate adjustments
EDGE_POS_RATES = [
    ("normal", "+0%"),
    ("fast",   "+12%"),
    ("slow",   "-12%"),
]


# ─── Audio Utilities ─────────────────────────────────────────────────────────

def resample_audio(audio, src_sr, target_sr, pitch_factor=1.0):
    """Resample audio to target_sr. pitch_factor != 1.0 shifts pitch."""
    effective_sr = src_sr * pitch_factor
    if effective_sr == target_sr:
        return audio
    n = int(len(audio) * target_sr / effective_sr)
    return scipy_resample(audio, n) if n > 0 else audio


def trim_silence(audio, threshold=0.01, pad=800):
    """Trim leading/trailing silence, keeping `pad` samples of padding."""
    mask = np.abs(audio) > threshold
    if not mask.any():
        return audio
    idx = np.where(mask)[0]
    lo = max(0, idx[0] - pad)
    hi = min(len(audio), idx[-1] + pad)
    return audio[lo:hi]


def save_wav(audio, path, sr=TARGET_SR):
    """Save as 16kHz mono 16-bit PCM WAV. Returns duration in seconds."""
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.95
    audio_i16 = (audio * 32767).astype(np.int16)
    sf.write(str(path), audio_i16, sr, subtype="PCM_16")
    return len(audio_i16) / sr


# ─── Kokoro Generation ──────────────────────────────────────────────────────

def generate_kokoro(manifest, sample_type):
    """Generate samples with Kokoro TTS. Returns count."""
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    from kokoro import KPipeline

    phrases = POSITIVE_PHRASES if sample_type == "positive" else NEGATIVE_PHRASES
    out_dir = POSITIVE_DIR if sample_type == "positive" else NEGATIVE_DIR
    voices = KOKORO_VOICES if sample_type == "positive" else KOKORO_VOICES[:8]
    variations = KOKORO_POS_VARIATIONS if sample_type == "positive" else [("normal", 1.0, 1.0)]

    total_est = len(voices) * len(phrases) * len(variations)
    count = 0
    errors = 0

    # Group by lang_code to minimize pipeline reloads (2 loads: 'a' and 'b')
    groups = {}
    for lc, vid in voices:
        groups.setdefault(lc, []).append(vid)

    for lang_code, voice_ids in groups.items():
        print(f"  Loading Kokoro pipeline (lang={lang_code})...")
        pipe = KPipeline(
            lang_code=lang_code, repo_id="hexgrad/Kokoro-82M", device="cuda"
        )

        for vid in voice_ids:
            for pi, phrase in enumerate(phrases):
                for var_label, speed, pitch in variations:
                    try:
                        chunks = [
                            r.audio.cpu().numpy()
                            for r in pipe(phrase, voice=vid, speed=speed)
                        ]
                        if not chunks:
                            errors += 1
                            continue

                        audio = np.concatenate(chunks)
                        audio = resample_audio(audio, KOKORO_SR, TARGET_SR, pitch)
                        audio = trim_silence(audio)

                        dur = len(audio) / TARGET_SR
                        if not (0.3 <= dur <= 4.0):
                            continue

                        fname = f"kokoro_{vid}_p{pi}_{var_label}.wav"
                        save_wav(audio, out_dir / fname)

                        manifest.append(dict(
                            filename=fname, phrase=phrase, voice=vid,
                            engine="kokoro", type=sample_type,
                            variation=var_label, duration_s=f"{dur:.2f}",
                        ))
                        count += 1

                        if count % 50 == 0:
                            print(f"  Kokoro {sample_type}: {count}/{total_est}")

                    except Exception as e:
                        errors += 1
                        print(f"  Skip: kokoro/{vid}/p{pi}/{var_label} -- {e}")

        del pipe  # free GPU memory before loading next lang

    print(f"  Kokoro {sample_type} done: {count} samples ({errors} errors)")
    return count


# ─── Edge-TTS Generation ────────────────────────────────────────────────────

async def _edge_one(voice, text, rate, out_path, tmp_dir):
    """Generate one edge-tts sample. Returns True on success."""
    import edge_tts

    tmp_mp3 = Path(tmp_dir) / f"{voice}_{abs(hash(text + rate))}.mp3"
    try:
        await edge_tts.Communicate(text, voice, rate=rate).save(str(tmp_mp3))

        result = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error",
             "-i", str(tmp_mp3),
             "-ar", str(TARGET_SR), "-ac", "1",
             "-acodec", "pcm_s16le", str(out_path)],
            capture_output=True, timeout=30,
        )
        tmp_mp3.unlink(missing_ok=True)

        if result.returncode != 0:
            return False

        audio, sr = sf.read(str(out_path))
        audio = trim_silence(audio)
        dur = len(audio) / sr

        if not (0.3 <= dur <= 4.0):
            out_path.unlink(missing_ok=True)
            return False

        save_wav(audio, out_path, sr)
        return True

    except Exception:
        tmp_mp3.unlink(missing_ok=True)
        out_path.unlink(missing_ok=True)
        return False


async def generate_edge(manifest, sample_type):
    """Generate edge-tts samples. Returns count."""
    phrases = POSITIVE_PHRASES if sample_type == "positive" else NEGATIVE_PHRASES
    out_dir = POSITIVE_DIR if sample_type == "positive" else NEGATIVE_DIR
    voices = EDGE_VOICES if sample_type == "positive" else EDGE_VOICES[:10]
    rates = EDGE_POS_RATES if sample_type == "positive" else [("normal", "+0%")]

    total_est = len(voices) * len(phrases) * len(rates)
    count = 0
    errors = 0

    with tempfile.TemporaryDirectory() as tmp:
        for voice in voices:
            for pi, phrase in enumerate(phrases):
                for rl, rate_str in rates:
                    safe_v = voice.replace("-", "_")
                    fname = f"edge_{safe_v}_p{pi}_{rl}.wav"
                    fpath = out_dir / fname

                    ok = await _edge_one(voice, phrase, rate_str, fpath, tmp)
                    if ok:
                        audio, sr = sf.read(str(fpath))
                        dur = len(audio) / sr
                        manifest.append(dict(
                            filename=fname, phrase=phrase, voice=voice,
                            engine="edge-tts", type=sample_type,
                            variation=rl, duration_s=f"{dur:.2f}",
                        ))
                        count += 1
                    else:
                        errors += 1

                    if count % 50 == 0 and count > 0:
                        print(f"  edge-tts {sample_type}: {count}/{total_est}")

    print(f"  edge-tts {sample_type} done: {count} samples ({errors} errors)")
    return count


# ─── Validation ──────────────────────────────────────────────────────────────

def validate(directory, n=5):
    """Spot-check random WAV files for correct format."""
    wavs = list(directory.glob("*.wav"))
    if not wavs:
        print("  (no files)")
        return
    for f in random.sample(wavs, min(n, len(wavs))):
        audio, sr = sf.read(str(f))
        dur = len(audio) / sr
        mono = audio.ndim == 1
        ok = sr == TARGET_SR and mono and 0.2 < dur < 5.0
        tag = "OK" if ok else "!!"
        ch = "mono" if mono else "STEREO"
        print(f"  [{tag}] {f.name}  {sr}Hz {ch} {dur:.2f}s")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    t0 = time.time()

    # ── Pre-flight checks ────────────────────────────────────────
    if not shutil.which("ffmpeg"):
        sys.exit(
            "ERROR: ffmpeg not found in PATH.\n"
            "Install:  winget install Gyan.FFmpeg\n"
            "Then restart your terminal."
        )

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        sys.exit("ERROR: edge-tts not installed.  Run: pip install edge-tts")

    # ── Create output dirs ───────────────────────────────────────
    POSITIVE_DIR.mkdir(parents=True, exist_ok=True)
    NEGATIVE_DIR.mkdir(parents=True, exist_ok=True)

    manifest = []

    # Expected counts:
    #   Positive Kokoro:  28 voices x 4 phrases x 5 variations = 560
    #   Positive edge:    20 voices x 4 phrases x 3 rates      = 240  => 800 total
    #   Negative Kokoro:   8 voices x 15 phrases x 1 variation =  120
    #   Negative edge:    10 voices x 15 phrases x 1 rate      =  150  => 270 total
    #   Grand total: ~1070

    print("\n[1/4] Generating Kokoro positive samples...")
    k_pos = generate_kokoro(manifest, "positive")

    print("\n[2/4] Generating Kokoro negative samples...")
    k_neg = generate_kokoro(manifest, "negative")

    print("\n[3/4] Generating edge-tts positive samples...")
    e_pos = asyncio.run(generate_edge(manifest, "positive"))

    print("\n[4/4] Generating edge-tts negative samples...")
    e_neg = asyncio.run(generate_edge(manifest, "negative"))

    # ── Write manifest CSV ───────────────────────────────────────
    print("\nWriting manifest...")
    with open(MANIFEST_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "filename", "phrase", "voice", "engine",
            "type", "variation", "duration_s",
        ])
        w.writeheader()
        w.writerows(manifest)

    # ── Summary ──────────────────────────────────────────────────
    total_pos = k_pos + e_pos
    total_neg = k_neg + e_neg
    total_dur = sum(float(m["duration_s"]) for m in manifest)
    n_voices = len({m["voice"] for m in manifest})
    elapsed = time.time() - t0

    pos_ok = "OK" if total_pos >= 500 else "BELOW TARGET"
    neg_ok = "OK" if total_neg >= 200 else "BELOW TARGET"

    print(f"""
{'=' * 60}
GENERATION COMPLETE
{'=' * 60}
  Positive:  {total_pos}  (Kokoro {k_pos} + edge {e_pos})  [{pos_ok}]
  Negative:  {total_neg}  (Kokoro {k_neg} + edge {e_neg})  [{neg_ok}]
  Voices:    {n_voices}
  Duration:  {total_dur:.0f}s ({total_dur / 60:.1f} min of audio)
  Manifest:  {MANIFEST_PATH}
  Time:      {elapsed:.0f}s ({elapsed / 60:.1f} min)
""")

    # ── Spot-check validation ────────────────────────────────────
    print("Validating positive samples...")
    validate(POSITIVE_DIR)
    print("\nValidating negative samples...")
    validate(NEGATIVE_DIR)

    print("\nDone. Next: train custom model via openWakeWord Colab notebook.")


if __name__ == "__main__":
    main()
