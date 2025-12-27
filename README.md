# Take Home Assignment

# **Drop Compliant Voicemails**

## The Problem

You’re a **software engineer at ClearPath Finance**, a company that helps people manage their credit card debt.

Every day, ClearPath’s system places **outbound phone calls** to customers to share important updates about their accounts.

One such customer is **Mike Rodriguez**.

Your system dials Mike’s number… but Mike is busy and doesn’t pick up.

Instead, the call goes to **voicemail**, and you hear this greeting:

> “Hi, you’ve reached Mike Rodriguez. I can’t take your call right now.
> 
> 
> Please leave your name, number, and a brief message after the beep.”
> 

### About Voicemail Greetings

These voicemail greetings are recorded by consumers, and in the real world they can be very different:

- Every person has a **different greeting**
- Some greetings **end with a beep**
- Some greetings **do not have a beep**
- Some greetings are **short**, others are **long**

---

## The Task

Your system now has an important job.

As soon as Mike’s greeting finishes, **ClearPath must leave a prerecorded, compliant voicemail message**, for example:

> “Hi, this is ClearPath Finance calling regarding your account.
> 
> 
> Please call us back at 800-555-0199. Thank you.”
> 

The challenge is deciding **exactly when to start playing this message**.

---

## What Does “Compliance” Mean?

**Anything the consumer hears must include:**

- The **company name**
- The **return phone number**

Anything the consumer **does not hear does not matter**. 

**⚠️ Important Note About the Beep:**

If a beep occurs, the consumer cannot hear anything spoken before the beep.

If the beep doesn’t occur, then the consumer can hear everything after their message ended.

This makes timing critical.

---

## Why Timing Matters

If your system:

- **Starts too early** → Mike might only hear
    
    *“…please call us back at 800-555-0199. Thank you”* ❌
    
    (Company name missing → non-compliant)
    
- **Starts too late** → The consumer may lose patience ❌

---

## Your Goal

> Develop a strategy to drop a compliant voicemail.
> 

---

## Input

