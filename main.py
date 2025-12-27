import asyncio
import os
import wave
from io import BytesIO

import numpy as np
import soundfile as sf
from deepgram import DeepgramClient
from dotenv import load_dotenv

# ==========================================
# 0. CONFIG & ENV
# ==========================================

load_dotenv()

AUDIO_DIR = "./voicemail_audio_files"
CHUNK_DURATION_MS = 50  # Simulated streaming chunk size
DEFAULT_STRATEGY = "combined"  # 'silence', 'beep', or 'combined'

# Silence Strategy defaults
SILENCE_WARMUP = 2.0        # seconds
SILENCE_THRESHOLD = 1.5     # seconds of continuous silence
SILENCE_ENERGY_FLOOR = 500  # RMS threshold (int16 domain)

# Beep Strategy defaults
BEEP_TARGET_FREQ = 800      # Hz
BEEP_TOLERANCE = 100        # Hz +/- around target
BEEP_MIN_DURATION = 0.15    # seconds
BEEP_MIN_AMP = 2000         # amplitude in FFT magnitudes

# ==========================================
# 1. STREAMING UTIL
# ==========================================

def stream_audio_file(filepath, chunk_duration_ms=CHUNK_DURATION_MS):
    """
    Generator that simulates live streaming of a WAV file.
    Yields (audio_chunk: np.ndarray (mono), sample_rate, current_time_sec).
    """
    with wave.open(filepath, 'rb') as wf:
        sample_rate = wf.getframerate()
        n_channels = wf.getnchannels()
        chunk_size = int(sample_rate * (chunk_duration_ms / 1000.0))
        current_time = 0.0

        while True:
            data = wf.readframes(chunk_size)
            if len(data) == 0:
                break

            audio_chunk = np.frombuffer(data, dtype=np.int16)
            if n_channels > 1:
                audio_chunk = audio_chunk.reshape(-1, n_channels).mean(axis=1).astype(np.int16)

            if len(audio_chunk) < chunk_size:
                audio_chunk = np.pad(audio_chunk, (0, chunk_size - len(audio_chunk)))

            yield audio_chunk, sample_rate, current_time
            current_time += (chunk_duration_ms / 1000.0)

# ==========================================
# 2. STRATEGY CLASSES
# ==========================================

class BaseStrategy:
    def process(self, chunk, sr, current_time):
        raise NotImplementedError


class SilenceStrategy(BaseStrategy):
    """
    Tracks RMS energy. If energy stays below floor for 'limit' seconds
    after 'warmup', it triggers a drop.
    """
    def __init__(self,
                 warmup=SILENCE_WARMUP,
                 silence_thresh=SILENCE_THRESHOLD,
                 energy_floor=SILENCE_ENERGY_FLOOR):
        self.warmup = warmup
        self.limit = silence_thresh
        self.floor = energy_floor
        self.counter = 0.0

    def process(self, chunk, sr, current_time):
        if current_time < self.warmup:
            self.counter = 0.0
            return False, None

        rms = float(np.sqrt(np.mean(chunk.astype(float) ** 2)))
        chunk_sec = len(chunk) / sr

        if rms < self.floor:
            self.counter += chunk_sec
        else:
            self.counter = 0.0

        if self.counter >= self.limit:
            return True, f"Silence Timeout ({self.limit:.2f}s)"
        return False, None


