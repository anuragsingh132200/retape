#!/usr/bin/env python3
"""
Quick test script to process a single voicemail file
Usage: python test_single.py <filename>
"""

import asyncio
import sys
from voicemail_drop import VoicemailDropDetector

async def test_single_file(filename):
    """Test a single voicemail file"""
    detector = VoicemailDropDetector()

    print(f"\nProcessing: {filename}")
    print("=" * 60)

    result = await detector.process_file(filename)

    print("\n" + "=" * 60)
    print("RESULT:")
    print(f"  Drop Timestamp: {result.drop_timestamp}s")
    print(f"  Reason: {result.reason}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Methods Used: {', '.join(result.method_used)}")
    print(f"  Compliance: {result.compliance_status}")
    if result.details:
        print(f"  Details: {result.details}")
    print("=" * 60 + "\n")

    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_single.py <filename>")
        print("Example: python test_single.py 'Voicemails - SWE Intern/vm1_output.wav'")
        sys.exit(1)

    filename = sys.argv[1]
    asyncio.run(test_single_file(filename))
