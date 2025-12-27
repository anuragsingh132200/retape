# Voicemail Drop Detection System

Production-grade voicemail drop detection system for ClearPath Finance using streaming audio processing, multi-method fusion, and LLM-powered phrase detection.

## Features

- **Real-time Streaming**: Processes audio in 20ms chunks to simulate live phone calls
- **Multi-Method Detection**: Combines beep detection, silence tracking, and phrase analysis
- **Voice Activity Detection**: Uses Silero VAD to filter speech from noise
- **FFT-based Beep Detection**: Identifies voicemail beeps at 1000-2000Hz
- **LLM Phrase Analysis**: Gemini 1.5 Flash detects voicemail end phrases
- **Fusion Engine**: Weighted confidence scoring for robust decision making
- **Compliance-Safe**: Built-in safety rules to prevent premature drops

## Architecture

```
┌─ Stream Simulator ─┐
│   20ms chunks     │
│   asyncio queue   │
└────────┬──────────┘
         │
┌─ PREPROCESSING ──┐
│  -  VAD (Silero)  │◄── 95% speech filter
│  -  RMS normalize │
└────────┬──────────┘
         │
    ┌────┼────┐
    │    │    │
STT  │    │   FFT    SILENCE
DETECTOR│   DETECTOR  TRACKER
(Deepgram)│ (1-2kHz)  (1.5s threshold)
    │    │    │
    └────┼────┘
         │
┌─ FUSION ENGINE ──┐
│ confidence =     │
│ 0.4*beep +       │◄── TRIGGER if >0.8
│ 0.3*phrase +     │
│ 0.3*silence      │
└────────┬──────────┘
         │
┌─ DECISION MAKER ─┤
│  -  Beep: +100ms │
│  -  No beep:     │
│    +500ms buffer │
└──────────────────┘
```

## Setup

### 1. Install Dependencies

**Windows:**
```bash
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

**Manual Installation:**
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Edit [.env](.env) file:
```env
DEEPGRAM_API_KEY=your_deepgram_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

Get API keys:
- **Deepgram**: https://console.deepgram.com/signup (Optional - STT disabled in demo mode)
- **Gemini**: https://makersuite.google.com/app/apikey

### 3. Audio Files

Place your 16kHz mono WAV files in the `Voicemails - SWE Intern/` directory, or update the path in the script.

## Usage

### Run Demo on All Files

**Windows:**
```bash
run_demo.bat
```

**Linux/Mac:**
```bash
chmod +x run_demo.sh
./run_demo.sh
```

**Python:**
```bash
python voicemail_drop.py
```

### Output

The system generates [results.json](results.json) with the following format:

```json
{
  "vm1_output.wav": {
    "drop_timestamp": 4.23,
    "reason": "beep_detected",
    "confidence": 0.92,
    "method_used": ["beep", "silence"],
    "compliance_status": "safe",
    "details": {
      "beep_confidence": 0.95,
      "phrase_confidence": 0.85,
      "silence_confidence": 0.90,
      "phrases_detected": ["after the beep", "leave a message"]
    }
  }
}
```

## Detection Methods

### 1. Beep Detection (FFT)
- Frequency range: 1000-2000Hz
- Minimum duration: 200ms
- Energy threshold: -20dB
- Buffer after beep: 100ms

### 2. Silence Detection
- RMS threshold: -40dB
- Duration threshold: 1.5s
- Buffer after silence: 500ms

### 3. Phrase Detection (Gemini LLM)
- Detects phrases like:
  - "after the beep/tone"
  - "leave a message"
  - "we'll get back to you"
- Fallback to keyword matching if API unavailable

### 4. Fusion Engine
- Beep weight: 40%
- Phrase weight: 30%
- Silence weight: 30%
- Confidence threshold: 0.8

## Compliance & Safety Rules

```python
SAFETY_RULES = {
    "min_buffer_beep": 0.1,      # 100ms after beep
    "min_buffer_silence": 0.5,   # 500ms after silence
    "max_greeting_length": 30.0, # 30s timeout
    "confidence_threshold": 0.8,
    "min_greeting_length": 2.0   # Don't drop too early
}
```

## Edge Cases Handled

1. **No Beep**: Falls back to silence + phrase detection
2. **False Beeps**: Requires sustained 200ms+ duration
3. **Music Background**: VAD filters non-speech
4. **Long Greetings**: 30s timeout protection
5. **Short Greetings**: Minimum 2s buffer enforced
6. **Multiple Beeps**: Uses last beep only
7. **No Speech**: 3s silence triggers drop
8. **Partial Phrases**: Weighted confidence prevents false positives

## Technical Details

### Audio Processing
- Sample Rate: 16kHz
- Chunk Size: 20ms (320 samples)
- Format: Mono WAV
- Normalization: RMS-based

### Voice Activity Detection
- Model: Silero VAD v3.1
- Threshold: 0.5
- Fallback: RMS-based detection

### Performance
- Real-time streaming simulation
- Async processing with asyncio
- Memory-efficient chunked processing
- No full file buffering

## Project Structure

```
retape/
├── voicemail_drop.py          # Main detection system
├── requirements.txt            # Python dependencies
├── .env                        # API keys (not committed)
├── README.md                   # This file
├── setup.bat / setup.sh        # Setup scripts
├── run_demo.bat / run_demo.sh  # Demo runners
├── results.json                # Output results
└── Voicemails - SWE Intern/    # Audio files
    ├── vm1_output.wav
    ├── vm2_output.wav
    └── ...
```

## Classes & Components

- **StreamSimulator**: Simulates real-time audio streaming
- **VADFilter**: Voice activity detection with Silero
- **BeepDetector**: FFT-based beep detection
- **SilenceTracker**: RMS-based silence tracking
- **PhraseDetector**: Gemini LLM phrase analysis
- **STTDetector**: Deepgram speech-to-text (optional)
- **FusionEngine**: Multi-method decision fusion
- **VoicemailDropDetector**: Main pipeline orchestrator

## Logging

Detailed logs include:
- File loading and duration
- Speech/silence detection
- Beep detection with timestamps
- Phrase analysis results
- Fusion engine decisions
- Final drop timestamps

## Example Output

```
============================================================
Processing: Voicemails - SWE Intern/vm1_output.wav
============================================================
Loaded vm1_output.wav: 16.88s, 16000Hz
Silero VAD model loaded successfully
Gemini model initialized successfully
Beep detected at 4.12s (energy: -15.3dB, conf: 0.92)
Silence threshold met at 5.20s (1.58s)
Phrase analysis: {'is_greeting_end': True, 'confidence': 0.85, ...}

============================================================
DECISION: Drop at 4.23s
Reason: beep_detected
Confidence: 0.89
Methods: beep, phrase, silence
Compliance: safe
============================================================
```

## Requirements

- Python 3.8+
- PyTorch 2.0+
- librosa 0.10+
- numpy 1.24+
- scipy 1.10+
- google-generativeai 0.3+
- deepgram-sdk 3.0+ (optional)

## License

Proprietary - ClearPath Finance

## Author

Developed for ClearPath Finance take-home assignment

## Support

For issues or questions, contact the development team.
