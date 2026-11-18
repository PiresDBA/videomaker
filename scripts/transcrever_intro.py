# -*- coding: utf-8 -*-
"""transcrever_intro.py - transcreve o audio do intro_8s com faster-whisper.
Passa o audio como array numpy (evita bug de versao do PyAV no decode_audio).
"""
import sys
import numpy as np
import soundfile as sf
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from faster_whisper import WhisperModel

AUDIO = r"C:\videomaker\intro_16k.wav"  # 16kHz mono, convertido com ffmpeg

print("lendo audio...")
data, sr = sf.read(AUDIO, dtype="float32")
if data.ndim > 1:
    data = data.mean(axis=1)
print("audio:", len(data), "amostras @", sr)

print("carregando modelo...")
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe(data, beam_size=5, language="en", vad_filter=True)
print("idioma:", info.language)
print("\n=== SEGMENTOS (fala original) ===")
res = []
for s in segments:
    print(f"[{s.start:5.2f} -> {s.end:5.2f}] {s.text.strip()}")
    res.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
import json
json.dump(res, open(r"C:\videomaker\intro_transcricao.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("\nsalvo intro_transcricao.json")
