# 📞 Drop Compliant Voicemails - ClearPath Finance Assignment

> **A real-time voicemail detection system that determines the optimal timestamp to start leaving compliant voicemail messages**

---

## 🎯 Problem Statement

When ClearPath Finance's automated system calls customers and reaches voicemail, it must leave a **compliant message** that includes:
- Company name ("ClearPath Finance")
- Return phone number

**The Challenge:** If a voicemail beep occurs, anything spoken before the beep is not recorded. The system must detect when the greeting ends (beep or silence) to ensure the complete message is captured.

### Real-World Scenarios

**❌ Non-Compliant (Too Early)**
```
Greeting: "Hi, you've reached Mike..."
System: "Hi, this is ClearPath Finance—"
[BEEP]
What Mike Hears: "—please call 800-555-0199"
Result: Missing company name = Legal violation
```

**✅ Compliant (Perfect Timing)**
```
Greeting: "...leave a message after the beep"
[BEEP]
System: "Hi, this is ClearPath Finance... call 800-555-0199"
Result: Complete message captured
```

---

## 🧠 Solution Approach

This solution uses **three detection strategies** to handle various voicemail greeting types:

### 1️⃣ Beep Detection Strategy
- **Method:** FFT (Fast Fourier Transform) frequency analysis
- **Logic:** Detects sustained tones around 800 Hz (±100 Hz tolerance)
- **Best for:** Voicemails with standard beep tones
- **Parameters:**
  - Target frequency: 800 Hz
  - Minimum duration: 0.15 seconds
  - Minimum amplitude: 2000

### 2️⃣ Silence Detection Strategy
- **Method:** RMS (Root Mean Square) energy analysis
- **Logic:** Triggers after 1.5 seconds of continuous silence
- **Best for:** Voicemails without beeps
- **Parameters:**
  - Warmup period: 2.0 seconds (ignore initial silence)
  - Silence threshold: 1.5 seconds
  - Energy floor: 500 (RMS threshold)

### 3️⃣ Combined Strategy (DEFAULT)
- **Method:** Parallel execution of both strategies
- **Priority:** Beep detection (fast lane) → Silence detection (fallback)
- **Best for:** Maximum robustness across all voicemail types

---

## 🏗️ Architecture

### Core Components

```
┌─────────────────────────────────────────────────┐
│          StreamingVoicemailDropper              │
│  (Main orchestrator + Deepgram integration)     │
└─────────────────┬───────────────────────────────┘
                  │
                  ├─> stream_audio_file()
                  │   (Simulates real-time streaming)
                  │
                  ├─> Strategy Engine (Pluggable)
                  │   │
                  │   ├─> BeepStrategy
                  │   │   └─> FFT frequency analysis
                  │   │
                  │   ├─> SilenceStrategy
                  │   │   └─> RMS energy tracking
                  │   │
                  │   └─> CombinedStrategy
                  │       └─> Beep (priority) + Silence (fallback)
                  │
                  └─> Deepgram API (optional)
                      └─> Speech-to-text for annotation
```

### Data Flow

```
Audio File (WAV)
    ↓
[Stream in 50ms chunks]
    ↓
[Process each chunk through Strategy Engine]
    ↓
[Beep detected? OR Silence detected?]
    ↓
[Record timestamp + Stop streaming]
    ↓
[Optional: Transcribe full audio with Deepgram]
    ↓
[Output results]
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Deepgram API key ([Get one free here](https://deepgram.com))
- Audio files in WAV format

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd retape

# Install dependencies
pip install numpy soundfile deepgram-sdk python-dotenv

# Create .env file
echo "DEEPGRAM_API_KEY=your_api_key_here" > .env
```

### Directory Structure

```
retape/
├── main.py                          # Main application
├── .env                             # API keys (create this)
├── voicemail_audio_files/           # Input audio files (create this folder)
│   ├── voicemail_001.wav
│   ├── voicemail_002.wav
│   └── ...
└── README.md
```

### Running the Application

```bash
python main.py
```

---

## 📊 Output Example

