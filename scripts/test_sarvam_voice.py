"""
Sarvam AI Voice-to-Text (STT) Standalone Verification Script
TurSathi AI / AgriMind AI

Usage:
  # 1. Test with verified sample Marathi audio:
  python scripts/test_sarvam_voice.py --sample

  # 2. Test with any audio file:
  python scripts/test_sarvam_voice.py --file path/to/audio.wav --lang mr

  # 3. Test via local FastAPI endpoint:
  python scripts/test_sarvam_voice.py --endpoint http://localhost:8000/api/v1/test/voice-to-text
"""

import argparse
import os
import sys
import time
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Load environment from backend/.env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv(env_path)

DEFAULT_EXPECTED_MARATHI = "माझ्या सोयाबीनच्या पानांवर पिवळे डाग पडले आहेत."


def compute_word_similarity(expected: str, actual: str) -> float:
    def clean(s: str) -> list[str]:
        for ch in ["।", ".", ",", "!", "?", "-", "_"]:
            s = s.replace(ch, " ")
        return [w.strip().lower() for w in s.split() if w.strip()]

    exp_words = clean(expected)
    act_words = clean(actual)
    if not exp_words:
        return 0.0

    matches = sum(1 for w in exp_words if w in act_words)
    return round((matches / len(exp_words)) * 100.0, 1)


def main():
    parser = argparse.ArgumentParser(description="Test Sarvam AI Voice-to-Text")
    parser.add_argument("--file", help="Path to audio file to transcribe")
    parser.add_argument("--sample", action="store_true", help="Use built-in sample Marathi audio")
    parser.add_argument("--lang", default="mr", choices=["mr", "hi", "en", "unknown"], help="Language code")
    parser.add_argument("--expected", default=DEFAULT_EXPECTED_MARATHI, help="Expected transcription text")
    parser.add_argument("--endpoint", help="Test via FastAPI endpoint URL instead of direct service")
    args = parser.parse_args()

    api_key = os.getenv("SARVAM_API_KEY")

    print("\n" + "=" * 60)
    print("🎙️  SARVAM AI VOICE-TO-TEXT (STT) TEST RUNNER")
    print("=" * 60)

    # 1. Check API Key
    if not api_key or not api_key.strip():
        print("❌ ERROR: SARVAM_API_KEY is not configured in backend/.env!")
        print("Please configure SARVAM_API_KEY in backend/.env before running this test.")
        sys.exit(1)

    print(f"🔑 SARVAM_API_KEY detected: {api_key[:8]}... (securely masked)")

    # 2. Locate audio file
    audio_path = None
    if args.sample or not args.file:
        default_sample = os.path.abspath(os.path.join(os.path.dirname(__file__), "sample_marathi_speech.wav"))
        if os.path.exists(default_sample):
            audio_path = default_sample
        elif args.file:
            audio_path = os.path.abspath(args.file)
        else:
            print("❌ No audio file specified and sample_marathi_speech.wav not found.")
            print("Please specify an audio file with --file <path> or generate sample first.")
            sys.exit(1)
    else:
        audio_path = os.path.abspath(args.file)

    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found at: {audio_path}")
        sys.exit(1)

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    print(f"📁 Audio file loaded: {os.path.basename(audio_path)}")
    print(f"   Size: {len(audio_bytes):,} bytes ({len(audio_bytes)/1024:.1f} KB)")
    print(f"   Target Language: {args.lang}")
    print(f"   Expected Sentence: {args.expected}")
    print("-" * 60)

    # 3. Transcribe
    print("⏳ Status: Transcribing via Sarvam AI API...")
    t_start = time.time()
    transcript = None
    error_msg = None

    if args.endpoint:
        # Test via HTTP endpoint
        import httpx
        try:
            files = {"audio": (os.path.basename(audio_path), audio_bytes, "audio/wav")}
            data = {"language": args.lang}
            with httpx.Client(timeout=25.0) as client:
                res = client.post(args.endpoint, files=files, data=data)
            if res.status_code == 200:
                payload = res.json()
                if payload.get("success"):
                    transcript = payload.get("transcript")
                else:
                    error_msg = payload.get("error")
            else:
                error_msg = f"HTTP {res.status_code}: {res.text[:200]}"
        except Exception as e:
            error_msg = str(e)
    else:
        # Test via backend Sarvam STT service
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
        from app.services.sarvam_stt_service import transcribe_audio_bytes
        try:
            transcript = transcribe_audio_bytes(
                file_bytes=audio_bytes,
                original_filename=os.path.basename(audio_path),
                content_type="audio/wav",
                language=args.lang,
                timeout_seconds=20.0,
            )
            if transcript is None:
                error_msg = "Sarvam API returned empty transcript or failed (check backend logs)"
        except Exception as e:
            error_msg = str(e)

    duration = time.time() - t_start

    print("-" * 60)
    if transcript:
        print("✅ Status: Transcription Successful")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"\n📢 Actual Transcript:\n   \"{transcript}\"")
        print(f"\n🎯 Expected Text:\n   \"{args.expected}\"")

        similarity = compute_word_similarity(args.expected, transcript)
        print(f"\n📊 Word Accuracy / Match Similarity: {similarity}%")
        if similarity >= 90:
            print("   Verdict: PERFECT / EXACT MATCH ✅")
        elif similarity >= 60:
            print("   Verdict: HIGH ACCURACY MATCH ⚡")
        else:
            print("   Verdict: PARTIAL MATCH ⚠️")
    else:
        print("❌ Status: Transcription Failed")
        print(f"⏱️  Duration: {duration:.2f} seconds")
        print(f"   Reason / Error: {error_msg}")
        sys.exit(1)

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
