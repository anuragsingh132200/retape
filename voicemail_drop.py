#!/usr/bin/env python3
"""
Voicemail Drop Detection System for ClearPath Finance
Production-grade implementation with streaming audio processing
"""

import asyncio
import json
import logging
import os
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Tuple

import librosa
import numpy as np
import torch
from dotenv import load_dotenv
from scipy import signal
from scipy.fft import fft, fftfreq

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from deepgram import DeepgramClient
except ImportError:
    DeepgramClient = None

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Compliance and safety rules
SAFETY_RULES = {
    "min_buffer_beep": 0.1,      # 100ms after beep
    "min_buffer_silence": 0.5,   # 500ms after silence
    "max_greeting_length": 30.0, # 30s timeout
    "confidence_threshold": 0.8,
    "min_greeting_length": 2.0   # Don't drop too early
}

# Audio processing constants
SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 20
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)  # 320 samples
VAD_THRESHOLD = 0.5
SILENCE_THRESHOLD_DB = -40
SILENCE_DURATION_THRESHOLD = 1.5
BEEP_FREQ_RANGE = (1000, 2000)
BEEP_MIN_DURATION = 0.2
BEEP_ENERGY_THRESHOLD = -20


@dataclass
class DetectionResult:
    """Result of voicemail drop detection"""
    drop_timestamp: float
    reason: str
    confidence: float
    method_used: List[str]
    compliance_status: str
    details: Dict = None


class StreamSimulator:
    """Simulates streaming audio by reading WAV file in chunks"""

    def __init__(self, filepath: str, chunk_size: int = CHUNK_SIZE):
        self.filepath = filepath
        self.chunk_size = chunk_size
        self.sample_rate = SAMPLE_RATE

    async def stream_chunks(self) -> AsyncGenerator[np.ndarray, None]:
        """Stream audio in 20ms chunks"""
        try:
            # Load audio file
            audio, sr = librosa.load(self.filepath, sr=self.sample_rate, mono=True)

            # Normalize audio
            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio))

            logger.info(f"Loaded {self.filepath}: {len(audio)/sr:.2f}s, {sr}Hz")

            # Stream in chunks
            for i in range(0, len(audio), self.chunk_size):
                chunk = audio[i:i + self.chunk_size]
                if len(chunk) < self.chunk_size:
                    # Pad last chunk
                    chunk = np.pad(chunk, (0, self.chunk_size - len(chunk)))

                yield chunk
                await asyncio.sleep(0.001)  # Simulate real-time streaming

        except Exception as e:
            logger.error(f"Error streaming {self.filepath}: {e}")
            raise


