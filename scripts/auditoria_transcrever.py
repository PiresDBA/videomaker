# -*- coding: utf-8 -*-
"""auditoria_transcrever.py - Transcreve a narração REAL com timestamps
para auditoria de sincronia imagem/fala. Usa faster-whisper (modelo small).

Converte o WAV para 16kHz mono via ffmpeg antes (evita incompatibilidade
do PyAV com o argumento metadata_errors).

Gera artifacts/auditoria/transcricao.json com segmentos e palavras.
"""
from __future__ import annotations
import json, sys, os, subprocess, tempfile
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from faster_whisper import WhisperModel
import soundfile as sf
import numpy as np

FF = r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
SLUG = (os.environ.get("VIDEOMAKER_PROJ") or "").strip()
for _i, _a in enumerate(sys.argv):
    if _a == "--slug" and _i + 1 < len(sys.argv):
        SLUG = sys.argv[_i + 1]
if not SLUG:
    SLUG = "e-se-os-cachorros-pudessem-falar-por-um-dia"
P = Path(SLUG) if Path(SLUG).is_absolute() else Path(r"C:\videomaker\projects") / SLUG
AUDIO = P / "assets/audio/narration_full_pt.wav"
OUT = P / "artifacts/auditoria"
OUT.mkdir(parents=True, exist_ok=True)

# converte para 16k mono wav PCM (faster-whisper/PyAV compativel)
tmp16 = OUT / "narration_16k.wav"
print("Convertendo audio para 16kHz mono...")
subprocess.run([FF, "-y", "-v", "error", "-i", str(AUDIO),
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(tmp16)],
               check=True)

print("Carregando modelo small...")
model = WhisperModel("small", device="cpu", compute_type="int8")
# le o wav como array numpy (float32 16k) e passa direto -> evita PyAV
audio_np, sr = sf.read(str(tmp16), dtype="float32")
print(f"Audio: {sr}Hz, {len(audio_np)/sr:.1f}s. Transcrevendo...")
segments, info = model.transcribe(
    audio_np, language="pt", beam_size=5,
    vad_filter=True, vad_parameters={"min_silence_duration_ms": 400},
    word_timestamps=True,
)
segs = []
for s in segments:
    words = [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)}
             for w in (s.words or [])]
    segs.append({"start": round(s.start, 3), "end": round(s.end, 3),
                 "text": s.text.strip(), "words": words})
    if len(segs) % 25 == 0:
        print(f"  {len(segs)} segmentos, t={s.end:.1f}s", flush=True)

json.dump({"duration": info.duration, "segments": segs},
          open(OUT / "transcricao.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"OK: {len(segs)} segmentos, duracao {info.duration:.1f}s -> {OUT/'transcricao.json'}")