```
>> Streaming Voicemail Dropper (Strategy: COMBINED)
>> Found 7 audio files

================================================================================

[CALL] voicemail_001.wav
[DROP] at 3.45s - [BEEP] Beep Detected (~823Hz) (18 words)

[CALL] voicemail_002.wav
[DROP] at 5.12s - [SILENCE] Silence Timeout (1.50s) (24 words)

[CALL] voicemail_003.wav
[DROP] at 2.89s - [BEEP] Beep Detected (~795Hz) (12 words)

================================================================================
FINAL STREAMING RESULTS
================================================================================
| File                     | Drop Time | Method                    | Words |
|------------------------------------------------------------------------------|
| voicemail_001.wav        |     3.45s | [BEEP] Beep Detected      |    18 |
| voicemail_002.wav        |     5.12s | [SILENCE] Silence Timeout |    24 |
| voicemail_003.wav        |     2.89s | [BEEP] Beep Detected      |    12 |
================================================================================

SUMMARY:
   * Strategy mode: combined
   * Average drop time: 3.82s
   * Total words transcribed: 54
   * Files processed: 3/3
```

---

## ⚙️ Configuration

Modify these constants in `main.py` to tune behavior:

### Streaming Configuration
```python
CHUNK_DURATION_MS = 50        # Process audio in 50ms chunks (real-time simulation)
DEFAULT_STRATEGY = "combined"  # Options: 'silence', 'beep', 'combined'
```

### Silence Detection Tuning
```python
SILENCE_WARMUP = 2.0          # Ignore first N seconds (greeting start)
SILENCE_THRESHOLD = 1.5       # Seconds of silence before trigger
SILENCE_ENERGY_FLOOR = 500    # RMS amplitude threshold
```

### Beep Detection Tuning
```python
BEEP_TARGET_FREQ = 800        # Target beep frequency (Hz)
BEEP_TOLERANCE = 100          # Frequency range (±Hz)
BEEP_MIN_DURATION = 0.15      # Minimum beep duration (seconds)
BEEP_MIN_AMP = 2000           # Minimum FFT magnitude
```

---

## 🔬 Technical Deep Dive

### How Silence Detection Works

1. **Calculate RMS Energy** for each audio chunk:
   ```
   RMS = sqrt(mean(audio_samples²))
   ```

2. **Compare to threshold:**
   - If RMS < 500 → Count as "silence"
   - If RMS ≥ 500 → Reset silence counter

3. **Trigger when:**
   - Silence duration ≥ 1.5 seconds
   - AND current time > 2.0 seconds (warmup period)

**Analogy:** Like waiting for someone to stop talking. If they pause for 1.5 seconds, you assume they're done.

---

### How Beep Detection Works

1. **Apply FFT** to convert time-domain audio → frequency-domain:
   ```python
   spectrum = np.fft.rfft(audio_chunk)
   frequencies = np.fft.rfftfreq(len(chunk), 1/sample_rate)
   ```

2. **Find peak frequency:**
   ```python
   peak_idx = np.argmax(abs(spectrum))
   peak_freq = frequencies[peak_idx]
   ```

3. **Check if it matches beep characteristics:**
   - Frequency: 700-900 Hz range
   - Amplitude: > 2000
   - Duration: ≥ 0.15 seconds

**Analogy:** Like unmixing a smoothie to identify individual fruits by color.

---

### Why FFT?

**FFT (Fast Fourier Transform)** decomposes complex audio signals into constituent frequencies.

**Example:**
```
Mixed Audio: [complex waveform]
              ↓ FFT
Frequency Spectrum:
  100 Hz: ▂     (quiet)
  800 Hz: █████ (LOUD - beep detected!)
  1500 Hz: ▃    (quiet)
```

**Real-world applications:**
- Music identification (Shazam)
- Noise cancellation
- Autotune
- Audio compression (MP3)

---

## 🎓 Edge Cases Handled

| Edge Case | Solution |
|-----------|----------|
| **No beep in voicemail** | Silence strategy acts as fallback |
| **Long pauses during greeting** | 2-second warmup period prevents premature triggering |
| **Background noise** | Energy floor (RMS > 500) filters out low-level noise |
| **Short beep-like sounds** | Minimum duration requirement (0.15s) |
| **Non-standard beep frequencies** | ±100 Hz tolerance around 800 Hz target |
| **Very quiet audio** | Amplitude threshold prevents false positives |

---

## 🧪 Testing Strategy

### Manual Testing
1. Place test WAV files in `voicemail_audio_files/`
2. Run `python main.py`
3. Review drop timestamps and detection methods

