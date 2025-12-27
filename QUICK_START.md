# 🚀 Quick Start Guide - Voicemail Dropper

> **Get up and running in 5 minutes**

---

## ⚡ Instant Setup

### 1. Install Dependencies (30 seconds)

```bash
pip install numpy soundfile deepgram-sdk python-dotenv
```

### 2. Get Deepgram API Key (2 minutes)

1. Go to https://deepgram.com
2. Sign up for free account
3. Copy your API key

### 3. Configure Environment (30 seconds)

Create a file named `.env` in the project folder:

```bash
DEEPGRAM_API_KEY=your_api_key_here
```

### 4. Add Audio Files (1 minute)

Create folder and add your voicemail WAV files:

```bash
mkdir voicemail_audio_files
# Copy your .wav files into this folder
```

### 5. Run (10 seconds)

```bash
python main.py
```

---

## 📊 Understanding the Output

### Sample Output

```
>> Streaming Voicemail Dropper (Strategy: COMBINED)
>> Found 3 audio files

================================================================================

[CALL] voicemail_001.wav
[DROP] at 3.45s - [BEEP] Beep Detected (~823Hz) (18 words)

[CALL] voicemail_002.wav
[DROP] at 5.12s - [SILENCE] Silence Timeout (1.50s) (24 words)

================================================================================
FINAL STREAMING RESULTS
================================================================================
| File                     | Drop Time | Method                    | Words |
|------------------------------------------------------------------------------|
| voicemail_001.wav        |     3.45s | [BEEP] Beep Detected      |    18 |
| voicemail_002.wav        |     5.12s | [SILENCE] Silence Timeout |    24 |
================================================================================

SUMMARY:
   * Average drop time: 4.29s
   * Files processed: 2/2
```

### What It Means

**Drop Time:** When to start playing your message (in seconds from call start)

**Method:**
- `[BEEP]` = Detected a beep tone → Very reliable
- `[SILENCE]` = Detected 1.5s of silence → Good fallback

**Words:** How many words were in the greeting (from AI transcription)

---

## 🎯 What Should You Look For?

### ✅ Good Results

```
[DROP] at 3.45s - [BEEP] Beep Detected (~823Hz)
```
- Drop time is reasonable (2-10 seconds typical)
- Method shows clear detection reason
- Matches when you'd expect the greeting to end

### ⚠️ Questionable Results

```
[DROP] at 0.95s - [SILENCE] Silence Timeout (1.50s)
```
- Too early (< 2 seconds) → Probably wrong
- Might be triggering during greeting

### ❌ Failed Detection

```
[DROP] at 12.50s - [NO_TRIGGER_FALLBACK]
```
- Used entire file duration
- Nothing detected → Need to adjust parameters

---

## ⚙️ Quick Tuning Guide

### Problem: Triggering Too Early

**Symptom:** Drop time < 2 seconds, during greeting

**Fix:** Edit [main.py](main.py), change:
```python
SILENCE_WARMUP = 3.0  # Increase from 2.0
```

---

### Problem: Triggering Too Late

**Symptom:** Long delays after greeting obviously ended

**Fix:** Edit [main.py](main.py), change:
```python
SILENCE_THRESHOLD = 1.0  # Decrease from 1.5
```

---

### Problem: Missing Beeps

**Symptom:** All results show `[SILENCE]`, never `[BEEP]`

**Fix:** Edit [main.py](main.py), change:
```python
BEEP_MIN_AMP = 1500  # Decrease from 2000
```

---

### Problem: Nothing Detected

**Symptom:** All results show `[NO_TRIGGER_FALLBACK]`

**Fix:** Edit [main.py](main.py), try:
```python
SILENCE_THRESHOLD = 1.0      # More aggressive
SILENCE_ENERGY_FLOOR = 300   # Lower threshold
BEEP_MIN_AMP = 1000          # Easier to detect
```

---

## 🎨 Visual Explanation

### How Beep Detection Works

```
Your Voicemail Greeting Audio:
─────────────────────────────────────────────────────────────
Time:    0s      1s      2s      3s      4s      5s
Audio:   "Hi, you've reached Mike... [BEEP]  [silence]"
         ▁▁▁▂▂▃▃▄▄▅▅▆▆▄▄▃▃▂▂▁▁▁███▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
                                 ↑
                            Beep detected!
                            (800 Hz tone)

Our System:
─────────────────────────────────────────────────────────────
         [Listening...] [Listening...] [TRIGGER!]
         RMS: 2800      RMS: 2100      RMS: 8900
         Freq: 450Hz    Freq: 520Hz    Freq: 815Hz ✓

Action:  Continue →     Continue →     START MESSAGE NOW!
                                       (at 3.15 seconds)
```

---

### How Silence Detection Works

