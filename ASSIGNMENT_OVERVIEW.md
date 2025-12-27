# 📞 Assignment Overview: Drop Compliant Voicemails

> **ClearPath Finance Take-Home Assignment - Complete Summary**

---

## 🎯 The Assignment in 60 Seconds

**Company:** ClearPath Finance (credit card debt management)

**Problem:** When calling customers and reaching voicemail, we need to leave a **legally compliant message** that includes:
- Company name
- Return phone number

**The Catch:** If there's a beep, anything spoken BEFORE the beep gets erased!

**Your Task:** Build a system that detects when to start playing the message so the customer hears everything.

**Input:** 7 voicemail audio files (streaming, not pre-loaded)

**Output:** Timestamp for when to start message for each file

---

## 🚨 Why This Matters (The Legal Risk)

### ❌ Non-Compliant Message

```
Timeline:
─────────────────────────────────────────────────────────
"Hi, this is ClearPath Finance calling—" [BEEP] "—please call 800-555-0199"
                                          ↑
                             Everything before beep is ERASED

Customer Hears: "—please call 800-555-0199"
Missing: Company name
Result: Legal violation! Could face FCC fines
```

### ✅ Compliant Message

```
Timeline:
─────────────────────────────────────────────────────────
"...leave a message after the beep" [BEEP] "Hi, this is ClearPath Finance calling about your account. Please call 800-555-0199"
                                      ↑
                                Start speaking HERE

Customer Hears: Full message with company name AND phone number
Result: Compliant! ✓
```

---

## 🧩 The Solution (3-Part Strategy)

### Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                   AUDIO FILE (.wav)                      │
│                          ↓                                │
│              ┌─────────────────────┐                     │
│              │  Stream in 50ms     │  ← Like buffering   │
│              │  chunks (real-time) │     a video         │
│              └──────────┬──────────┘                     │
│                         ↓                                 │
│         ┌───────────────────────────────┐                │
│         │   COMBINED DETECTION ENGINE   │                │
│         │                                │                │
│         │  ┌──────────┐  ┌───────────┐ │                │
│         │  │   BEEP   │  │  SILENCE  │ │                │
│         │  │ DETECTOR │  │ DETECTOR  │ │                │
│         │  │          │  │           │ │                │
│         │  │ FFT      │  │ RMS       │ │                │
│         │  │ 800 Hz   │  │ Energy    │ │                │
│         │  └─────┬────┘  └─────┬─────┘ │                │
│         │        └──────┬───────┘       │                │
│         │               ↓                │                │
│         │    First to detect wins!      │                │
│         └───────────────┬───────────────┘                │
│                         ↓                                 │
│              ┌─────────────────────┐                     │
│              │  TIMESTAMP OUTPUT   │                     │
│              │  (e.g., 3.45s)      │                     │
│              └─────────────────────┘                     │
└──────────────────────────────────────────────────────────┘
```

---

## 🔬 The Two Detection Methods

### Method 1: Beep Detection (Primary) 🔊

**How it works:**
1. Use FFT to analyze frequencies in audio
2. Look for sustained tone around 800 Hz
3. Must last at least 0.15 seconds
4. Trigger immediately when detected

**Think of it like:**
- A guitar tuner detecting a specific note
- Or how Shazam identifies songs by their "audio fingerprint"

**When it's best:**
- Standard carrier voicemails (AT&T, Verizon, etc.)
- Google Voice
- Any voicemail with a beep

**Pros:** ✅ Very accurate, fast (150ms latency)
**Cons:** ❌ Doesn't work if there's no beep

---

### Method 2: Silence Detection (Fallback) 🔇

**How it works:**
1. Measure audio "loudness" (RMS energy)
2. If RMS < 500 for 1.5 seconds → Person stopped talking
3. Wait 2 seconds before checking (warmup period)
4. Trigger when silence threshold met

**Think of it like:**
- Waiting for someone to finish talking
- If they pause for 1.5 seconds, it's your turn to speak

**When it's best:**
- Voicemails without beeps
- Custom recordings
- Unusual greeting formats

**Pros:** ✅ Works without beeps, universal fallback
**Cons:** ⚠️ Slower (1.5s delay), can be fooled by pauses

---

### Method 3: Combined (What We Use) 🎯

**Strategy:** Run both in parallel, first to trigger wins!

```
For each 50ms audio chunk:
┌────────────────────────────────┐
│  1. Check for beep (800 Hz)    │ ← Priority
│     └─ Found? → TRIGGER!       │
│                                 │
│  2. Check for silence (RMS)    │ ← Fallback
│     └─ 1.5s quiet? → TRIGGER!  │
│                                 │
│  3. Neither? → Next chunk      │
└────────────────────────────────┘
```

**Why this is smart:**
- ✅ Fast when there's a beep (most cases)
- ✅ Reliable when there's no beep (edge cases)
- ✅ Robust to different voicemail types

---

## 📊 Key Concepts Explained Simply

### What is FFT (Fast Fourier Transform)?

**Simple explanation:** It "unmixes" audio to show individual frequencies

**Visual analogy:**

```
Mixed Smoothie              Unmixed Ingredients
(Time domain)              (Frequency domain)

   [Purple]                 🍓 Strawberries
     ↓                      🍌 Bananas
  Apply FFT     ──────→     🫐 Blueberries
     ↓
