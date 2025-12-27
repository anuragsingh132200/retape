# 🔬 Technical Summary: Voicemail Compliance System

> **Quick reference for understanding the implementation approach**

---

## 🎯 Problem Summary

**Goal:** Detect the optimal timestamp to start playing a compliant voicemail message

**Constraint:** Message must include company name AND phone number that the customer can hear

**Challenge:** Voicemail beeps erase anything spoken before them

---

## 🧩 Solution Architecture

### Three-Strategy Approach

```
┌─────────────────────────────────────────────────────────────┐
│                 STREAMING AUDIO PROCESSOR                    │
│                                                              │
│  Input: WAV file → Stream in 50ms chunks                    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           COMBINED STRATEGY (Default)              │    │
│  │                                                     │    │
│  │  ┌──────────────────────┐  ┌──────────────────┐  │    │
│  │  │  BEEP DETECTION      │  │ SILENCE DETECTION│  │    │
│  │  │  (Priority/Fast)     │  │  (Fallback)      │  │    │
│  │  │                      │  │                  │  │    │
│  │  │ • FFT Analysis       │  │ • RMS Energy     │  │    │
│  │  │ • 700-900 Hz         │  │ • < 500 RMS      │  │    │
│  │  │ • Duration: 0.15s    │  │ • Duration: 1.5s │  │    │
│  │  └──────────────────────┘  └──────────────────┘  │    │
│  │                                                     │    │
│  │  First to trigger wins → Record timestamp          │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  Output: Timestamp + Detection Method                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Algorithm Comparison

| Feature | Beep Detection | Silence Detection | Combined |
|---------|---------------|-------------------|----------|
| **Method** | FFT frequency analysis | RMS energy tracking | Both in parallel |
| **Works with beep** | ✅ Excellent | ⚠️ Delayed by 1.5s | ✅ Excellent |
| **Works without beep** | ❌ Never triggers | ✅ Good | ✅ Good |
| **Latency** | ~150ms after beep | ~1.5s after silence | Minimum of both |
| **False positives** | Low (with amplitude threshold) | Medium (voices vary) | Low |
| **Best for** | Standard voicemails | No-beep voicemails | **Production use** |

---

## 🔢 Key Parameters & Tuning Guide

### Silence Detection Parameters

```python
SILENCE_WARMUP = 2.0          # Ignore first N seconds
SILENCE_THRESHOLD = 1.5       # Seconds of silence needed
SILENCE_ENERGY_FLOOR = 500    # RMS threshold for "silence"
```

**Tuning Guide:**

| Symptom | Adjustment | Reason |
|---------|-----------|--------|
| Triggering too early | ↑ `SILENCE_WARMUP` to 3.0s | Greeting still playing |
| Triggering too late | ↓ `SILENCE_THRESHOLD` to 1.0s | Being too conservative |
| Missing quiet greetings | ↑ `SILENCE_ENERGY_FLOOR` to 800 | Audio is naturally quiet |
| False triggers on pauses | ↓ `SILENCE_ENERGY_FLOOR` to 300 | Background noise too high |

---

### Beep Detection Parameters

```python
BEEP_TARGET_FREQ = 800        # Target frequency (Hz)
BEEP_TOLERANCE = 100          # Acceptable range (±Hz)
BEEP_MIN_DURATION = 0.15      # Minimum beep length (seconds)
BEEP_MIN_AMP = 2000           # FFT magnitude threshold
```

**Tuning Guide:**

| Symptom | Adjustment | Reason |
|---------|-----------|--------|
| Missing beeps | ↓ `BEEP_MIN_AMP` to 1500 | Beeps are quieter |
| False beep detection | ↑ `BEEP_MIN_AMP` to 3000 | Background tones triggering |
| Detecting wrong tones | ↓ `BEEP_TOLERANCE` to 50 | Tighten frequency match |
| Missing varied beeps | ↑ `BEEP_TOLERANCE` to 150 | Beeps vary more |
| Detecting brief tones | ↑ `BEEP_MIN_DURATION` to 0.20 | Need longer confirmation |

---

## 🎓 Core Algorithms Explained

### 1. RMS Energy Calculation

**Purpose:** Measure audio "loudness" to detect silence

**Formula:**
```
RMS = √(Σ(sample²) / n)
```

**Implementation:**
```python
rms = np.sqrt(np.mean(chunk.astype(float) ** 2))

