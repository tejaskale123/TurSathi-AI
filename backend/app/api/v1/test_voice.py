import logging
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.services.sarvam_stt_service import (
    map_language_code,
    transcribe_audio_bytes,
)

logger = logging.getLogger("tursathi.test_voice")

router = APIRouter(prefix="/test", tags=["Voice Testing"])

_MAX_TEST_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB


@router.post("/voice-to-text", summary="Isolated Sarvam AI Voice-to-Text Test Endpoint")
async def test_voice_to_text(
    audio: UploadFile = File(..., description="Audio file from microphone or upload"),
    language: Optional[str] = Form(default="mr", description="Language code: mr | hi | en | unknown"),
):
    """
    Isolated test endpoint for Sarvam AI Voice-to-Text.
    Does not touch scans, ML disease models, database, or user auth.
    Securely reads SARVAM_API_KEY from backend environment.
    """
    if not settings.SARVAM_API_KEY or not settings.SARVAM_API_KEY.strip():
        logger.warning("[TEST_VOICE] SARVAM_API_KEY is missing from environment.")
        return {
            "success": False,
            "error": "SARVAM_API_KEY is not configured in backend/.env",
            "transcript": None,
        }

    try:
        file_bytes = await audio.read(_MAX_TEST_AUDIO_BYTES)
    except Exception as read_err:
        logger.error("[TEST_VOICE] Failed to read audio upload: %s", read_err)
        return {
            "success": False,
            "error": "Failed to read audio data from request",
            "transcript": None,
        }

    if not file_bytes or len(file_bytes) == 0:
        return {
            "success": False,
            "error": "Empty audio data received. Please record or upload valid audio.",
            "transcript": None,
        }

    content_type = audio.content_type or "audio/webm"
    filename = audio.filename or "recording.webm"
    norm_lang = (language or "mr").strip().lower()

    logger.info(
        "[TEST_VOICE] Audio received for STT test: size=%d bytes, format=%s, requested_language=%s",
        len(file_bytes), content_type, norm_lang,
    )

    try:
        transcript = transcribe_audio_bytes(
            file_bytes=file_bytes,
            original_filename=filename,
            content_type=content_type,
            language=norm_lang,
            timeout_seconds=20.0,
        )

        if transcript is not None:
            return {
                "success": True,
                "transcript": transcript,
                "language_requested": norm_lang,
                "sarvam_language_code": map_language_code(norm_lang),
                "audio_size_bytes": len(file_bytes),
                "model_used": settings.SARVAM_STT_MODEL,
            }
        else:
            return {
                "success": False,
                "error": "Sarvam API could not transcribe this audio. It may be silent or unclear.",
                "transcript": None,
                "audio_size_bytes": len(file_bytes),
            }

    except Exception as exc:
        logger.error("[TEST_VOICE] Unexpected error during STT processing: %s", exc)
        return {
            "success": False,
            "error": f"STT processing failed: {str(exc)}",
            "transcript": None,
        }