Identify each fruit by "frequency" (color)
```

**In audio:**

```
Mixed Audio                 Separated Frequencies
╱╲╱╲╱╲╱╲                          │
 ╲╱ ╲╱ ╲╱          FFT      8000│        █  ← Beep (800 Hz)
  ────────        ────→          │    ▃   █
                                 │  ▂ █ ▂ █ ▂
                            1000│ ▁█▁█▁█▁█▁█▁
                                └────────────→ Hz
                                   400 800 1200
```

---

### What is RMS (Root Mean Square)?

**Simple explanation:** A way to measure "loudness"

**Formula:** `RMS = √(average(all_samples²))`

**What the numbers mean:**

| RMS Value | What It Sounds Like |
|-----------|---------------------|
| 0 - 300 | Dead silence, empty room |
| 300 - 800 | Quiet whisper, background noise |
| 800 - 3000 | Normal speaking voice |
| 3000+ | Loud voice, shouting, beep tones |

**How we use it:**

```python
if rms < 500:
    # It's quiet → Count as silence
    silence_duration += 0.05  # Add 50ms
else:
    # Someone's talking → Reset counter
    silence_duration = 0.0

if silence_duration >= 1.5:
    print("Greeting over! Start message now!")
```

---

## 🎬 Complete Example Walkthrough

### Input: voicemail_001.wav

**Audio content:**
> "Hi, you've reached Mike Rodriguez. I can't take your call right now. Please leave your name and number after the beep. [BEEP]"

**Processing timeline:**

```
Time  | What's Playing           | RMS  | Peak Freq | Detection
------|-------------------------|------|-----------|------------
0.0s  | "Hi, you've"            | 2900 | 420 Hz    | Warmup
0.5s  | "reached Mike"          | 3200 | 510 Hz    | Warmup
1.0s  | "Rodriguez..."          | 2100 | 380 Hz    | Warmup
1.5s  | "I can't take"          | 2500 | 460 Hz    | Warmup
2.0s  | "your call"             | 1900 | 390 Hz    | Listening
2.5s  | "right now"             | 2200 | 520 Hz    | Listening
3.0s  | "Please leave"          | 2400 | 430 Hz    | Listening
3.5s  | [BEEEEEEEEP]            | 8700 | 812 Hz ✓  | Beep: 0.05s
3.55s | [BEEEEEEEEP]            | 8900 | 805 Hz ✓  | Beep: 0.10s
3.60s | [BEEEEEEEEP]            | 8600 | 798 Hz ✓  | Beep: 0.15s ✓
                                                   └─→ TRIGGER!
```

**Output:**

```json
{
  "filename": "voicemail_001.wav",
  "drop_time": 3.60,
  "method": "[BEEP] Beep Detected (~805Hz)",
  "words": 23,
  "transcript": "Hi, you've reached Mike Rodriguez. I can't..."
}
```

**What this means:**
- Start playing your message at **3.60 seconds** into the call
- Detection method: **Beep found** at ~805 Hz
- Greeting had **23 words** (from AI transcription)

---

## ⚙️ Tunable Parameters

### Configuration Settings (with defaults)

```python
# Streaming
CHUNK_DURATION_MS = 50        # Process in 50ms pieces

