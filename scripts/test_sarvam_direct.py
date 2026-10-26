import os
import io
import wave
import math
import struct
import httpx
from dotenv import load_dotenv

# Load backend .env
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
api_key = os.getenv("SARVAM_API_KEY")

print("Checking SARVAM_API_KEY from backend/.env...")
if not api_key:
    print("ERROR: SARVAM_API_KEY not found in backend/.env!")
    exit(1)
else:
    print("SARVAM_API_KEY is configured (starts with:", api_key[:8] + "...)")

# Generate 1.5 seconds of a simple 440Hz sine wave WAV audio in memory
sample_rate = 16000
duration = 1.5
num_samples = int(sample_rate * duration)

buf = io.BytesIO()
with wave.open(buf, 'wb') as wav_file:
    wav_file.setnchannels(1)        # Mono
    wav_file.setsampwidth(2)        # 16-bit
    wav_file.setframerate(sample_rate)
    frames = []
    for i in range(num_samples):
        # 440 Hz tone
        val = int(32767.0 * 0.3 * math.sin(2.0 * math.pi * 440.0 * i / sample_rate))
        frames.append(struct.pack('<h', val))
    wav_file.writeframes(b''.join(frames))

wav_bytes = buf.getvalue()
print(f"Generated test WAV audio: {len(wav_bytes)} bytes")

# Test Sarvam STT endpoint
endpoint = "https://api.sarvam.ai/speech-to-text"
headers = {
    "api-subscription-key": api_key.strip(),
}

# Let's test with model saaras:v4 and language mr-IN
data = {
    "model": "saaras:v4",
    "mode": "transcribe",
    "language_code": "mr-IN",
}
files = {
    "file": ("test_tone.wav", wav_bytes, "audio/wav"),
}

print("Sending request to Sarvam STT API...")
try:
    with httpx.Client(timeout=20.0) as client:
        resp = client.post(endpoint, headers=headers, data=data, files=files)
        print("Response HTTP Status:", resp.status_code)
        print("Response Text:", resp.text)
except Exception as e:
    print("Request failed with error:", e)