```
Your Voicemail Greeting (No Beep):
─────────────────────────────────────────────────────────────
Time:    0s      1s      2s      3s      4s      5s
Audio:   "Leave a message, thanks!"  [silence continues...]
         ▁▁▁▂▂▃▃▄▄▅▅▃▃▂▂▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁
                             ↑________________↑
                             Silence starts   1.5s later

Our System:
─────────────────────────────────────────────────────────────
Silence Counter:
         0.0s → 0.0s → 0.0s → 0.5s → 1.0s → 1.5s ✓

Action:  Continue → Continue → Count → Count → TRIGGER!
                                              (at 4.5 seconds)
```

---

## 🧪 Test with Sample Audio

### Create a Test Voicemail

Don't have voicemail audio? Create a simple test:

**Option 1: Record yourself**
1. Use your phone's voice recorder
2. Say: "Hi, you've reached [your name]. Leave a message after the beep."
3. Play a beep sound (from YouTube: "voicemail beep sound")
4. Save as WAV format

**Option 2: Use text-to-speech**
1. Go to https://ttsmaker.com
2. Enter: "Hi, you've reached Mike Rodriguez. Please leave a message after the beep."
3. Download as WAV
4. Add a beep sound using audio editing tool

---

## 📝 Checklist for First Run

- [ ] Python 3.8+ installed
- [ ] Dependencies installed (`pip install ...`)
- [ ] `.env` file created with Deepgram API key
- [ ] `voicemail_audio_files/` folder created
- [ ] At least one `.wav` file in the folder
- [ ] File is actually audio (not just renamed .mp3)
- [ ] Run `python main.py`
- [ ] See output with timestamps

---

## 🐛 Common Errors & Quick Fixes

### Error: "DEEPGRAM_API_KEY not found"

**Fix:**
```bash
# Create .env file in project root
echo "DEEPGRAM_API_KEY=your_actual_key_here" > .env
```

---

### Error: "Directory 'voicemail_audio_files' not found"

**Fix:**
```bash
mkdir voicemail_audio_files
```

---

### Error: "No .wav files found"

**Fix:**
- Make sure files end in `.wav` (not `.mp3`, `.m4a`, etc.)
- Convert files to WAV using: https://cloudconvert.com/mp3-to-wav

---

### Error: "Module 'numpy' not found"

**Fix:**
```bash
pip install numpy soundfile deepgram-sdk python-dotenv
```

---

## 🎓 Next Steps

Once you have it running:

1. **Understand the code:** Read [EXPLANATION.md](EXPLANATION.md)
2. **Learn the concepts:** Read [TECHNICAL_SUMMARY.md](TECHNICAL_SUMMARY.md)
3. **Customize:** Adjust parameters for your use case
4. **Test:** Try different voicemail styles
5. **Deploy:** Integrate into your phone system

---

## 💡 Pro Tips

### Tip 1: Test One File at a Time

Comment out other files to focus on one:

```python
# In main.py, after line 316:
files = sorted(f for f in os.listdir(AUDIO_DIR) if f.lower().endswith(".wav"))

# Add this to test only one file:
files = [f for f in files if f == "voicemail_001.wav"]
```

---

### Tip 2: Add Debug Logging

See what's happening in real-time:

```python
# In BeepStrategy.process(), add after line 127:
print(f"Time {current_time:.2f}s: Peak {peak_freq:.0f}Hz @ {peak_amp:.0f}")
```

---

### Tip 3: Visualize Audio

Want to see the waveform? Add this:

```python
import matplotlib.pyplot as plt

# After reading audio, add:
plt.plot(audio_data)
plt.title("Audio Waveform")
plt.show()
```

---

## 🎯 Success Criteria

Your solution is working well if:

✅ **Beep voicemails:** Detect within 0.2s of beep ending
✅ **No-beep voicemails:** Detect within 2s of silence starting
✅ **No false triggers:** Never triggers during active speech
✅ **Consistent:** Similar voicemails get similar timestamps

---

## 📚 Documentation Map

```
📁 Project Documentation
│
├── 📄 QUICK_START.md (You are here!)
│   └─→ "How do I get this running?"
│
├── 📄 README.md
│   └─→ "What is this project?"
│
├── 📄 EXPLANATION.md
│   └─→ "How does it work? (Beginner-friendly)"
│
└── 📄 TECHNICAL_SUMMARY.md
    └─→ "Deep technical details"
```

---

## 🤝 Getting Help

**Issue tracking:**
- Read error messages carefully
- Check [TECHNICAL_SUMMARY.md](TECHNICAL_SUMMARY.md) debugging section
- Verify file formats (must be WAV)
- Test with simple, known audio first

---

**You're ready to go! Run `python main.py` and see the magic happen!** ✨