# Silence Detection
SILENCE_WARMUP = 2.0          # Ignore first 2 seconds
SILENCE_THRESHOLD = 1.5       # Need 1.5s of silence
SILENCE_ENERGY_FLOOR = 500    # RMS below this = silent

# Beep Detection
BEEP_TARGET_FREQ = 800        # Look for 800 Hz tone
BEEP_TOLERANCE = 100          # Accept 700-900 Hz
BEEP_MIN_DURATION = 0.15      # Beep must last 150ms
BEEP_MIN_AMP = 2000           # Must be loud enough
```

### Quick Tuning Guide

**Triggering too early?**
```python
SILENCE_WARMUP = 3.0  # Increase warmup period
```

**Triggering too late?**
```python
SILENCE_THRESHOLD = 1.0  # Reduce silence requirement
```

**Missing beeps?**
```python
BEEP_MIN_AMP = 1500  # Lower amplitude threshold
```

**False beep detections?**
```python
BEEP_MIN_DURATION = 0.20  # Require longer confirmation
```

---

## 🧪 Edge Cases Handled

| Scenario | How We Handle It |
|----------|------------------|
| **No beep in voicemail** | Silence detection catches it |
| **Long pauses during greeting** | Warmup period (2s) prevents early trigger |
| **Background music** | Amplitude threshold filters noise |
| **Very short greetings** | Warmup ensures minimum 2s delay |
| **Multiple beeps** | First beep wins (earliest detection) |
| **Non-standard beep frequency** | ±100 Hz tolerance (700-900 Hz) |
| **Quiet audio** | Configurable RMS threshold |
| **Very long greetings** | Both strategies keep checking |

---

## 📈 Expected Results

### By Voicemail Type

| Type | Expected Method | Typical Time |
|------|----------------|--------------|
| AT&T/Verizon carrier | `[BEEP]` | 3-5s |
| Google Voice | `[BEEP]` | 2-4s |
| Custom + beep | `[BEEP]` | 5-10s |
| Custom, no beep | `[SILENCE]` | 6-12s |
| Short greeting | `[SILENCE]` | 3-4s |
| Professional auto-attendant | `[BEEP]` | 8-15s |

---

## 🎓 Technologies Used

### Core Libraries

**NumPy:** Numerical computing (FFT, RMS calculations)
```python
import numpy as np
spectrum = np.fft.rfft(audio_chunk)  # Frequency analysis
```

**SoundFile:** Audio file I/O
```python
import soundfile as sf
with sf.SoundFile(filepath) as f:
    duration = len(f) / f.samplerate
```

**Deepgram:** AI speech-to-text (for transcription)
```python
from deepgram import DeepgramClient
response = client.listen.v1.media.transcribe_file(audio)
```

**Asyncio:** Asynchronous processing
```python
import asyncio
async def process_audio_file(filename):
    # Process asynchronously
