# Windows：用系统中文语音将分段旁白写成 WAV；依赖与语音都保留在本机。
param([string]$OutputDirectory = "$PSScriptRoot/../../tmp/video/audio")
Add-Type -AssemblyName System.Speech
$speech = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speech.SelectVoice('Microsoft Huihui Desktop')
$speech.Rate = 1
$target = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $target | Out-Null
$parts = Get-Content -LiteralPath "$PSScriptRoot/narration.json" -Raw -Encoding UTF8 | ConvertFrom-Json
try {
  for ($i = 0; $i -lt $parts.Count; $i++) {
    $speech.SetOutputToWaveFile((Join-Path $target ('{0:d2}.wav' -f $i)))
    $speech.Speak($parts[$i].text)
    $speech.SetOutputToNull()
  }
} finally { $speech.Dispose() }
