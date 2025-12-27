# System Architecture

## High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     VOICEMAIL AUDIO FILE                        │
│                         (WAV Format)                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AUDIO PREPROCESSING                          │
│  • Load audio file                                              │
│  • Resample to 16kHz standard rate                              │
│  • Normalize audio levels                                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│  BEEP DETECTION  │          │ VOICE ACTIVITY   │
│                  │          │   DETECTION      │
├──────────────────┤          ├──────────────────┤
│ • FFT Analysis   │          │ • RMS Energy     │
│ • 100ms chunks   │          │ • 25ms frames    │
│ • 800-1200 Hz    │          │ • Threshold      │
│ • Peak detection │          │ • Segment track  │
└────────┬─────────┘          └────────┬─────────┘
         │                             │
         │        ┌────────────────────┘
         │        │
         │        │    ┌─────────────────────┐
         │        │    │  GEMINI LLM         │
         │        │    │  ANALYSIS           │
         │        │    │  (Optional)         │
         │        │    ├─────────────────────┤
         │        │    │ • Transcript info   │
         │        │    │ • Pattern matching  │
         │        │    │ • End-of-greeting   │
         │        │    │ • Estimated time    │
         │        │    └────────┬────────────┘
         │        │             │
         ▼        ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│              TIMESTAMP CALCULATION ENGINE                       │
│                                                                 │
│  Decision Tree:                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ IF beep_detected:                                        │  │
│  │     timestamp = beep_time + 0.1s                         │  │
│  │ ELIF voice_segments:                                     │  │
│  │     timestamp = last_speech_end + 0.3s                   │  │
│  │     timestamp = max(timestamp, llm_estimate)             │  │
│  │ ELSE:                                                    │  │
│  │     timestamp = llm_estimate + 0.3s                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESULT PACKAGE                               │
│  • Recommended timestamp                                        │
│  • Beep detection info                                          │
│  • Voice segments                                               │
│  • Reasoning explanation                                        │
│  • Confidence indicators                                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────┴───────────────┐
         │                               │
         ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│  JSON OUTPUT     │          │  TEXT OUTPUT     │
│  (Detailed)      │          │  (Simple)        │
├──────────────────┤          ├──────────────────┤
│ • Full analysis  │          │ • Timestamps     │
│ • All metrics    │          │ • File names     │
│ • Structured data│          │ • Clean format   │
└──────────────────┘          └──────────────────┘
```

## Component Details

### 1. Audio Preprocessing Layer

**Purpose**: Normalize input for consistent processing

**Key Operations**:
- Load WAV file using librosa
- Resample to 16kHz (standard speech processing rate)
- Convert to mono if stereo
- Normalize amplitude

**Output**: numpy array of audio samples + sample rate

### 2. Beep Detection Engine

**Algorithm**: Frequency Domain Analysis

```python
for each 100ms chunk:
    1. Compute FFT (Fast Fourier Transform)
    2. Extract frequency bins
    3. Look for peaks in 800-1200 Hz range
    4. Calculate energy ratio: beep_energy / total_energy
    5. If ratio > 0.7: BEEP DETECTED
    6. Return timestamp of beep
```

**Why it works**:
- Beeps are pure sine waves at specific frequencies
- High energy concentration in narrow frequency band
- Machine-generated → consistent characteristics

### 3. Voice Activity Detection (VAD)

**Algorithm**: Energy-Based Segmentation

```python
1. Calculate RMS energy in 25ms frames (10ms hop)
2. Compute threshold = mean_energy * 0.3
3. Mark frames above threshold as "speech"
4. Group consecutive speech frames into segments
5. Return list of (start_time, end_time) tuples
```

**Why it works**:
- Speech has higher energy than silence
- RMS captures overall signal strength
- Temporal grouping finds continuous speech

### 4. LLM Analysis Layer

**Purpose**: Semantic understanding and validation

**Input to Gemini**:
```
Transcript metadata + duration
Request: Analyze greeting patterns
Expected: JSON with end phrases, beep mentions, estimated time
```

**Role**:
- Validates signal-based detection
- Provides fallback estimate
- Understands language patterns

### 5. Decision Engine

**Priority-based selection**:

```
Priority 1: Beep Detection (most reliable)
    ↓ If no beep
Priority 2: Voice Activity Detection + Safety Buffer
    ↓ Validated by