if rms < SILENCE_ENERGY_FLOOR:
    silence_duration += chunk_duration
```

**What the numbers mean:**

| RMS Value | Interpretation | Example |
|-----------|---------------|---------|
| 0 - 300 | Dead silence | Empty voicemail |
| 300 - 800 | Quiet/background noise | Faint speaking |
| 800 - 3000 | Normal speech | Typical voicemail greeting |
| 3000+ | Loud speech/music | Shouting, beep tones |

---

### 2. FFT Frequency Analysis

**Purpose:** Detect specific tone frequencies (beeps)

**How it works:**

```
Time Domain              Frequency Domain
(amplitude over time)    (energy per frequency)

  ╱╲╱╲╱╲╱╲                     │
 ╱      ╲                 8000 │        █  ← 800 Hz beep
╱        ╲                     │        █     (dominant)
          ╲               4000 │    ▃   █
           ╲                   │  ▂ █ ▂ █ ▂
────────────╲──→ time     1000 │ ▁█▁█▁█▁█▁█▁
                               └────────────→ Hz
                                  400 800 1200
         FFT
         ───→
```

**Implementation:**
```python
spectrum = np.fft.rfft(chunk)              # Time → Frequency
freqs = np.fft.rfftfreq(len(chunk), 1/sr)  # Frequency axis
mags = np.abs(spectrum)                     # Magnitudes

peak_idx = np.argmax(mags)                  # Find loudest
peak_freq = freqs[peak_idx]                 # Its frequency

is_beep = (BEEP_FREQ_MIN <= peak_freq <= BEEP_FREQ_MAX) and (peak_amp > BEEP_MIN_AMP)
```

**Real-world frequencies:**

| Frequency | Sound |
|-----------|-------|
| 261 Hz | Middle C (piano) |
| 440 Hz | A note (tuning fork) |
| **700-900 Hz** | **Voicemail beeps** |
| 1000 Hz | High-pitched tone |
| 2000+ Hz | Very high tones |

---

### 3. Streaming Processing

**Purpose:** Simulate real-time phone call (not batch processing)

```
Traditional Approach (NOT used):
─────────────────────────────────
1. Download entire audio file
2. Analyze whole file
3. Decide timestamp

❌ Problem: Real phone calls don't work this way


Streaming Approach (What we do):
─────────────────────────────────
1. Read 50ms → Process → Decision
2. Read 50ms → Process → Decision
3. Read 50ms → Process → TRIGGER!
4. Stop

✅ Advantage: Works in real-time
```

**Implementation:**
```python
def stream_audio_file(filepath, chunk_duration_ms=50):
    while True:
        chunk = read_next_chunk()  # Get 50ms
        if not chunk:
            break
        yield chunk, sample_rate, current_time
        current_time += 0.05  # Advance 50ms

# Usage
for chunk, sr, time in stream_audio_file("audio.wav"):
    should_drop, reason = engine.process(chunk, sr, time)
    if should_drop:
        break  # Stop immediately when triggered
