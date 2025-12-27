# Quick Start Guide

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. The API key is already configured in `.env.example` and copied to `.env`

## Running the Demo

### Option 1: Full Demo (All 7 Files)
```bash
python demo.py
```

This will:
- Process all 7 voicemail audio files
- Display detailed analysis for each
- Save results to `results/analysis_results.json`
- Save simple timestamps to `results/timestamps.txt`

### Option 2: Quick Test (Single File)
```bash
python test_single.py
```

This will:
- Test the system on just the first audio file
- Show that the detector is working correctly

## What to Expect

The system will:
1. Load each audio file
2. Detect beeps using frequency analysis
3. Identify voice activity segments
4. (Optional) Use Gemini AI for additional analysis
5. Calculate the optimal timestamp to start the compliance message

## Sample Output

```
============================================================
Processing: vm1_output.wav
============================================================
Duration: 16.90 seconds
[+] Beep detected at: 1.70s
Voice segments detected: 20
  Segment 1: 3.22s - 3.43s
  Segment 2: 3.48s - 3.97s
  Segment 3: 4.04s - 4.16s

------------------------------------------------------------
RECOMMENDED DROP TIMESTAMP: 1.80s
------------------------------------------------------------

Reasoning: Beep detected at 1.70s. Starting message at 1.80s
(immediately after beep) ensures consumer hears complete
compliance message.
```

## Understanding the Results

- **Beep Detected**: System found a voicemail beep (most reliable signal)
- **Voice Segments**: Shows when speech was detected in the audio
- **Recommended Timestamp**: The exact moment to start playing the compliance message
- **Reasoning**: Explanation of why this timestamp was chosen

## Files Generated

After running the demo, check the `results/` directory:

- `analysis_results.json`: Detailed analysis with all data points
- `timestamps.txt`: Simple list of recommended timestamps

## Troubleshooting

### LLM Rate Limit Errors
If you see Gemini API rate limit errors, don't worry! The system works perfectly without LLM analysis using signal processing alone. The LLM is just an additional validation layer.

### No Audio Files Found
Make sure the audio files are in the `Voicemails - SWE Intern/` directory.

### Module Not Found Errors
Run `pip install -r requirements.txt` to install all dependencies.

## Next Steps

Read [SOLUTION_EXPLANATION.md](SOLUTION_EXPLANATION.md) for a deep dive into how the system works and the reasoning behind the implementation.
