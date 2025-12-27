#!/usr/bin/env python3
"""
Demo script for the Voicemail Compliance Drop System

This script processes all voicemail audio files and determines
optimal timestamps for dropping compliant messages.
"""

import os
import json
from pathlib import Path
from voicemail_detector import VoicemailDetector


def main():
    """Run the demo on all voicemail files."""
    print("\n" + "="*70)
    print(" VOICEMAIL COMPLIANCE DROP SYSTEM - DEMO ".center(70))
    print("="*70)

    # Initialize detector
    try:
        detector = VoicemailDetector()
    except ValueError as e:
        print(f"\n[ERROR] {e}")
        print("\nPlease create a .env file with your GEMINI_API_KEY")
        print("Example: Copy .env.example to .env and add your API key")
        return

    # Audio files directory
    audio_dir = Path("Voicemails - SWE Intern")

    if not audio_dir.exists():
        print(f"\n[ERROR] Directory '{audio_dir}' not found")
        return

    # Get all WAV files
    audio_files = sorted(audio_dir.glob("*.wav"))

    if not audio_files:
        print(f"\n[ERROR] No .wav files found in '{audio_dir}'")
        return

    print(f"\nFound {len(audio_files)} voicemail files to process\n")

    # Process each file
    results = []

    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n[{i}/{len(audio_files)}]", end=" ")
        result = detector.process_voicemail(str(audio_file), verbose=True)
        results.append(result)

    # Summary
    print("\n\n" + "="*70)
    print(" SUMMARY OF RESULTS ".center(70))
    print("="*70)

    print(f"\n{'File':<20} {'Duration':<10} {'Beep':<8} {'Drop Time':<12} {'Reasoning'}")
    print("-" * 100)

    for result in results:
        file_name = result['audio_file']
        duration = f"{result['duration']:.2f}s"
        beep = "[+]" if result['beep_detected'] else "[-]"
        drop_time = f"{result['recommended_timestamp']:.2f}s"
        reasoning = result['reasoning'][:40] + "..." if len(result['reasoning']) > 40 else result['reasoning']

        print(f"{file_name:<20} {duration:<10} {beep:<8} {drop_time:<12} {reasoning}")

    # Save results to JSON
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "analysis_results.json"

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print(f"\n[OK] Detailed results saved to: {output_file}")

    # Create simple output format
    simple_output = output_dir / "timestamps.txt"
    with open(simple_output, 'w', encoding='utf-8') as f:
        f.write("VOICEMAIL DROP TIMESTAMPS\n")
        f.write("="*50 + "\n\n")
        for result in results:
            f.write(f"{result['audio_file']}: {result['recommended_timestamp']:.2f}s\n")

    print(f"[OK] Simple timestamps saved to: {simple_output}")

    print("\n" + "="*70)
    print(" DEMO COMPLETE ".center(70))
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