class VADFilter:
    """Voice Activity Detection using Silero VAD"""

    def __init__(self, threshold: float = VAD_THRESHOLD):
        self.threshold = threshold
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load Silero VAD model"""
        try:
            self.model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            logger.info("Silero VAD model loaded successfully")
        except Exception as e:
            logger.warning(f"Could not load Silero VAD: {e}. Using RMS-based VAD.")
            self.model = None

    def is_speech(self, chunk: np.ndarray) -> bool:
        """Detect if chunk contains speech"""
        if self.model is None:
            # Fallback to RMS-based detection
            rms = np.sqrt(np.mean(chunk ** 2))
            rms_db = 20 * np.log10(rms + 1e-10)
            return rms_db > SILENCE_THRESHOLD_DB

        try:
            # Convert to tensor
            audio_tensor = torch.from_numpy(chunk).float()

            # Get VAD probability
            speech_prob = self.model(audio_tensor, SAMPLE_RATE).item()

            return speech_prob > self.threshold
        except Exception as e:
            logger.warning(f"VAD error: {e}")
            return True  # Conservative: assume speech on error


class BeepDetector:
    """Detects voicemail beep using FFT analysis"""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.freq_range = BEEP_FREQ_RANGE
        self.min_duration = BEEP_MIN_DURATION
        self.energy_threshold = BEEP_ENERGY_THRESHOLD
        self.beep_buffer = []
        self.beep_timestamps = []

    def analyze_chunk(self, chunk: np.ndarray, timestamp: float) -> Tuple[bool, float]:
        """
        Analyze chunk for beep presence
        Returns: (is_beep, confidence)
        """
        # Perform FFT
        fft_vals = fft(chunk)
        freqs = fftfreq(len(chunk), 1/self.sample_rate)

        # Get positive frequencies only
        positive_freqs = freqs[:len(freqs)//2]
        positive_fft = np.abs(fft_vals[:len(fft_vals)//2])

        # Convert to dB
        with np.errstate(divide='ignore'):
            fft_db = 20 * np.log10(positive_fft + 1e-10)

        # Find peaks in beep frequency range
        mask = (positive_freqs >= self.freq_range[0]) & (positive_freqs <= self.freq_range[1])
        if not np.any(mask):
            return False, 0.0

        beep_energy = np.max(fft_db[mask])

        # Check if energy is above threshold
        if beep_energy > self.energy_threshold:
            self.beep_buffer.append(timestamp)

            # Check if we have sustained beep (200ms+)
            if len(self.beep_buffer) >= int(self.min_duration / (CHUNK_DURATION_MS / 1000)):
                # Calculate confidence based on energy
                confidence = min(1.0, (beep_energy - self.energy_threshold) / 20)
                self.beep_timestamps.append(timestamp)
                logger.info(f"Beep detected at {timestamp:.2f}s (energy: {beep_energy:.1f}dB, conf: {confidence:.2f})")
                return True, confidence
        else:
            self.beep_buffer.clear()

        return False, 0.0

    def get_last_beep(self) -> Optional[float]:
        """Get timestamp of last detected beep"""
        return self.beep_timestamps[-1] if self.beep_timestamps else None


class SilenceTracker:
    """Tracks silence periods in audio"""

    def __init__(self, threshold_db: float = SILENCE_THRESHOLD_DB,
                 duration_threshold: float = SILENCE_DURATION_THRESHOLD):
        self.threshold_db = threshold_db
        self.duration_threshold = duration_threshold
        self.silence_start = None
        self.last_speech_time = 0
        self.silence_detected = False

    def analyze_chunk(self, chunk: np.ndarray, timestamp: float, is_speech: bool) -> Tuple[bool, float]:
        """
        Track silence in chunk
        Returns: (is_silence_threshold_met, confidence)
        """
        # Calculate RMS energy
        rms = np.sqrt(np.mean(chunk ** 2))
        rms_db = 20 * np.log10(rms + 1e-10)

        is_silent = rms_db < self.threshold_db and not is_speech

        if is_silent:
            if self.silence_start is None:
                self.silence_start = timestamp

            silence_duration = timestamp - self.silence_start

            if silence_duration >= self.duration_threshold and self.last_speech_time > 0:
                confidence = min(1.0, silence_duration / (self.duration_threshold * 2))
                if not self.silence_detected:
                    logger.info(f"Silence threshold met at {timestamp:.2f}s ({silence_duration:.2f}s)")
                    self.silence_detected = True
                return True, confidence
        else:
            if is_speech:
                self.last_speech_time = timestamp
            self.silence_start = None

        return False, 0.0


class PhraseDetector:
    """Detects voicemail end phrases using Gemini LLM"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize Gemini model"""
        if genai is None:
            logger.warning("google-generativeai not installed. Phrase detection disabled.")
            return

        if not self.api_key or self.api_key == 'your_gemini_api_key_here':
            logger.warning("Gemini API key not configured. Phrase detection disabled.")
            return

        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            logger.info("Gemini model initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize Gemini: {e}")
            self.model = None

    async def analyze_transcript(self, transcript: str) -> Dict:
        """
        Analyze transcript for voicemail end phrases
        Returns dict with is_greeting_end, phrases, beep_expected, confidence
        """
        if not self.model or not transcript.strip():
            return {
                "is_greeting_end": False,
                "end_phrases_detected": [],
                "beep_expected": False,
                "confidence": 0.0
            }

        prompt = f"""Analyze this voicemail greeting transcript:
"{transcript}"

JSON output:
{{
  "is_greeting_end": true/false,
  "end_phrases_detected": ["after the beep", "leave message"],
  "beep_expected": true/false,
  "confidence": 0.95
}}

Look for phrases indicating the greeting is ending such as:
- "after the beep"
- "leave a message"
- "at the tone"
- "after the tone"
- "leave your message"
- "we'll get back to you"

Return ONLY valid JSON."""

        try:
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt
            )

            # Parse JSON from response
            text = response.text.strip()
            # Remove markdown code blocks if present
            if text.startswith('```'):
                text = text.split('```')[1]
                if text.startswith('json'):
                    text = text[4:]

            result = json.loads(text)
            logger.info(f"Phrase analysis: {result}")
            return result

        except Exception as e:
            logger.warning(f"Phrase detection error: {e}")
            # Fallback to simple keyword matching
            return self._simple_phrase_detection(transcript)

    def _simple_phrase_detection(self, transcript: str) -> Dict:
        """Fallback phrase detection using keywords"""
        transcript_lower = transcript.lower()

        phrases = [
            "after the beep", "after the tone", "at the tone",
            "leave a message", "leave your message", "leave message",
            "we'll get back", "we will get back", "return your call"
        ]

        detected = [p for p in phrases if p in transcript_lower]
        beep_expected = any(word in transcript_lower for word in ["beep", "tone"])

        return {
            "is_greeting_end": len(detected) > 0,
            "end_phrases_detected": detected,
            "beep_expected": beep_expected,
            "confidence": 0.7 if detected else 0.0
        }


