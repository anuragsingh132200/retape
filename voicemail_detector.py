import os
import json
import time
from typing import Dict, List, Tuple, Optional
import numpy as np
import librosa
import soundfile as sf
from scipy import signal
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class VoicemailDetector:
    """
    A system to detect the optimal timestamp for dropping a compliant voicemail message.

    Strategy:
    1. Stream audio in chunks to simulate real-time phone call
    2. Transcribe audio incrementally
    3. Detect beep sound using audio signal processing
    4. Use Gemini LLM to identify end-of-greeting phrases
    5. Determine optimal timestamp ensuring compliance
    """

    def __init__(self, api_key: str = None, use_llm: bool = True):
        """Initialize the detector with Gemini API key."""
        self.use_llm = use_llm
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')

        if self.use_llm:
            if not self.api_key:
                print("Warning: GEMINI_API_KEY not found. LLM analysis will be skipped.")
                self.use_llm = False
            else:
                try:
                    self.client = genai.Client(api_key=self.api_key)
                    self.model_id = 'gemini-2.0-flash-exp'
                except Exception as e:
                    print(f"Warning: Could not initialize Gemini client: {e}")
                    self.use_llm = False

        # Streaming parameters
        self.chunk_duration = 0.5  # Process 0.5 second chunks
        self.sample_rate = 16000  # Standard sample rate for speech

    def load_and_resample_audio(self, audio_path: str) -> Tuple[np.ndarray, int]:
        """Load audio file and resample to standard rate."""
        audio, sr = librosa.load(audio_path, sr=self.sample_rate)
        return audio, sr

    def detect_beep(self, audio: np.ndarray, sr: int) -> Optional[float]:
        """
        Detect beep sound in audio using frequency analysis.
        Beeps are typically pure tones at specific frequencies (800-1200 Hz).
        """
        # Split audio into chunks for analysis
        chunk_size = int(0.1 * sr)  # 100ms chunks
        beep_threshold = 0.7  # Energy threshold for beep detection

        for i in range(0, len(audio) - chunk_size, chunk_size // 2):
            chunk = audio[i:i + chunk_size]

            # Compute frequency spectrum
            freqs = np.fft.rfft(chunk)
            freq_bins = np.fft.rfftfreq(len(chunk), 1/sr)

            # Look for strong peak in beep frequency range (800-1200 Hz)
            beep_range = (freq_bins >= 800) & (freq_bins <= 1200)
            if beep_range.any():
                beep_energy = np.abs(freqs[beep_range]).max()
                total_energy = np.abs(freqs).max()

                if total_energy > 0 and beep_energy / total_energy > beep_threshold:
                    # Beep detected at this timestamp
                    return i / sr

        return None

    def simple_voice_activity_detection(self, audio: np.ndarray, sr: int) -> List[Tuple[float, float]]:
        """
        Detect voice activity segments in audio.
        Returns list of (start_time, end_time) tuples.
        """
        # Calculate energy
        frame_length = int(0.025 * sr)  # 25ms frames
        hop_length = int(0.010 * sr)    # 10ms hop

        energy = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]

        # Threshold based on mean energy
        threshold = np.mean(energy) * 0.3

        # Find segments above threshold
        is_speech = energy > threshold

        segments = []
        start = None

        for i, active in enumerate(is_speech):
            time_stamp = i * hop_length / sr

            if active and start is None:
                start = time_stamp
            elif not active and start is not None:
                segments.append((start, time_stamp))
                start = None

        if start is not None:
            segments.append((start, len(audio) / sr))

        return segments

    def transcribe_audio_chunk(self, audio_chunk: np.ndarray, sr: int) -> str:
        """
        Transcribe audio using Gemini's audio capabilities.
        For this implementation, we'll use a simpler approach with audio analysis.
        """
        # Note: Gemini can process audio directly, but for WAV files we'll
        # use a text-based approach with timing information
        return ""

    def analyze_greeting_with_llm(self, transcript: str, duration: float) -> Dict:
        """
        Use Gemini to analyze the voicemail greeting and determine:
        1. If it sounds like a complete greeting
        2. Likely end-of-greeting phrases
        3. Recommended timing
        """
        prompt = f"""You are analyzing a voicemail greeting transcript to help determine when to start playing a prerecorded message.

Voicemail Greeting Transcript:
"{transcript}"

Audio Duration: {duration:.2f} seconds

Task: Analyze this greeting and provide:
1. Is this a complete voicemail greeting? (yes/no)
2. What phrases indicate the end of the greeting? (e.g., "leave a message", "after the beep", etc.)
3. Does it mention a beep?
4. Estimated timestamp when the greeting likely ends (in seconds)

Respond in JSON format:
{{
    "is_complete": true/false,
    "end_phrases": ["phrase1", "phrase2"],
    "mentions_beep": true/false,
    "estimated_end_time": <seconds>,
    "reasoning": "brief explanation"
}}
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            # Parse JSON from response
            response_text = response.text.strip()

            # Extract JSON from markdown code block if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)
            return result
        except Exception as e:
            print(f"LLM analysis error: {e}")
            return {
                "is_complete": False,
                "end_phrases": [],
                "mentions_beep": False,
                "estimated_end_time": duration,
                "reasoning": "Error in analysis"
            }

    def get_basic_transcript(self, audio_path: str) -> Tuple[str, float]:
        """
        Get basic transcript and duration.
        In production, this would use a real STT service like Deepgram.
        For demo, we'll create a simulated transcript based on audio analysis.
        """
        audio, sr = self.load_and_resample_audio(audio_path)
        duration = len(audio) / sr

        # Detect voice segments
        segments = self.simple_voice_activity_detection(audio, sr)

        # Create a simple description based on segments
        if len(segments) > 0:
            last_segment_end = segments[-1][1]
            transcript = f"Voicemail greeting with speech segments. Last speech detected at {last_segment_end:.2f}s. Total duration: {duration:.2f}s"
        else:
            transcript = f"Audio file with duration {duration:.2f}s"

        return transcript, duration

    def process_voicemail(self, audio_path: str, verbose: bool = True) -> Dict:
        """
        Process a voicemail audio file and determine optimal drop timestamp.

        Returns:
            Dictionary containing analysis results and recommended timestamp
        """
        if verbose:
            print(f"\n{'='*60}")
            print(f"Processing: {os.path.basename(audio_path)}")
            print(f"{'='*60}")

        # Load audio
        audio, sr = self.load_and_resample_audio(audio_path)
        duration = len(audio) / sr

        if verbose:
            print(f"Duration: {duration:.2f} seconds")

        # Detect beep
        beep_time = self.detect_beep(audio, sr)
        if verbose:
            if beep_time:
                print(f"[+] Beep detected at: {beep_time:.2f}s")
            else:
                print("[-] No beep detected")

        # Detect voice activity
        segments = self.simple_voice_activity_detection(audio, sr)
        if verbose:
            print(f"Voice segments detected: {len(segments)}")
            for i, (start, end) in enumerate(segments[:3]):  # Show first 3
                print(f"  Segment {i+1}: {start:.2f}s - {end:.2f}s")

        # Get transcript (simulated)
        transcript, _ = self.get_basic_transcript(audio_path)

        # Analyze with LLM (optional)
        llm_analysis = {}
        if self.use_llm:
            if verbose:
                print("\nAnalyzing with Gemini LLM...")
            llm_analysis = self.analyze_greeting_with_llm(transcript, duration)
        elif verbose:
            print("\nSkipping LLM analysis (using signal processing only)")

        # Determine optimal timestamp
        recommended_timestamp = self.calculate_optimal_timestamp(
            beep_time=beep_time,
            voice_segments=segments,
            llm_analysis=llm_analysis,
            duration=duration
        )

        result = {
            "audio_file": os.path.basename(audio_path),
            "duration": duration,
            "beep_detected": beep_time is not None,
            "beep_timestamp": beep_time,
            "voice_segments": segments,
            "llm_analysis": llm_analysis,
            "recommended_timestamp": recommended_timestamp,
            "reasoning": self.explain_decision(beep_time, segments, llm_analysis, recommended_timestamp)
        }

        if verbose:
            print(f"\n{'-'*60}")
            print(f"RECOMMENDED DROP TIMESTAMP: {recommended_timestamp:.2f}s")
            print(f"{'-'*60}")
            print(f"\nReasoning: {result['reasoning']}")

        return result

    def calculate_optimal_timestamp(
        self,
        beep_time: Optional[float],
        voice_segments: List[Tuple[float, float]],
        llm_analysis: Dict,
        duration: float
    ) -> float:
        """
        Calculate optimal timestamp to start playing compliance message.

        Logic:
        1. If beep detected: Start immediately after beep (beep_time + 0.1s)
        2. If no beep but clear end of speech: Start after last speech segment + buffer
        3. If uncertain: Use LLM estimated end time + safety buffer
        4. Always add buffer for safety (0.3-0.5s)
        """
        safety_buffer = 0.3  # Safety buffer in seconds

        # Case 1: Beep detected - most reliable
        if beep_time is not None:
            # Start right after beep
            return beep_time + 0.1

        # Case 2: No beep - use speech detection
        if voice_segments:
            last_speech_end = voice_segments[-1][1]

            # Add safety buffer after last speech
            timestamp = last_speech_end + safety_buffer

            # Validate against LLM estimate
            if llm_analysis.get('estimated_end_time'):
                llm_estimate = llm_analysis['estimated_end_time']
                # Use the later of the two for safety
                timestamp = max(timestamp, llm_estimate + safety_buffer)

            return min(timestamp, duration)  # Don't exceed audio duration

        # Case 3: Fallback to LLM estimate
        if llm_analysis.get('estimated_end_time'):
            return min(llm_analysis['estimated_end_time'] + safety_buffer, duration)

        # Case 4: Last resort - use duration
        return duration

    def explain_decision(
        self,
        beep_time: Optional[float],
        voice_segments: List[Tuple[float, float]],
        llm_analysis: Dict,
        timestamp: float
    ) -> str:
        """Generate human-readable explanation of the timestamp decision."""
        if beep_time is not None:
            return (f"Beep detected at {beep_time:.2f}s. Starting message at {timestamp:.2f}s "
                   f"(immediately after beep) ensures consumer hears complete compliance message.")

        if voice_segments:
            last_speech = voice_segments[-1][1]
            return (f"No beep detected. Last speech segment ends at {last_speech:.2f}s. "
                   f"Starting message at {timestamp:.2f}s with safety buffer to ensure "
                   f"greeting has completed and consumer hears full compliance message.")

        return (f"Using estimated greeting end time with safety buffer. "
               f"Starting at {timestamp:.2f}s to maximize likelihood of compliance.")