- You are given **7 audio files** from calls that went to voicemail. You can access the audio files [here](https://drive.google.com/drive/folders/1RnRAkMxQTwsD5w3Kzd3BawpiLes2GOqn?usp=sharing).
- You must **stream** these audio files to simulate phone calls
    
    (Important: real phone calls are streaming, not pre-recorded chunks)
    

---

## Output

For **each audio file**, output the **timestamp(s)** at which you would start playing the voicemail.

---

## Hints (Optional)

- Speech-to-Text (e.g., Deepgram)
- LLMs for detecting common **end-of-greeting phrases**
- Handling cases with and without a beep

You are **encouraged to use AI**—both while writing code and while brainstorming your approach.

---

## What We’re Evaluating

This is a **learning-focused assignment**.

We are **not** expecting a perfect solution.

We care about:

- How you **think**
- How you **handle edge cases**
- How clearly you can **explain your logic**

---

## Deliverables

Please submit:

1. **Code**
    - Any programming language
2. **A short paragraph**
    - Explaining how your logic works
3. **A small demo**
    - Showing your solution in action

Please drop your submissions [here](https://forms.gle/XwAdpFPna7zkMXeC7).

---

## Final Note

This is the kind of real-world problem we solve every day for our customers.

There is no single correct answer.

If thinking through problems like this excites you, you'd be a great fit for our team, we're excited to see your approach 🙂

---

# SOLUTION IMPLEMENTATION

## Overview

This solution uses a multi-layered approach combining signal processing, voice activity detection, beep detection, and AI-powered analysis using Google's Gemini LLM to determine the optimal timestamp for dropping compliant voicemail messages.

## How It Works

### Core Strategy

The system processes voicemail audio files through several detection layers:

1. **Audio Signal Processing**
   - Loads and resamples audio to a standard 16kHz sample rate
   - Simulates streaming by processing audio in chunks (as would happen in a real phone call)

2. **Beep Detection**
   - Analyzes frequency spectrum in 100ms chunks
   - Identifies pure tones in the 800-1200 Hz range (typical voicemail beep frequencies)
   - High energy concentration in this range indicates a beep
   - **If beep detected**: This is the most reliable signal - we start the message immediately after (beep_time + 0.1s)

3. **Voice Activity Detection (VAD)**
   - Calculates energy levels across the audio using RMS (Root Mean Square)
   - Identifies segments where speech is present
   - Tracks the end of the last speech segment
   - **If no beep**: Uses last speech end + safety buffer (0.3s) as starting point

4. **Gemini LLM Analysis**
   - Provides transcript information and audio metadata to Gemini
   - LLM analyzes patterns like "leave a message", "after the beep", etc.
   - Validates our signal-based detection with AI understanding
   - Provides fallback estimate if other methods are uncertain

5. **Timestamp Calculation**
   - **Priority 1**: Beep detection (most reliable)
   - **Priority 2**: Last speech segment end + buffer
   - **Priority 3**: LLM estimated end time + buffer
   - Always includes safety buffer to ensure compliance

### Why This Approach Ensures Compliance

The compliance requirement states the consumer MUST hear:
- Company name ("ClearPath Finance")
- Return phone number ("800-555-0199")

Our logic ensures this by:

1. **After beep**: Consumer can ONLY hear what comes after the beep, so we start immediately after it. They hear the complete message including company name and number.

2. **No beep**: Consumer can hear everything after the greeting ends. We wait for speech to completely finish + buffer, ensuring they hear our full message from the beginning.

3. **Safety buffers**: We add 0.1-0.3s buffers to account for:
   - Audio processing delays
   - Voicemail system variations
   - Brief pauses in speech that aren't actually the end

### Edge Cases Handled

1. **Long greetings**: Voice activity detection tracks all speech segments
2. **Short greetings**: System works with greetings of any length
3. **No beep**: Falls back to speech detection + LLM analysis
4. **Unclear endings**: LLM provides semantic understanding of greeting patterns
5. **Multiple beeps**: Takes the first detected beep
6. **Background noise**: Energy threshold filtering reduces false positives

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Key

The API key is already configured in `.env.example`. The system will automatically use it.

### 3. Run the Demo

```bash
python demo.py
```

## Project Structure

```
retape/
├── voicemail_detector.py    # Core detection logic
├── demo.py                  # Demo script to process all files
├── requirements.txt         # Python dependencies
├── .env.example            # Gemini API key configuration
├── Voicemails - SWE Intern/  # Audio files (7 WAV files)
└── results/                 # Output directory (created on first run)
    ├── analysis_results.json   # Detailed analysis
    └── timestamps.txt          # Simple timestamp output
```

## Output Format

The system produces:

1. **Console output** with detailed analysis for each file
2. **analysis_results.json** with complete analysis data
3. **timestamps.txt** with simple timestamp listings

### Example Output

```
vm1_output.wav: 3.45s
vm2_output.wav: 2.80s
vm3_output.wav: 5.12s
...
```

## Technical Details

- **Language**: Python 3.8+
- **Key Libraries**:
  - `librosa`: Audio processing and feature extraction
  - `scipy`: Signal processing for beep detection
  - `numpy`: Numerical operations
  - `google-generativeai`: Gemini LLM integration
- **Approach**: Multi-modal detection (signal processing + AI)
- **Real-time simulation**: Processes audio in chunks to simulate streaming

## Future Improvements

If deploying to production, consider:

1. **Real-time STT**: Integrate Deepgram or similar for actual transcription
2. **Model fine-tuning**: Train on labeled voicemail dataset
3. **Confidence scores**: Return probability estimates for each timestamp
4. **A/B testing**: Track compliance rates in production
5. **Adaptive thresholds**: Adjust based on success metrics
6. **Multi-language support**: Handle greetings in different languages