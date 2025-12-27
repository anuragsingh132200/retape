#!/usr/bin/env python3
"""
Quick test script to verify the system works on a single audio file
"""

from pathlib import Path
from voicemail_detector import VoicemailDetector


def main():
    print("\n" + "="*60)
    print(" Testing Voicemail Detector ")
    print("="*60 + "\n")

    # Initialize detector
    try:
        detector = VoicemailDetector()
        print("[OK] VoicemailDetector initialized successfully")
    except ValueError as e:
        print(f"[ERROR] {e}")
        return

    # Test on first audio file
    audio_dir = Path("Voicemails - SWE Intern")
    audio_files = sorted(audio_dir.glob("*.wav"))

    if not audio_files:
        print("[ERROR] No audio files found")
        return

    print(f"[OK] Found {len(audio_files)} audio files")
    print(f"\nTesting with: {audio_files[0].name}\n")

    # Process single file
    result = detector.process_voicemail(str(audio_files[0]), verbose=True)

    print("\n" + "="*60)
    print(" Test Complete ")
    print("="*60)
    print(f"\nRecommended timestamp: {result['recommended_timestamp']:.2f}s")
    print(f"File duration: {result['duration']:.2f}s")
    print(f"Beep detected: {'Yes' if result['beep_detected'] else 'No'}")

    if result['beep_detected']:
        print(f"Beep at: {result['beep_timestamp']:.2f}s")

    print("\n[OK] System is working correctly!\n")


if __name__ == "__main__":
    main()