class BeepStrategy(BaseStrategy):
    """
    Uses FFT to find dominant frequency. If the loudest frequency is
    within [target_freq - tol, target_freq + tol] for >= min_dur, triggers.
    """
    def __init__(self,
                 target_freq=BEEP_TARGET_FREQ,
                 tolerance=BEEP_TOLERANCE,
                 min_dur=BEEP_MIN_DURATION,
                 min_amp=BEEP_MIN_AMP):
        self.freq_min = target_freq - tolerance
        self.freq_max = target_freq + tolerance
        self.min_dur = min_dur
        self.min_amp = min_amp
        self.counter = 0.0

    def process(self, chunk, sr, current_time):
        chunk_float = chunk.astype(float)
        spectrum = np.fft.rfft(chunk_float)
        freqs = np.fft.rfftfreq(len(chunk_float), 1.0 / sr)
        mags = np.abs(spectrum)

        peak_idx = int(np.argmax(mags))
        peak_freq = float(freqs[peak_idx])
        peak_amp = float(mags[peak_idx])
        chunk_sec = len(chunk_float) / sr

        is_match = (peak_amp > self.min_amp) and (self.freq_min <= peak_freq <= self.freq_max)

        if is_match:
            self.counter += chunk_sec
        else:
            self.counter = 0.0

        if self.counter >= self.min_dur:
            return True, f"Beep Detected (~{peak_freq:.0f}Hz)"
        return False, None


class CombinedStrategy(BaseStrategy):
    """
    Parallel beep + silence.
    Priority:
      1. Beep detection (fast lane)
      2. Silence detection (fallback)
    """
    def __init__(self,
                 warmup=SILENCE_WARMUP,
                 silence_thresh=SILENCE_THRESHOLD,
                 target_freq=BEEP_TARGET_FREQ,
                 tolerance=BEEP_TOLERANCE,
                 min_dur=BEEP_MIN_DURATION,
                 energy_floor=SILENCE_ENERGY_FLOOR,
                 min_amp=BEEP_MIN_AMP):
        self.silence_engine = SilenceStrategy(
            warmup=warmup,
            silence_thresh=silence_thresh,
            energy_floor=energy_floor
        )
        self.beep_engine = BeepStrategy(
            target_freq=target_freq,
            tolerance=tolerance,
            min_dur=min_dur,
            min_amp=min_amp
        )

    def process(self, chunk, sr, current_time):
        # 1. Beep (priority)
        drop_beep, reason_beep = self.beep_engine.process(chunk, sr, current_time)
        if drop_beep:
            # Tag with type for clearer logs
            return True, f"[BEEP] {reason_beep}"

        # 2. Silence (fallback)
        drop_silence, reason_silence = self.silence_engine.process(chunk, sr, current_time)
        if drop_silence:
            return True, f"[SILENCE] {reason_silence}"

        return False, None

# ==========================================
# 3. DEEPGRAM-AWARE WRAPPER
# ==========================================

class StreamingVoicemailDropper:
    """
    Uses the same DSP strategies as the Streamlit version to decide drop time
    while streaming each file in small chunks. Deepgram is used optionally for
    transcript annotation (word count + transcript snippet).
    """
    def __init__(self, api_key, strategy_mode=DEFAULT_STRATEGY):
        self.dg_client = DeepgramClient(api_key=api_key)
        self.audio_dir = AUDIO_DIR
        self.strategy_mode = strategy_mode

    def _build_engine(self):
        if self.strategy_mode == "silence":
            return SilenceStrategy()
        elif self.strategy_mode == "beep":
            return BeepStrategy()
        else:
            return CombinedStrategy()

    def _get_duration(self, filepath):
        try:
            with sf.SoundFile(filepath) as f:
                return len(f) / f.samplerate
        except Exception:
            return 0.0

    def transcribe_file(self, filepath):
        """
        Optional STT pass for annotation.
        """
        try:
            with open(filepath, "rb") as audio:
                audio_data = audio.read()

            response = self.dg_client.listen.v1.media.transcribe_file(
                request=audio_data,
                model="nova-2",
                language="en-US",
                smart_format=True,
                punctuate=True,
                utterances=True
            )
            return response
        except Exception:
            return None

    async def process_audio_file(self, filename):
        """
        Core streaming logic:
          - Stream file in CHUNK_DURATION_MS chunks
          - Run selected DSP strategy on each chunk
          - Stop and record drop_time & reason at first trigger
        """
        filepath = os.path.join(self.audio_dir, filename)
        print(f"\n[CALL] {filename}")

        if not os.path.isfile(filepath):
            print(f"[ERROR] File not found: {filepath}")
            return {
                "filename": filename,
                "drop_time": 0.0,
                "method": "[MISSING]",
                "words": 0,
                "transcript": ""
            }

        duration = self._get_duration(filepath)
        engine = self._build_engine()

        drop_time = None
        drop_reason = "[NO_TRIGGER]"

        # --- STREAM LOOP (DSP-BASED DECISION) ---
        for chunk, sr, cur_time in stream_audio_file(filepath, CHUNK_DURATION_MS):
            should_drop, reason = engine.process(chunk, sr, cur_time)
            if should_drop:
                drop_time = cur_time
                drop_reason = reason or "[UNKNOWN]"
                break

        if drop_time is None:
            drop_time = max(duration, 0.0)
            drop_reason = "[NO_TRIGGER_FALLBACK]"

        # --- OPTIONAL: STT PASS (ANNOTATION / DEBUG) ---
        transcript_result = self.transcribe_file(filepath)
        full_transcript = ""
        word_count = 0

        if transcript_result and hasattr(transcript_result, "results"):
            channels = transcript_result.results.channels or []
            if channels:
                alternatives = channels[0].alternatives or []
                if alternatives:
                    alt = alternatives[0]
                    full_transcript = getattr(alt, "transcript", "") or ""
                    words = getattr(alt, "words", []) or []
                    word_count = len(words)

        # Detailed per-file log includes which path fired
        print(f"[DROP] at {drop_time:.2f}s - {drop_reason} ({word_count} words)")

        return {
            "filename": filename,
            "drop_time": drop_time,
            "method": drop_reason,
            "words": word_count,
            "transcript": (
                full_transcript[:50] + "..." if len(full_transcript) > 50 else full_transcript
            ),
        }