Priority 3: LLM Estimate (if available)
```

**Safety Buffers**:
- Post-beep: +0.1s (minimal delay)
- Post-speech: +0.3s (allow greeting to fully complete)
- LLM estimate: +0.3s (conservative estimate)

## Data Flow Example

### Example: vm1_output.wav

```
Input Audio: 16.90 seconds
    ↓
Beep Detection: FOUND at 1.70s
    ↓
Voice Detection: 20 segments identified
    Last segment: ends at ~4.16s
    ↓
LLM Analysis: (Rate limited, skipped)
    ↓
Decision Engine:
    Beep detected → Use beep-based timing
    timestamp = 1.70s + 0.1s = 1.80s
    ↓
Output: "Start message at 1.80s"
Reasoning: "Consumer can only hear audio after beep,
           guarantees full compliance message"
```

## Error Handling Architecture

```
┌─────────────────┐
│ Try Beep Detect │
└────────┬────────┘
         │
    ┌────▼────┐
    │ Success?│
    └─┬────┬──┘
      │    │
     Yes   No
      │    │
      │    └──► Try VAD ──► Success? ──► Use VAD + Buffer
      │                        │
      │                        No
      │                        │
      │                        └──► Try LLM ──► Success? ──► Use LLM
      │                                           │
      │                                           No
      │                                           │
      │                                           └──► Fallback: duration
      │
      └──► Use Beep Timestamp
```

## Performance Characteristics

### Time Complexity
- **Beep Detection**: O(n) where n = audio samples
  - FFT per chunk: O(k log k) where k = chunk size
  - Total chunks: n / chunk_size

- **VAD**: O(n) where n = audio samples
  - Single pass through audio
  - RMS calculation per frame

- **Overall**: O(n) - Linear in audio length

### Space Complexity
- **Memory**: O(n) for audio array + O(m) for segments
- Typical: ~1MB per minute of audio

### Latency
- **Processing time**: ~0.5-2 seconds per audio file (on standard CPU)
- **Could be real-time**: Yes, with streaming implementation

## Scalability Considerations

### Current Implementation
- Batch processing of files
- Single-threaded
- Suitable for demo/testing

### Production Enhancements
```
┌────────────────┐
│  Audio Stream  │
└───────┬────────┘
        │
        ▼
┌────────────────┐
│  Buffer Queue  │ ◄─── Chunk-based processing
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Parallel       │ ◄─── Multi-threaded
│ Detection      │      (beep + VAD concurrent)
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Result Merger  │ ◄─── Combine results
└───────┬────────┘
        │
        ▼
┌────────────────┐
│ Decision Point │ ◄─── Immediate action
└────────────────┘
```

## Technology Stack Mapping

```
Application Layer:     demo.py, test_single.py
    ↓
Business Logic:        VoicemailDetector class
    ↓
Detection Engines:     beep_detect(), VAD(), LLM_analysis()
    ↓
Signal Processing:     scipy.signal, numpy.fft
    ↓
Audio I/O:            librosa, soundfile
    ↓
External Services:     Google Gemini API
```

## Configuration Management

```
Environment Variables (.env):
    └─ GEMINI_API_KEY

Detection Parameters:
    ├─ sample_rate: 16000 Hz
    ├─ chunk_duration: 0.5s (streaming)
    ├─ beep_freq_range: 800-1200 Hz
    ├─ beep_threshold: 0.7
    ├─ vad_frame_length: 25ms
    ├─ vad_hop_length: 10ms
    ├─ safety_buffer_beep: 0.1s
    └─ safety_buffer_speech: 0.3s
```

## Deployment Architecture (Future)

```
┌──────────────┐         ┌──────────────┐
│   Phone      │         │   Phone      │
│   System     │ ──────► │   System     │
└──────┬───────┘         └──────┬───────┘
       │                        │
       │ Audio Stream           │ Audio Stream
       ▼                        ▼
┌─────────────────────────────────────────┐
│      Load Balancer                      │
└────────────┬───────────────┬────────────┘
             │               │
       ┌─────▼─────┐   ┌────▼──────┐
       │ Detector  │   │ Detector  │
       │ Instance 1│   │ Instance 2│
       └─────┬─────┘   └────┬──────┘
             │               │
       ┌─────▼───────────────▼─────┐
       │   Results Database        │
       │   (Timestamps + Metrics)  │
       └───────────────────────────┘
```

---

**Note**: This architecture is designed for clarity and modularity, making it easy to extend with additional detection methods or integrate into larger systems.