# Interactive Web Test UI
_HTML_PAGE = """<!DOCTYPE html>
<html lang="mr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sarvam AI Voice-to-Text Test | AgriMind AI</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b130e;
      --card-bg: rgba(18, 32, 24, 0.85);
      --card-border: rgba(46, 125, 50, 0.35);
      --primary: #2e7d32;
      --primary-light: #4caf50;
      --primary-glow: rgba(76, 175, 80, 0.3);
      --danger: #e53935;
      --danger-glow: rgba(229, 57, 53, 0.35);
      --text: #f1f8e9;
      --text-muted: #a5d6a7;
      --text-dim: #81c784;
      --badge-ready: #1b5e20;
      --badge-rec: #b71c1c;
      --badge-proc: #0d47a1;
      --badge-success: #2e7d32;
      --badge-fail: #c62828;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      background: radial-gradient(circle at 50% 10%, #152e1b, var(--bg));
      color: var(--text);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px 16px;
    }

    .container {
      width: 100%;
      max-width: 680px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .header {
      text-align: center;
      padding-bottom: 8px;
    }

    .header h1 {
      font-size: 26px;
      font-weight: 700;
      color: #a5d6a7;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }

    .header p {
      color: #81c784;
      font-size: 14px;
      margin-top: 6px;
    }

    .card {
      background: var(--card-bg);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }

    /* Status Badge */
    .status-container {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 16px;
      border-radius: 999px;
      font-size: 14px;
      font-weight: 600;
      transition: all 0.3s ease;
      background: rgba(46, 125, 50, 0.25);
      border: 1px solid #4caf50;
      color: #c8e6c9;
    }

    .status-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #4caf50;
    }

    .status-ready {
      background: rgba(46, 125, 50, 0.25);
      border-color: #4caf50;
      color: #c8e6c9;
    }
    .status-ready .status-dot { background: #4caf50; }

    .status-recording {
      background: rgba(229, 57, 53, 0.25);
      border-color: #e53935;
      color: #ffcdd2;
      animation: pulse 1.5s infinite;
    }
    .status-recording .status-dot {
      background: #e53935;
      box-shadow: 0 0 8px #e53935;
    }

    .status-transcribing {
      background: rgba(25, 118, 210, 0.25);
      border-color: #2196f3;
      color: #bbdefb;
    }
    .status-transcribing .status-dot {
      background: #2196f3;
      animation: blink 0.8s infinite;
    }

    .status-success {
      background: rgba(46, 125, 50, 0.35);
      border-color: #66bb6a;
      color: #e8f5e9;
    }
    .status-success .status-dot { background: #66bb6a; }

    .status-failed {
      background: rgba(211, 47, 47, 0.3);
      border-color: #ef5350;
      color: #ffebee;
    }
    .status-failed .status-dot { background: #ef5350; }

    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(229, 57, 53, 0.5); }
      70% { box-shadow: 0 0 0 10px rgba(229, 57, 53, 0); }
      100% { box-shadow: 0 0 0 0 rgba(229, 57, 53, 0); }
    }

    @keyframes blink {
      50% { opacity: 0.2; }
    }

    /* Language row */
    .controls-row {
      display: flex;
      gap: 16px;
      align-items: center;
      margin-bottom: 24px;
    }

    .controls-row label {
      font-size: 13px;
      color: #c8e6c9;
      font-weight: 500;
    }

    select {
      background: #152e1b;
      color: #fff;
      border: 1px solid #2e7d32;
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 14px;
      outline: none;
      cursor: pointer;
    }

    /* Record Button Area */
    .record-area {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 20px 0;
      gap: 16px;
    }

    .mic-button {
      width: 96px;
      height: 96px;
      border-radius: 50%;
      border: none;
      background: linear-gradient(135deg, #2e7d32, #4caf50);
      color: white;
      font-size: 36px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 8px 24px var(--primary-glow);
      transition: all 0.25s ease;
      outline: none;
    }

    .mic-button:hover {
      transform: scale(1.05);
      box-shadow: 0 12px 28px var(--primary-glow);
    }

    .mic-button.recording {
      background: linear-gradient(135deg, #c62828, #e53935);
      box-shadow: 0 8px 28px var(--danger-glow);
      animation: pulse-ring 1.5s infinite;
    }

    @keyframes pulse-ring {
      0% { transform: scale(1); }
      50% { transform: scale(1.08); }
      100% { transform: scale(1); }
    }

    .timer-text {
      font-size: 20px;
      font-weight: 600;
      letter-spacing: 1px;
      color: #e8f5e9;
      font-variant-numeric: tabular-nums;
    }

    .btn-label {
      font-size: 14px;
      color: #c8e6c9;
      font-weight: 500;
    }

    /* Expected sentence box */
    .field-label {
      font-size: 13px;
      font-weight: 600;
      color: #a5d6a7;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 8px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .input-box {
      width: 100%;
      background: #0f2014;
      border: 1px solid #2e7d32;
      border-radius: 10px;
      padding: 12px 14px;
      color: #fff;
      font-size: 15px;
      line-height: 1.5;
      resize: vertical;
      font-family: inherit;
      outline: none;
    }

    .input-box:focus {
      border-color: #4caf50;
      box-shadow: 0 0 0 2px var(--primary-glow);
    }

    /* Actual Transcript Box */
    .transcript-box {
      background: #0f2014;
      border: 1px solid #2e7d32;
      border-radius: 10px;
      padding: 16px;
      min-height: 80px;
      color: #f1f8e9;
      font-size: 16px;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .transcript-box.empty {
      color: #66bb6a88;
      font-style: italic;
    }

    /* Comparison Result */
    .comparison-card {
      background: #112618;
      border: 1px solid #2e7d32;
      border-radius: 12px;
      padding: 16px;
      margin-top: 14px;
      display: none;
    }

    .comparison-title {
      font-weight: 600;
      font-size: 14px;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .match-exact {
      color: #4caf50;
    }
    .match-close {
      color: #ffb74d;
    }
    .match-diff {
      color: #ef5350;
    }

    /* Audio preview */
    .audio-preview {
      width: 100%;
      margin-top: 10px;
      display: none;
    }

    .audio-preview audio {
      width: 100%;
      height: 40px;
    }

    /* Quick helper button */
    .btn-secondary {
      background: #1b3822;
      border: 1px solid #2e7d32;
      color: #c8e6c9;
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
      transition: background 0.2s;
    }
    .btn-secondary:hover {
      background: #264e30;
    }

    .error-box {
      background: rgba(229, 57, 53, 0.15);
      border: 1px solid #ef5350;
      color: #ffcdd2;
      border-radius: 8px;
      padding: 12px;
      font-size: 13px;
      margin-top: 10px;
      display: none;
    }
  </style>
</head>
<body>

  <div class="container">
    <div class="header">
      <h1>🎙️ Sarvam AI Voice-to-Text Test</h1>
      <p>AgriMind AI — Marathi / Hindi Speech Recognition Verification</p>
    </div>

    <div class="card">
      <div class="status-container">
        <span class="field-label" style="margin: 0;">Status</span>
        <div id="statusBadge" class="status-badge status-ready">
          <span class="status-dot"></span>
          <span id="statusText">Ready to Record</span>
        </div>
      </div>

      <div class="controls-row">
        <label for="langSelect">Language:</label>
        <select id="langSelect">
          <option value="mr" selected>मराठी (Marathi - mr-IN)</option>
          <option value="hi">हिंदी (Hindi - hi-IN)</option>
          <option value="unknown">Auto-detect (स्वयंचलित)</option>
          <option value="en">English (en-IN)</option>
        </select>
        <span style="flex: 1;"></span>
        <button id="btnSampleAudio" class="btn-secondary" title="Use verified pre-recorded Marathi audio">
          ▶ Test Sample Marathi Audio
        </button>
      </div>

      <div class="record-area">
        <button id="micBtn" class="mic-button" title="Start Recording">
          <span id="micIcon">🎤</span>
        </button>
        <div id="timerDisplay" class="timer-text">00:00</div>
        <div id="micLabel" class="btn-label">Tap microphone to start recording</div>

        <div id="audioPreview" class="audio-preview">
          <audio id="audioElement" controls></audio>
        </div>
      </div>

      <div id="errorDisplay" class="error-box"></div>
    </div>

    <!-- Expected Sentence -->
    <div class="card">
      <div class="field-label">
        <span>Expected Marathi Sentence (अपेक्षित वाक्य)</span>
        <button class="btn-secondary" onclick="resetExpectedText()">Reset Default</button>
      </div>
      <textarea id="expectedInput" class="input-box" rows="2">माझ्या सोयाबीनच्या पानांवर पिवळे डाग पडले आहेत.</textarea>
    </div>

    <!-- Actual Transcript Result -->
    <div class="card">
      <div class="field-label">
        <span>Actual Transcript from Sarvam API (मिळालेला मजकूर)</span>
        <button id="btnCopy" class="btn-secondary" onclick="copyTranscript()" style="display: none;">Copy</button>
      </div>
      <div id="actualTranscript" class="transcript-box empty">Recording सुरू करा व बोला. येथे Sarvam API कडून आलेला transcript दिसेल.</div>

      <!-- Comparison Card -->
      <div id="comparisonCard" class="comparison-card">
        <div id="comparisonTitle" class="comparison-title">
          <span id="comparisonIcon">✅</span>
          <span id="comparisonText">Match Analysis</span>
        </div>
        <div id="comparisonDetails" style="font-size: 13px; color: #c8e6c9; line-height: 1.5;"></div>
      </div>
    </div>
  </div>

  <script>
    let mediaRecorder = null;
    let audioChunks = [];
    let timerInterval = null;
    let recordStartTime = 0;
    let recordedBlob = null;

    const micBtn = document.getElementById('micBtn');
    const micIcon = document.getElementById('micIcon');
    const micLabel = document.getElementById('micLabel');
    const timerDisplay = document.getElementById('timerDisplay');
    const statusBadge = document.getElementById('statusBadge');
    const statusText = document.getElementById('statusText');
    const langSelect = document.getElementById('langSelect');
    const expectedInput = document.getElementById('expectedInput');
    const actualTranscript = document.getElementById('actualTranscript');
    const comparisonCard = document.getElementById('comparisonCard');
    const comparisonTitle = document.getElementById('comparisonTitle');
    const comparisonText = document.getElementById('comparisonText');
    const comparisonDetails = document.getElementById('comparisonDetails');
    const comparisonIcon = document.getElementById('comparisonIcon');
    const audioPreview = document.getElementById('audioPreview');
    const audioElement = document.getElementById('audioElement');
    const errorDisplay = document.getElementById('errorDisplay');
    const btnCopy = document.getElementById('btnCopy');
    const btnSampleAudio = document.getElementById('btnSampleAudio');

    function setStatus(state, message) {
      statusBadge.className = 'status-badge';
      let text = '';
      if (state === 'ready') {
        statusBadge.classList.add('status-ready');
        text = 'Ready to Record';
      } else if (state === 'recording') {
        statusBadge.classList.add('status-recording');
        text = 'Recording...';
      } else if (state === 'transcribing') {
        statusBadge.classList.add('status-transcribing');
        text = 'Transcribing...';
      } else if (state === 'success') {
        statusBadge.classList.add('status-success');
        text = 'Transcription Successful';
      } else if (state === 'failed') {
        statusBadge.classList.add('status-failed');
        text = 'Transcription Failed';
      }
      statusText.innerText = message || text;
    }

    function showError(msg) {
      if (!msg) {
        errorDisplay.style.display = 'none';
        errorDisplay.innerText = '';
      } else {
        errorDisplay.style.display = 'block';
        errorDisplay.innerText = msg;
      }
    }

    function formatTime(ms) {
      const totalSec = Math.floor(ms / 1000);
      const min = Math.floor(totalSec / 60);
      const sec = totalSec % 60;
      return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
    }

    micBtn.addEventListener('click', async () => {
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        stopRecording();
      } else {
        startRecording();
      }
    });

    async function startRecording() {
      showError(null);
      comparisonCard.style.display = 'none';
      audioPreview.style.display = 'none';
      btnCopy.style.display = 'none';

      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showError('Microphone not supported on this browser/connection. Please use Chrome, Edge, or Firefox over localhost/HTTPS.');
        setStatus('failed');
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];

        // Check supported audio mime types
        let mimeType = 'audio/webm';
        if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
          mimeType = 'audio/webm;codecs=opus';
        } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4';
        }

        mediaRecorder = new MediaRecorder(stream, { mimeType });
        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
          stream.getTracks().forEach(track => track.stop());
          recordedBlob = new Blob(audioChunks, { type: mimeType });
          const audioUrl = URL.createObjectURL(recordedBlob);
          audioElement.src = audioUrl;
          audioPreview.style.display = 'block';
          await submitAudioForTranscription(recordedBlob, mimeType);
        };

        mediaRecorder.start();
        recordStartTime = Date.now();
        timerInterval = setInterval(() => {
          timerDisplay.innerText = formatTime(Date.now() - recordStartTime);
        }, 200);

        micBtn.classList.add('recording');
        micIcon.innerText = '⏹️';
        micLabel.innerText = 'Recording... Tap to Stop & Transcribe';
        setStatus('recording');
      } catch (err) {
        console.error('Microphone permission error:', err);
        showError('Microphone permission denied or device not found: ' + err.message);
        setStatus('failed');
      }
    }

    function stopRecording() {
      if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
      }
      clearInterval(timerInterval);
      micBtn.classList.remove('recording');
      micIcon.innerText = '🎤';
      micLabel.innerText = 'Tap microphone to start recording';
      setStatus('transcribing');
    }

    async function submitAudioForTranscription(blob, mimeType) {
      setStatus('transcribing');
      actualTranscript.className = 'transcript-box empty';
      actualTranscript.innerText = 'Sarvam API कडे पाठवत आहे... कृपया प्रतीक्षा करा...';

      const formData = new FormData();
      const ext = mimeType.includes('mp4') ? 'm4a' : 'webm';
      formData.append('audio', blob, `voice_test.${ext}`);
      formData.append('language', langSelect.value);

      try {
        const resp = await fetch('/api/v1/test/voice-to-text', {
          method: 'POST',
          body: formData,
        });

        const data = await resp.json();
        if (resp.ok && data.success && data.transcript) {
          setStatus('success');
          actualTranscript.className = 'transcript-box';
          actualTranscript.innerText = data.transcript;
          btnCopy.style.display = 'inline-block';
          evaluateMatch(expectedInput.value.trim(), data.transcript.trim());
        } else {
          setStatus('failed');
          actualTranscript.className = 'transcript-box empty';
          const errMsg = data.error || 'No transcript returned by Sarvam API.';
          actualTranscript.innerText = `त्रुटी (Error): ${errMsg}`;
          showError(`Transcription Failed: ${errMsg}`);
        }
      } catch (err) {
        console.error('STT Request Error:', err);
        setStatus('failed');
        actualTranscript.className = 'transcript-box empty';
        actualTranscript.innerText = `Network/API Error: ${err.message}`;
        showError(`Request failed: ${err.message}`);
      }
    }

    function evaluateMatch(expected, actual) {
      if (!actual) return;

      comparisonCard.style.display = 'block';

      // Clean punctuation & normalize for comparison
      const cleanExp = expected.replace(/[।.,!?]/g, '').trim().toLowerCase();
      const cleanAct = actual.replace(/[।.,!?]/g, '').trim().toLowerCase();

      const expWords = cleanExp.split(/\s+/).filter(Boolean);
      const actWords = cleanAct.split(/\s+/).filter(Boolean);

      let matchedWords = 0;
      expWords.forEach(w => {
        if (actWords.includes(w)) matchedWords++;
      });

      const accuracy = expWords.length > 0 ? Math.round((matchedWords / expWords.length) * 100) : 0;

      if (cleanExp === cleanAct || accuracy >= 95) {
        comparisonTitle.className = 'comparison-title match-exact';
        comparisonIcon.innerText = '✅';
        comparisonText.innerText = `Exact / Perfect Match (${accuracy}% Similarity)`;
      } else if (accuracy >= 65) {
        comparisonTitle.className = 'comparison-title match-close';
        comparisonIcon.innerText = '⚡';
        comparisonText.innerText = `High Accuracy Match (${accuracy}% Similarity)`;
      } else {
        comparisonTitle.className = 'comparison-title match-diff';
        comparisonIcon.innerText = '⚠️';
        comparisonText.innerText = `Partial Match (${accuracy}% Similarity)`;
      }

      comparisonDetails.innerHTML = `
        <div style="margin-bottom: 4px;"><strong>Expected (अपेक्षित):</strong> ${escapeHtml(expected)}</div>
        <div style="margin-bottom: 6px;"><strong>Actual (मिळालेला):</strong> ${escapeHtml(actual)}</div>
        <div style="font-size: 12px; color: #81c784;">Matched words: ${matchedWords} / ${expWords.length} (${accuracy}% accuracy)</div>
      `;
    }

    function escapeHtml(text) {
      const div = document.createElement('div');
      div.innerText = text;
      return div.innerHTML;
    }

    function resetExpectedText() {
      expectedInput.value = 'माझ्या सोयाबीनच्या पानांवर पिवळे डाग पडले आहेत.';
    }

    function copyTranscript() {
      const text = actualTranscript.innerText;
      if (text) {
        navigator.clipboard.writeText(text);
        btnCopy.innerText = 'Copied!';
        setTimeout(() => { btnCopy.innerText = 'Copy'; }, 1800);
      }
    }

    // Direct sample audio test
    btnSampleAudio.addEventListener('click', async () => {
      showError(null);
      setStatus('transcribing');
      actualTranscript.className = 'transcript-box empty';
      actualTranscript.innerText = 'Sample Marathi speech file पाठवत आहे...';

      try {
        const resp = await fetch('/api/v1/test/sample-marathi-test', { method: 'POST' });
        const data = await resp.json();
        if (data.success && data.transcript) {
          setStatus('success');
          actualTranscript.className = 'transcript-box';
          actualTranscript.innerText = data.transcript;
          btnCopy.style.display = 'inline-block';
          evaluateMatch(expectedInput.value.trim(), data.transcript.trim());
        } else {
          setStatus('failed');
          actualTranscript.innerText = 'Sample test failed: ' + (data.error || 'Unknown error');
          showError(data.error);
        }
      } catch (e) {
        setStatus('failed');
        showError('Sample test request failed: ' + e.message);
      }
    });
  </script>
</body>
</html>
"""