# ==========================================
# 4. MAIN / CLI TABLE
# ==========================================

async def main():
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("[ERROR] DEEPGRAM_API_KEY not found in .env file")
        return

    dropper = StreamingVoicemailDropper(api_key=api_key, strategy_mode=DEFAULT_STRATEGY)

    if not os.path.isdir(AUDIO_DIR):
        print(f"[ERROR] Directory '{AUDIO_DIR}' not found")
        return

    files = sorted(f for f in os.listdir(AUDIO_DIR) if f.lower().endswith(".wav"))
    if not files:
        print(f"[ERROR] No .wav files found in '{AUDIO_DIR}'")
        return

    print(f"\n>> Streaming Voicemail Dropper (Strategy: {DEFAULT_STRATEGY.upper()})")
    print(f">> Found {len(files)} audio files\n")
    print("=" * 80)

    results = []
    for filename in files:
        try:
            result = await dropper.process_audio_file(filename)
            results.append(result)
        except Exception as e:
            print(f"\n[ERROR] {filename}: {str(e)}")
            results.append({
                "filename": filename,
                "drop_time": 3.0,
                "method": "[ERROR]",
                "words": 0,
                "transcript": str(e),
            })

    # RESULTS TABLE
    print("\n" + "=" * 80)
    print("FINAL STREAMING RESULTS")
    print("=" * 80)
    print(f"| {'File':<24} | {'Drop Time':>9} | {'Method':<25} | {'Words':>5} |")
    print("|" + "-" * 78 + "|")

    for r in results:
        print(
            f"| {r['filename']:<24} | {r['drop_time']:>8.2f}s | "
            f"{r['method']:<25} | {r['words']:>5} |"
        )

    print("=" * 80)

    if results:
        avg_drop_time = sum(r["drop_time"] for r in results) / len(results)
        total_words = sum(r["words"] for r in results)
    else:
        avg_drop_time = 0.0
        total_words = 0

    print(f"\nSUMMARY:")
    print(f"   * Strategy mode: {DEFAULT_STRATEGY}")
    print(f"   * Average drop time: {avg_drop_time:.2f}s")
    print(f"   * Total words transcribed: {total_words}")
    print(f"   * Files processed: {len(results)}/{len(files)}")
    print("\n[SUCCESS] DSP-based streaming voicemail dropper (beep + silence) "
          "with optional Deepgram transcript annotation.\n")


if __name__ == "__main__":
    asyncio.run(main())
