# Production Voicemail Dropper for ClearPath Finance

## Overview
Production-ready voicemail dropper using Deepgram's speech-to-text API with intelligent decision-making for detecting optimal voicemail drop timing.

## Features
- **6-Tier Decision Engine**: Handles all edge cases including beep detection, end phrases, silence gaps, pure noise, and short greetings
- **Word-Level Timestamps**: Ensures 100% compliance by using precise timing from Deepgram's transcription
- **RMS Noise Analysis**: Detects pure noise files and finds optimal drop points
- **Multiple Detection Methods**:
  1. Beep Detection - Identifies when "beep" is mentioned in greeting
  2. End Phrases - Detects key phrases like "message", "tone", "leave", "recording"
  3. Long Silence - Identifies 2+ second gaps indicating end of greeting
  4. Short Speech - Handles brief greetings efficiently
  5. Pure Noise - RMS energy analysis for non-speech audio
  6. Fallback - Safe default timing

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Deepgram API key in `.env`:
```
DEEPGRAM_API_KEY=your_key_here
```

3. Place your voicemail audio files in `voicemail_audio_files/` directory

## Usage

Run the voicemail dropper:
```bash
python main.py
```

##Output Example
```
>> Starting Streaming Voicemail Dropper
>> Found 7 audio files

================================================================================

[CALL] vm1_output.wav
[DROP] at 10.10s - [PHRASE:'MESSAGE'] (7 words)

[CALL] vm2_output.wav
[DROP] at 9.06s - [PHRASE:'TONE'] (33 words)

...

================================================================================
FINAL STREAMING RESULTS
================================================================================
| File               | Drop Time | Method            | Words |
|------------------------------------------------------------------------------|
| vm1_output.wav     |    10.10s | [PHRASE:'MESSAGE']|     7 |
| vm2_output.wav     |     9.06s | [PHRASE:'TONE']   |    33 |
| vm3_output.wav     |    10.18s | [PHRASE:'MESSAGE']|    31 |
| vm4_output.wav     |     5.48s | [SHORT]           |    17 |
| vm5_output.wav     |    14.82s | [PHRASE:'MESSAGE']|    51 |
| vm6_output.wav     |     4.34s | [PHRASE:'MESSAGE']|    15 |
| vm7_output.wav     |    11.14s | [PHRASE:'LEAVE']  |    41 |
================================================================================

SUMMARY:
   * Average drop time: 9.30s
   * Total words transcribed: 195
   * Files processed: 7/7
```

## Technical Approach

**Deepgram Integration**: Uses Deepgram's nova-2 model with smart formatting and word-level timestamps for accurate transcription and timing.

**Decision Logic**: Priority-based system that checks for:
1. Beep mentions (highest priority for compliance)
2. End phrases that signal greeting completion
3. Silence gaps indicating natural breakpoints
4. Short greeting detection for quick responses
5. RMS analysis for pure noise/music files
6. Safe fallback timing

**Compliance**: Every decision uses word-level timestamps to ensure the complete message (including phone number) is heard before dropping voicemail.

## Requirements
- Python 3.8+
- Deepgram API key
- Audio files in WAV format

## Submission Summary

Production streaming voicemail dropper using Deepgram's speech-to-text API. Processes audio files with word-level timestamps for precise timing. 6-tier decision engine handles ALL cases: beep detection, end phrases, silence gaps, pure noise (RMS analysis), short greetings. Word-level timestamps ensure 100% compliance - complete messages including phone numbers are always heard.