```

---

## 📝 Deliverables Checklist

✅ **Code**
- [main.py](main.py) - Complete implementation
- Uses Python (as allowed by assignment)
- Modular, commented, readable

✅ **Explanation Paragraph**
- See "How My Logic Works" section below

✅ **Demo**
- Run `python main.py` to see live output
- Processes all 7 audio files
- Shows timestamps and detection methods

✅ **Documentation**
- [README.md](README.md) - Project overview
- [EXPLANATION.md](EXPLANATION.md) - Beginner guide
- [TECHNICAL_SUMMARY.md](TECHNICAL_SUMMARY.md) - Technical deep dive
- [QUICK_START.md](QUICK_START.md) - Setup guide

---

## 💡 How My Logic Works (Explanation Paragraph)

My solution simulates real-time phone call streaming by processing audio in 50ms chunks, running two detection algorithms in parallel. The **beep detector** uses FFT (Fast Fourier Transform) to analyze frequency spectrums, triggering when it finds a sustained tone around 800 Hz (±100 Hz) lasting at least 150ms—this catches standard voicemail beeps with ~200ms latency. The **silence detector** tracks RMS (Root Mean Square) energy as a loudness measure, triggering after 1.5 seconds of continuous low energy (RMS < 500) following a 2-second warmup period—this handles voicemails without beeps. The **combined strategy** gives priority to beep detection (faster, more reliable) while using silence detection as a universal fallback, ensuring compliance regardless of voicemail format. Optional Deepgram transcription provides word counts and greeting text for validation and debugging, though it's not used for the drop decision itself since real-time detection must happen during streaming.

---

## 🎯 What We're Being Evaluated On

Per the assignment:

> "This is a learning-focused assignment. We are not expecting a perfect solution."

### What They Care About:

1. ✅ **How you think**
   - Demonstrated through: Strategy pattern, parallel detection
   - Shows: Systematic problem-solving

2. ✅ **How you handle edge cases**
   - Demonstrated through: Warmup periods, fallback strategies, configurable thresholds
   - Shows: Awareness of real-world complexity

3. ✅ **How clearly you explain logic**
   - Demonstrated through: Extensive documentation, code comments
   - Shows: Communication skills

### What They DON'T Expect:

- ❌ Perfect accuracy (this is a hard problem)
- ❌ Production-ready scalability
- ❌ 100% coverage of every possible voicemail
- ❌ Machine learning / complex AI

---

## 🚀 Running the Demo

### Basic Run

```bash
python main.py
```

### Expected Output

```
>> Streaming Voicemail Dropper (Strategy: COMBINED)
>> Found 7 audio files

================================================================================

[CALL] voicemail_001.wav
[DROP] at 3.45s - [BEEP] Beep Detected (~823Hz) (18 words)

[CALL] voicemail_002.wav
[DROP] at 5.12s - [SILENCE] Silence Timeout (1.50s) (24 words)

... (continues for all files) ...

================================================================================
FINAL STREAMING RESULTS
================================================================================
| File                     | Drop Time | Method                    | Words |
|------------------------------------------------------------------------------|
| voicemail_001.wav        |     3.45s | [BEEP] Beep Detected      |    18 |
| voicemail_002.wav        |     5.12s | [SILENCE] Silence Timeout |    24 |
... (all files) ...

SUMMARY:
   * Strategy mode: combined
   * Average drop time: 4.29s
   * Total words transcribed: 154
   * Files processed: 7/7
```

---

## 📚 Documentation Navigation

```
Start Here:
├─ 📄 ASSIGNMENT_OVERVIEW.md (You are here)
│  └─ "What is this assignment about?"
│
For Implementation:
├─ 📄 QUICK_START.md
│  └─ "How do I run this?"
│
For Understanding:
├─ 📄 EXPLANATION.md
│  └─ "How does it work? (Beginner-friendly)"
│
For Deep Dive:
├─ 📄 TECHNICAL_SUMMARY.md
│  └─ "Technical details and algorithms"
│
For Users:
└─ 📄 README.md
   └─ "Project overview and usage"
```

---

## 🎉 Conclusion

This assignment demonstrates:

✅ **Real-time audio processing** (streaming vs batch)
✅ **Signal processing fundamentals** (FFT, RMS)
✅ **Practical AI integration** (Deepgram STT)
✅ **Robust system design** (multiple strategies, fallbacks)
✅ **Legal compliance awareness** (FCC regulations)
✅ **Clean code architecture** (Strategy pattern, separation of concerns)

**The solution balances:**
- Speed (beep detection) vs Reliability (silence fallback)
- Accuracy (conservative thresholds) vs Latency (minimize wait)
- Simplicity (understandable logic) vs Robustness (handles edge cases)

---

**Ready to explore the code?** Start with [QUICK_START.md](QUICK_START.md)!

**Want to understand deeply?** Read [EXPLANATION.md](EXPLANATION.md)!

**Need technical details?** Check [TECHNICAL_SUMMARY.md](TECHNICAL_SUMMARY.md)!

---

**Good luck with your submission! 🚀**
