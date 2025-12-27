# Quick Start Guide

Get up and running in 3 simple steps!

## Step 1: Install Dependencies

**Windows:**
```bash
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

**Manual:**
```bash
pip install -r requirements.txt
```

## Step 2: Configure API Keys (Optional)

Edit `.env` file:
```env
DEEPGRAM_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

**Note**: System works without API keys using fallback methods!

## Step 3: Run Demo

**Windows:**
```bash
run_demo.bat
```

**Linux/Mac:**
```bash
chmod +x run_demo.sh
./run_demo.sh
```

**Direct:**
```bash
python voicemail_drop.py
```

## That's it! 🎉

Results will be saved to `results.json`

## Test Single File

```bash
python test_single.py "Voicemails - SWE Intern/vm1_output.wav"
```

## View Results

```bash
cat results.json
```

## Expected Output

```json
{
  "vm1_output.wav": {
    "drop_timestamp": 10.84,
    "reason": "end_of_file",
    "confidence": 1.0,
    "method_used": ["beep"],
    "compliance_status": "safe"
  }
}
```

## Need Help?

- 📖 Full documentation: [README.md](README.md)
- 🎥 Demo guide: [DEMO_GUIDE.md](DEMO_GUIDE.md)
- 📊 Technical summary: [SUBMISSION_SUMMARY.md](SUBMISSION_SUMMARY.md)

## System Requirements

- Python 3.8 or higher
- 2GB RAM minimum
- Internet connection for API calls (optional)

## Project Structure

```
retape/
├── voicemail_drop.py       # Main system
├── results.json            # Output
├── requirements.txt        # Dependencies
├── .env                    # API keys
└── Voicemails - SWE Intern/ # Audio files
```

## Common Issues

**Import Error?** → Run `pip install -r requirements.txt`

**VAD Warnings?** → Expected! System uses RMS fallback

**No Results?** → Check audio files are in `Voicemails - SWE Intern/`

---

**Ready to impress? Run the demo now!** 🚀