### Expected Outcomes
- **Voicemails with beeps:** Should detect beep (~3-5s typically)
- **Voicemails without beeps:** Should detect silence timeout
- **Short greetings:** Should trigger faster
- **Long greetings:** Should wait for natural pause

### Validation
- Check that detected timestamp is AFTER the greeting ends
- Verify method used ([BEEP] vs [SILENCE])
- Compare word count with audio duration (sanity check)

---

## 📈 Performance Characteristics

### Time Complexity
- **Streaming:** O(n) where n = audio duration
- **FFT per chunk:** O(m log m) where m = chunk size
- **Overall:** Linear with audio length

### Space Complexity
- **Memory:** O(1) - only processes one 50ms chunk at a time
- **No buffering:** Suitable for real-time phone systems

### Latency
- **Detection delay:** ~50-200ms after actual event
- **Total processing:** <1s per audio file (excluding transcription)

---

## 🔮 Future Enhancements

### AI-Based Improvements
1. **LLM Integration:**
   - Detect end-of-greeting phrases ("leave a message", "after the beep")
   - Handle multi-language greetings

2. **Machine Learning:**
   - Train classifier on labeled voicemail datasets
   - Adaptive threshold tuning based on call history

3. **Advanced Audio Processing:**
   - Multi-frequency beep detection (handle harmonics)
   - Voice activity detection (VAD) models
   - Background noise suppression

### Operational Improvements
- **A/B Testing Framework:** Compare strategy effectiveness
- **Compliance Reporting:** Track success rates
- **Real-time Monitoring:** Dashboard for live call analysis

---

## 🛠️ Dependencies

```
numpy==1.24.0          # Audio processing, FFT, RMS calculations
soundfile==0.12.1      # Audio file I/O and duration extraction
deepgram-sdk==3.0.0    # Speech-to-text transcription
python-dotenv==1.0.0   # Environment variable management
```

Install all:
```bash
pip install -r requirements.txt
```

---

## 🐛 Troubleshooting

### Issue: "DEEPGRAM_API_KEY not found"
**Solution:** Create a `.env` file with:
```
DEEPGRAM_API_KEY=your_actual_api_key
```

### Issue: "Directory 'voicemail_audio_files' not found"
**Solution:** Create the directory and add WAV files:
```bash
mkdir voicemail_audio_files
# Copy your .wav files into this directory
```

### Issue: All detections show "[NO_TRIGGER_FALLBACK]"
**Possible causes:**
1. Audio files are corrupted or wrong format
2. Detection thresholds are too strict
3. Audio is too quiet (normalize volume)

**Solution:** Lower thresholds:
```python
SILENCE_THRESHOLD = 1.0  # Reduce from 1.5
BEEP_MIN_AMP = 1000      # Reduce from 2000
```

### Issue: Triggering too early
**Solution:** Increase warmup period:
```python
SILENCE_WARMUP = 3.0  # Increase from 2.0
```

---

## 📚 Key Concepts Explained

### For Node.js Developers

| Python Concept | Node.js Equivalent |
|----------------|-------------------|
| `async def` | `async function` |
| `asyncio.run()` | Top-level `await` or `.then()` |
| `numpy` arrays | `Float32Array`, `Int16Array` |
| Generators (`yield`) | Async iterators, `Readable` streams |
| Class inheritance | ES6 class inheritance |
| `dotenv` | `require('dotenv').config()` |

### Audio Processing 101

**Sample Rate:** Number of audio measurements per second (e.g., 16000 Hz = 16000 samples/sec)

**RMS (Root Mean Square):** Mathematical way to measure "average loudness"
```
RMS = sqrt((sample₁² + sample₂² + ... + sampleₙ²) / n)
```

**FFT (Fast Fourier Transform):** Converts time-domain audio (amplitude over time) to frequency-domain (which frequencies are present)

---

## 📝 License

This is a take-home assignment for ClearPath Finance. Code is provided for educational purposes.

---

## 👥 Author

**Assignment Submission for ClearPath Finance**

---

## 🙏 Acknowledgments

- **Deepgram** for speech-to-text API
- **NumPy** for efficient numerical computing
- **SoundFile** for audio I/O

---

## 📞 Questions?

For technical questions about this implementation, please refer to the code comments or reach out through the submission form.

---

**Last Updated:** December 2024
