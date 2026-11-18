# -*- coding: utf-8 -*-
"""dublar_intro_voicecraft.py - Cria as versoes ES e EN do intro novo,
usando a VOZ APROVADA (VoiceCraft/Gemini Aoede, perfil infantil).

O intro PT (intro-nova-8s.mp4) diz:
  "Bom dia! Bem-vindo ao nosso canal! Aproveite mais uma das nossas aventuras!"

Traducoes:
  ES: "¡Buenos días! ¡Bienvenidos a nuestro canal! ¡Disfruten otra de nuestras aventuras!"
  EN: "Good morning! Welcome to our channel! Enjoy another one of our adventures!"

Tecnica: TTS por frase via VoiceCraft, comprimir (atempo) para caber no beat
real (word-timestamps do audio PT), adelay no inicio do beat, amix, e substituir
o audio do video mantendo o video (lip-sync) intacto.

Saida: intro-nova-8s_es.mp4, intro-nova-8s_en.mp4 em assets/images/gemini/scenes/
"""
from __future__ import annotations
import sys, subprocess, json, tempfile, shutil
from pathlib import Path
import numpy as np
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import soundfile as sf
from faster_whisper import WhisperModel

FF = shutil.which("ffmpeg") or r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
SCENES = P / "assets/images/gemini/scenes"
SRC = SCENES / "intro-nova-8s.mp4"
TMP = P / "artifacts/auditoria/_intro_dub_tmp"
TMP.mkdir(parents=True, exist_ok=True)

FRASES = {
    "es": ["¡Buenos días!",
           "¡Bienvenidos a nuestro canal!",
           "¡Disfruten otra de nuestras aventuras!"],
    "en": ["Good morning!",
           "Welcome to our channel!",
           "Enjoy another one of our adventures!"],
}
# voz aprovada: VoiceCraft (Gemini Aoede, perfil infantil)
VOICECRAFT_URL = "http://127.0.0.1:8090/api/tts"


def extract_audio(path, wav):
    subprocess.run([FF, "-y", "-v", "error", "-i", str(path), "-vn",
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)],
                   check=True)


def beats_do_intro():
    """Extrai os beats (frases) e seus tempos reais do audio PT do intro."""
    wav = TMP / "intro_pt.wav"
    extract_audio(SRC, wav)
    x, sr = sf.read(wav, dtype="float32")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(x, language="pt", beam_size=5)
    beats = [(s.start, s.end, s.text.strip()) for s in segs]
    for a, b, t in beats:
        print(f"  beat {a:.2f}-{b:.2f}s: {t}")
    return beats


def tts_voicecraft(texto, lang, out):
    """Gera fala via VoiceCraft (Gemini Aoede, perfil infantil)."""
    import urllib.request
    payload = json.dumps({"text": texto, "provider": "auto",
                          "profile": "infantil", "language": lang}).encode("utf-8")
    req = urllib.request.Request(VOICECRAFT_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    out.write_bytes(data)
    print(f"  TTS: {len(data)} bytes -> {out.name}")


def duracao(path):
    r = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True)
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    if m:
        return int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
    return 0.0


def main():
    print("=== beats do intro PT ===")
    beats = beats_do_intro()
    if len(beats) < 1:
        print("ERRO: nao foi possivel transcrever o intro")
        sys.exit(1)

    for lang, frases in FRASES.items():
        print(f"\n=== {lang.upper()} ===")
        fits, filtros = [], []
        for i, (frase, (t0, t1, _)) in enumerate(zip(frases, beats)):
            alvo = max(0.5, t1 - t0)
            raw = TMP / f"{lang}_{i}_raw.mp3"
            fit = TMP / f"{lang}_{i}_fit.wav"
            tts_voicecraft(frase, lang, raw)
            d = duracao(raw)
            tempo = max(0.5, min(3.2, d / alvo))
            subprocess.run([FF, "-y", "-v", "error", "-i", str(raw),
                            "-af", f"atempo={tempo:.3f}", "-ar", "44100", "-ac", "1",
                            str(fit)], check=True)
            fits.append(fit)
            delay = int(t0 * 1000)
            filtros.append(f"[{i}:a]adelay={delay}|{delay},apad=pad_dur=8.0,atrim=0:8.0[f{i}]")
            print(f"  beat {i}: {t0:.2f}-{t1:.2f} (alvo {alvo:.2f}s) | tts {d:.2f}s -> {tempo:.2f}x")

        mix = "".join(f"[f{i}]" for i in range(len(fits)))
        filtro = ";".join(filtros) + ";" + mix + f"amix=inputs={len(fits)}:duration=longest:dropout_transition=0[voz]"
        cmd = [FF, "-y", "-v", "error"]
        for f in fits:
            cmd += ["-i", str(f)]
        voz = TMP / f"voz_{lang}.wav"
        cmd += ["-filter_complex", filtro, "-map", "[voz]", "-ar", "44100", "-ac", "2", str(voz)]
        subprocess.run(cmd, check=True)

        out = SCENES / f"intro-nova-8s_{lang}.mp4"
        subprocess.run([FF, "-y", "-v", "error", "-i", str(SRC), "-i", str(voz),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", "-shortest", str(out)], check=True)
        print(f"  SALVO: {out.name} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