```

---

## 🧪 Edge Cases & Handling

| Edge Case | Detection Method | Handling Strategy |
|-----------|-----------------|-------------------|
| **No beep in greeting** | Silence fallback | Triggers after 1.5s silence |
| **Multiple beeps** | First beep wins | Stops at first 800Hz tone |
| **Long pauses in greeting** | Warmup period | Ignores silence in first 2s |
| **Background music** | Amplitude threshold | Only loud, sustained tones count |
| **Very short greetings** | Warmup prevents early trigger | Minimum 2s before any trigger |
| **Very long greetings** | Both strategies active | Will eventually trigger on silence |
| **Quiet audio** | Configurable RMS threshold | Tune `ENERGY_FLOOR` down |
| **Noisy audio** | Frequency selectivity | FFT isolates specific tones |
| **Non-standard beep freq** | Tolerance range | ±100 Hz catches 700-900 Hz |

---

## 📈 Performance Characteristics

### Time Complexity

| Operation | Complexity | Per What? |
|-----------|-----------|-----------|
| **Streaming** | O(n) | Audio duration |
| **RMS calculation** | O(m) | Chunk size (800 samples) |
| **FFT** | O(m log m) | Chunk size |
| **Total per chunk** | O(m log m) | ~800 samples |

**Real-world performance:**
- Processing a 10-second audio file: ~200 chunks
- Per chunk: ~0.5ms processing time
- Total: ~100ms processing time (excluding transcription)

---

### Space Complexity

| Component | Memory Usage |
|-----------|-------------|
| **Single chunk** | 800 samples × 2 bytes = 1.6 KB |
| **FFT output** | ~400 complex numbers = 3.2 KB |
| **Strategy state** | 2-3 float counters = 24 bytes |
| **Total active** | ~5 KB per stream |

**Why this matters:** Can handle thousands of concurrent calls with minimal RAM

---

## 🔄 Decision Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    START PROCESSING                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │  Read Next 50ms Chunk  │
         └────────┬───────────────┘
                  │
                  ▼
         ┌────────────────────────┐
         │ Current Time < 2.0s?   │  ← Warmup period
         └────┬───────────────┬───┘
             Yes             No
              │               │
              │               ▼
              │    ┌──────────────────────┐
              │    │   Beep Detection:    │
              │    │   Apply FFT          │
              │    └──────┬───────────────┘
              │           │
              │           ├─ Peak freq 700-900 Hz?
              │           ├─ Amplitude > 2000?
              │           └─ Duration > 0.15s?
              │                   │
              │           ┌───────┴────────┐
              │          Yes              No
              │           │                │
              │           ▼                ▼
              │    ┌──────────┐   ┌──────────────────┐
              │    │ TRIGGER! │   │ Silence Detection│
              │    │ (Beep)   │   │ Calculate RMS    │
              │    └──────────┘   └──────┬───────────┘
              │                           │
              │                   ┌───────┴────────┐
              │                  RMS < 500?
              │                   └───┬───────┬────┘
              │                      Yes     No
              │                       │       │
              │                       ▼       │
              │              Silence > 1.5s?  │
              │                   └─┬────┬────┘
              │                    Yes  No
              │                     │    │
              │                     ▼    │
              │              ┌──────────┐│
              │              │ TRIGGER! ││
              │              │(Silence) ││
              │              └──────────┘│
              │                          │
              └──────────────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  More Audio Chunks?  │
                  └──────┬───────────┬───┘
                        Yes         No
                         │           │
                         └───────────┤
                                     ▼
                          ┌──────────────────┐
                          │ Record Timestamp │
                          │ Return Results   │
                          └──────────────────┘
```

---

## 🎯 Strategy Selection Guide

### When to Use Each Strategy

**Use `strategy="beep"`:**
```python
DEFAULT_STRATEGY = "beep"
```
- All voicemails known to have beeps
- Low-latency critical
- Don't care about no-beep voicemails

**Use `strategy="silence"`:**
```python
DEFAULT_STRATEGY = "silence"
```
- Testing silence detection specifically
- Known no-beep environment
- Debugging silence thresholds

**Use `strategy="combined"` (RECOMMENDED):**
```python
DEFAULT_STRATEGY = "combined"
```
- **Production environments** ✅
- Maximum robustness
- Unknown voicemail types
- Real-world deployment

---

## 📊 Expected Results by Voicemail Type

| Voicemail Type | Expected Trigger | Expected Method | Typical Time |
|----------------|-----------------|-----------------|--------------|
| Standard carrier (AT&T, Verizon) | Beep | `[BEEP]` | 3-5s |
| Google Voice | Beep | `[BEEP]` | 2-4s |
| Custom greeting + beep | Beep | `[BEEP]` | 5-10s |
| Custom greeting, no beep | Silence | `[SILENCE]` | 6-12s |
| Very short greeting | Silence | `[SILENCE]` | 3-4s |
| Professional auto-attendant | Beep | `[BEEP]` | 8-15s |

---

## 🔍 Debugging Guide

### Common Issues & Solutions

**Issue:** All files trigger at same time
```
Symptom: Every file shows drop_time ~2.0s
Cause: Warmup period ending, silence immediately triggering
Fix: Increase SILENCE_THRESHOLD or WARMUP
```

**Issue:** No triggers, all show `[NO_TRIGGER_FALLBACK]`
```
Symptom: drop_time = file_duration for all files
Cause: Thresholds too strict
Fix: Lower BEEP_MIN_AMP (try 1000) and SILENCE_ENERGY_FLOOR (try 300)
```

**Issue:** Triggers too early (during greeting)
```
Symptom: drop_time < 2s, during speech
Cause: Warmup too short or thresholds too loose
Fix: Increase SILENCE_WARMUP to 3.0s
```

