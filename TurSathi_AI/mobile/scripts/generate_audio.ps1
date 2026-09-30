Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$dir = "c:\Users\admin\OneDrive\Documents\Desktop\TurSathi AI\TurSathi_AI\mobile\assets\audio"
if (!(Test-Path $dir)) {
    New-Item -ItemType Directory -Force -Path $dir
}
$filePath = Join-Path $dir "tur_leaf_scan_guide.wav"
$synth.SetOutputToWaveFile($filePath)
$synth.Speak("Place one healthy-looking Tur leaf clearly inside the camera frame. Keep the leaf in good natural light, avoid blur, and make sure the leaf is fully visible before capturing the photo.")
$synth.Dispose()
Write-Host "Generated audio at $filePath"