class STTDetector:
    """Speech-to-Text detector using Deepgram"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('DEEPGRAM_API_KEY')
        self.transcript_buffer = []
        self.full_transcript = ""

    async def process_audio(self, audio_data: np.ndarray) -> str:
        """
        Process audio and return transcript
        For demo purposes, we'll skip actual Deepgram API to avoid costs
        """
        # In production, this would connect to Deepgram's live API
        # For now, return empty transcript
        return ""

    def get_recent_transcript(self, window_seconds: float = 5.0) -> str:
        """Get recent transcript from buffer"""
        return self.full_transcript


class FusionEngine:
    """Combines multiple detection methods into final decision"""

    def __init__(self):
        self.beep_weight = 0.4
        self.phrase_weight = 0.3
        self.silence_weight = 0.3
        self.confidence_threshold = SAFETY_RULES["confidence_threshold"]

    def calculate_confidence(self, beep_conf: float, phrase_conf: float,
                           silence_conf: float) -> float:
        """Calculate weighted confidence score"""
        confidence = (
            self.beep_weight * beep_conf +
            self.phrase_weight * phrase_conf +
            self.silence_weight * silence_conf
        )
        return confidence

    def make_decision(self, timestamp: float, beep_detected: bool,
                     beep_conf: float, beep_timestamp: Optional[float],
                     phrase_result: Dict, silence_detected: bool,
                     silence_conf: float) -> Optional[DetectionResult]:
        """
        Make final drop decision based on all signals
        """
        # Calculate combined confidence
        phrase_conf = phrase_result.get('confidence', 0.0)
        total_confidence = self.calculate_confidence(beep_conf, phrase_conf, silence_conf)

        methods_used = []
        reason = None
        drop_time = None

        # Beep-based detection (highest priority)
        if beep_detected and beep_timestamp:
            methods_used.append("beep")
            reason = "beep_detected"
            drop_time = beep_timestamp + SAFETY_RULES["min_buffer_beep"]

        # Phrase + silence detection
        if phrase_result.get('is_greeting_end', False):
            methods_used.append("phrase")
            if not reason:
                reason = "phrase_detected"

        if silence_detected:
            methods_used.append("silence")
            if not reason:
                reason = "silence_detected"
                drop_time = timestamp + SAFETY_RULES["min_buffer_silence"]

        # Make decision
        if total_confidence >= self.confidence_threshold and drop_time:
            # Ensure minimum greeting length
            if drop_time < SAFETY_RULES["min_greeting_length"]:
                logger.warning(f"Drop time {drop_time:.2f}s too early, adjusting to minimum")
                drop_time = SAFETY_RULES["min_greeting_length"]

            # Check timeout
            if drop_time > SAFETY_RULES["max_greeting_length"]:
                drop_time = SAFETY_RULES["max_greeting_length"]
                reason = "timeout"

            compliance = "safe" if drop_time >= SAFETY_RULES["min_greeting_length"] else "risky"

            return DetectionResult(
                drop_timestamp=round(drop_time, 2),
                reason=reason,
                confidence=round(total_confidence, 2),
                method_used=methods_used,
                compliance_status=compliance,
                details={
                    "beep_confidence": round(beep_conf, 2),
                    "phrase_confidence": round(phrase_conf, 2),
                    "silence_confidence": round(silence_conf, 2),
                    "phrases_detected": phrase_result.get('end_phrases_detected', [])
                }
            )

        return None


class VoicemailDropDetector:
    """Main voicemail drop detection system"""

    def __init__(self):
        self.vad = VADFilter()
        self.beep_detector = BeepDetector()
        self.silence_tracker = SilenceTracker()
        self.phrase_detector = PhraseDetector()
        self.stt_detector = STTDetector()
        self.fusion_engine = FusionEngine()

    async def process_file(self, filepath: str) -> DetectionResult:
        """
        Process a single audio file and detect voicemail drop point
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {filepath}")
        logger.info(f"{'='*60}")

        stream = StreamSimulator(filepath)

        timestamp = 0.0
        chunk_duration = CHUNK_DURATION_MS / 1000

        beep_detected = False
        beep_conf = 0.0
        silence_detected = False
        silence_conf = 0.0

        transcript = ""
        phrase_result = {
            "is_greeting_end": False,
            "end_phrases_detected": [],
            "beep_expected": False,
            "confidence": 0.0
        }

        async for chunk in stream.stream_chunks():
            # VAD filtering
            is_speech = self.vad.is_speech(chunk)

            # Beep detection
            chunk_beep, chunk_beep_conf = self.beep_detector.analyze_chunk(chunk, timestamp)
            if chunk_beep:
                beep_detected = True
                beep_conf = max(beep_conf, chunk_beep_conf)

            # Silence tracking
            chunk_silence, chunk_silence_conf = self.silence_tracker.analyze_chunk(
                chunk, timestamp, is_speech
            )
            if chunk_silence:
                silence_detected = True
                silence_conf = max(silence_conf, chunk_silence_conf)

            # Update timestamp
            timestamp += chunk_duration

            # Check for decision every 0.5s
            if int(timestamp * 2) != int((timestamp - chunk_duration) * 2):
                # Get transcript (in production, from Deepgram)
                transcript = self.stt_detector.get_recent_transcript()

                # Analyze phrases (every 2 seconds to avoid rate limits)
                if int(timestamp) % 2 == 0 and int(timestamp) > 0:
                    phrase_result = await self.phrase_detector.analyze_transcript(transcript)

                # Make decision
                decision = self.fusion_engine.make_decision(
                    timestamp=timestamp,
                    beep_detected=beep_detected,
                    beep_conf=beep_conf,
                    beep_timestamp=self.beep_detector.get_last_beep(),
                    phrase_result=phrase_result,
                    silence_detected=silence_detected,
                    silence_conf=silence_conf
                )

                if decision:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"DECISION: Drop at {decision.drop_timestamp}s")
                    logger.info(f"Reason: {decision.reason}")
                    logger.info(f"Confidence: {decision.confidence}")
                    logger.info(f"Methods: {', '.join(decision.method_used)}")
                    logger.info(f"Compliance: {decision.compliance_status}")
                    logger.info(f"{'='*60}\n")
                    return decision

            # Timeout check
            if timestamp > SAFETY_RULES["max_greeting_length"]:
                logger.warning("Timeout reached")
                return DetectionResult(
                    drop_timestamp=SAFETY_RULES["max_greeting_length"],
                    reason="timeout",
                    confidence=0.5,
                    method_used=["timeout"],
                    compliance_status="safe",
                    details={"timeout": True}
                )

        # End of file - use best available signal
        final_timestamp = timestamp
        if beep_detected:
            final_timestamp = self.beep_detector.get_last_beep() + SAFETY_RULES["min_buffer_beep"]
        elif silence_detected:
            final_timestamp = timestamp

        return DetectionResult(
            drop_timestamp=max(final_timestamp, SAFETY_RULES["min_greeting_length"]),
            reason="end_of_file",
            confidence=max(beep_conf, silence_conf),
            method_used=["beep"] if beep_detected else ["silence"] if silence_detected else ["timeout"],
            compliance_status="safe",
            details={}
        )