**Issue:** Beep never detected
```
Symptom: Only [SILENCE] triggers, never [BEEP]
Cause: Beep frequency or amplitude mismatch
Fix: Add logging to check peak frequencies:
     print(f"Peak freq: {peak_freq} Hz, amp: {peak_amp}")
```

---

## 🚀 Production Deployment Considerations

### Configuration for Different Environments

**Conservative (Prioritize Compliance):**
```python
SILENCE_WARMUP = 3.0         # Wait longer before considering silence
SILENCE_THRESHOLD = 2.0      # Require more silence
BEEP_MIN_DURATION = 0.20     # Confirm beep longer
```
✅ Lower false positive rate
⚠️ Higher latency

**Aggressive (Minimize Latency):**
```python
SILENCE_WARMUP = 1.5
SILENCE_THRESHOLD = 1.0
BEEP_MIN_DURATION = 0.10
```
✅ Faster response
⚠️ Higher risk of early trigger

**Balanced (Production Default):**
```python
SILENCE_WARMUP = 2.0
SILENCE_THRESHOLD = 1.5
BEEP_MIN_DURATION = 0.15
```
✅ Good balance of speed and accuracy

---

## 📝 Integration with Deepgram

### Purpose of Transcription

```python
transcript_result = self.transcribe_file(filepath)
```

**Why we transcribe:**
1. **Debugging:** See what was actually said
2. **Validation:** Confirm greeting ended
3. **Analytics:** Track common greeting patterns
4. **Future enhancement:** Could use LLM to detect end-of-greeting phrases

**Not used for trigger decision** (too slow for real-time)

---

## 🎬 Complete Example Flow

### Input File: `voicemail_003.wav`

**Content:**
> "Hey, this is Sarah. Sorry I missed your call. Leave me a message! [BEEP]"

**Processing:**

```
Chunk | Time  | RMS  | Peak Freq | Beep Cnt | Silence Cnt | Decision
------|-------|------|-----------|----------|-------------|----------
  1   | 0.00s | 2900 | 420 Hz    | 0.00s    | 0.00 (WU)   | Continue
  2   | 0.05s | 3100 | 510 Hz    | 0.00s    | 0.00 (WU)   | Continue
  ...
 40   | 2.00s | 1800 | 380 Hz    | 0.00s    | 0.00s       | Continue (WU end)
 41   | 2.05s | 2200 | 440 Hz    | 0.00s    | 0.00s       | Continue
 ...
 58   | 2.90s | 1100 | 490 Hz    | 0.00s    | 0.00s       | Continue
 59   | 2.95s | 8700 | 812 Hz ✓  | 0.05s    | -           | Continue
 60   | 3.00s | 8900 | 805 Hz ✓  | 0.10s    | -           | Continue
 61   | 3.05s | 8600 | 798 Hz ✓  | 0.15s ✓  | -           | TRIGGER!
```

**Output:**
```json
{
  "filename": "voicemail_003.wav",
  "drop_time": 3.05,
  "method": "[BEEP] Beep Detected (~805Hz)",
  "words": 15,
  "transcript": "Hey, this is Sarah. Sorry I missed your call..."
}
```

---

## 📚 References & Further Reading

### Audio Signal Processing
- **FFT:** Cooley-Tukey algorithm (1965)
- **RMS:** Statistical measure of magnitude
- **Sample Rate:** Nyquist-Shannon sampling theorem

### Design Patterns
- **Strategy Pattern:** Pluggable algorithms
- **Stream Processing:** Real-time data handling
- **Factory Pattern:** `_build_engine()` method

### Real-World Applications
- Voice activity detection (VAD)
- Speech recognition systems
- Audio fingerprinting (Shazam)
- Noise cancellation
- Telecommunication systems

---

## ✅ Success Metrics

**What defines a successful drop:**

1. ✅ **Triggered after greeting ended**
2. ✅ **Triggered after beep (if present)**
3. ✅ **Latency < 2 seconds from actual endpoint**
4. ✅ **No false triggers during greeting**

**Ideal performance:**
- 95%+ success rate across varied voicemails
- <200ms latency from beep/silence to trigger
- <5% false positive rate

---

**End of Technical Summary** 🎉

For implementation details, see [main.py](main.py)
For beginner guide, see [EXPLANATION.md](EXPLANATION.md)
For project overview, see [README.md](README.md)