@router.get("/ui", response_class=HTMLResponse, summary="Interactive Voice Test UI")
def get_voice_test_ui():
    """Renders the isolated web UI for microphone voice-to-text testing."""
    return HTMLResponse(content=_HTML_PAGE, status_code=status.HTTP_200_OK)


@router.post("/sample-marathi-test", summary="Automated 1-Click Test using sample Marathi speech file")
def test_sample_marathi_speech():
    """
    Directly passes the verified sample Marathi audio file ('माझ्या सोयाबीनच्या पानांवर पिवळे डाग पडले आहेत.')
    to the Sarvam STT service and returns the transcript.
    Useful for immediate validation without needing a physical microphone.
    """
    import os
    sample_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "scripts", "sample_marathi_speech.wav"))
    if not os.path.exists(sample_path):
        return {
            "success": False,
            "error": "Sample audio file not found. Please record via microphone.",
            "transcript": None,
        }

    try:
        with open(sample_path, "rb") as f:
            audio_data = f.read()

        transcript = transcribe_audio_bytes(
            file_bytes=audio_data,
            original_filename="sample_marathi_speech.wav",
            content_type="audio/wav",
            language="mr",
        )

        if transcript:
            return {
                "success": True,
                "transcript": transcript,
                "language": "mr-IN",
                "audio_size_bytes": len(audio_data),
            }
        else:
            return {
                "success": False,
                "error": "Sarvam API returned empty transcript for sample audio.",
                "transcript": None,
            }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
            "transcript": None,
        }