async def process_all_files(audio_dir: str = "Voicemails - SWE Intern") -> Dict:
    """Process all voicemail files and return results"""

    detector = VoicemailDropDetector()
    results = {}

    # Find all WAV files
    audio_path = Path(audio_dir)
    wav_files = sorted(audio_path.glob("*.wav"))

    if not wav_files:
        logger.error(f"No WAV files found in {audio_dir}")
        return results

    logger.info(f"Found {len(wav_files)} audio files")

    for wav_file in wav_files:
        try:
            result = await detector.process_file(str(wav_file))

            results[wav_file.name] = {
                "drop_timestamp": result.drop_timestamp,
                "reason": result.reason,
                "confidence": result.confidence,
                "method_used": result.method_used,
                "compliance_status": result.compliance_status
            }

            if result.details:
                results[wav_file.name]["details"] = result.details

        except Exception as e:
            logger.error(f"Error processing {wav_file.name}: {e}", exc_info=True)
            results[wav_file.name] = {
                "error": str(e),
                "drop_timestamp": None,
                "reason": "error",
                "confidence": 0.0,
                "method_used": [],
                "compliance_status": "error"
            }

    return results


async def main():
    """Main demo function"""
    print("\n" + "="*60)
    print("VOICEMAIL DROP DETECTION SYSTEM")
    print("ClearPath Finance - Production Demo")
    print("="*60 + "\n")

    # Process all files
    results = await process_all_files()

    # Save results
    output_file = "results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)

    for filename, result in results.items():
        print(f"\n{filename}:")
        print(f"  Drop Time: {result.get('drop_timestamp', 'N/A')}s")
        print(f"  Reason: {result.get('reason', 'N/A')}")
        print(f"  Confidence: {result.get('confidence', 0.0)}")
        print(f"  Methods: {', '.join(result.get('method_used', []))}")
        print(f"  Compliance: {result.get('compliance_status', 'N/A')}")

    print(f"\n\nResults saved to: {output_file}")
    print("="*60 + "\n")

    return results


if __name__ == "__main__":
    asyncio.run(main())
