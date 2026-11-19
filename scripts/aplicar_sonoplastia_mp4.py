# -*- coding: utf-8 -*-
"""aplicar_sonoplastia_mp4.py - Aplica a sonoplastia a um MP4 JA RENDERIZADO,
sem re-renderizar o video (c:v copy).

Como:
  1. Le o mix BASE (sem sonoplastia) e o mix COM sonoplastia do idioma
  2. extrai só os EFEITOS = mix_sono - mix_base
  3. le o audio do MP4 final e soma os efeitos
  4. remuxa o MP4 com o novo audio (-c:v copy, sem perder qualidade)

Uso: python scripts/aplicar_sonoplastia_mp4.py --lang es
"""
from __future__ import annotations
import sys, subprocess, shutil, argparse
from pathlib import Path
import numpy as np
import soundfile as sf

FF = shutil.which("ffmpeg") or r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
AUD = P / "assets/audio"
OUT = P / "output"
SR = 44100


def wav(path, out):
    subprocess.run([FF, "-y", "-v", "error", "-i", str(path), "-ar", str(SR),
                    "-ac", "1", "-c:a", "pcm_s16le", str(out)], check=True)
    return sf.read(out, dtype="float32")[0]


def main(lang):
    video = OUT / f"e-se-os-cachorros-pudessem-falar-por-um-dia_{lang}.mp4"
    if not video.exists():
        print("ERRO: video nao encontrado:", video)
        sys.exit(1)
    mix_base = AUD / "final_mix.m4a"
    mix_sono = AUD / f"final_mix_sonoplastia_{lang}.m4a"
    if not mix_sono.exists():
        print("ERRO: mix com sonoplastia nao encontrado:", mix_sono)
        sys.exit(1)

    tmp = AUD / f"_apply_{lang}"
    tmp.mkdir(exist_ok=True)

    # efeitos = mix_sono - mix_base
    b = wav(mix_base, tmp / "base.wav")
    s = wav(mix_sono, tmp / "sono.wav")
    n = min(len(b), len(s))
    efeitos = s[:n] - b[:n]

    # audio do MP4 final
    a = wav(video, tmp / "audio_mp4.wav")
    m = min(len(a), len(efeitos))
    novo = a[:m].copy()
    novo[:m] += efeitos[:m]
    pk = np.max(np.abs(novo))
    if pk > 0.99:
        novo = novo / pk * 0.99
    sf.write(tmp / "audio_final.wav", novo.astype(np.float32), SR)

    # remux: video copiado + audio novo
    saida = OUT / f"e-se-os-cachorros-pudessem-falar-por-um-dia_{lang}_COM_SONOPLASTIA.mp4"
    subprocess.run([FF, "-y", "-v", "error", "-i", str(video), "-i", str(tmp / "audio_final.wav"),
                    "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(saida)], check=True)
    print(f"OK: {saida} ({saida.stat().st_size} bytes)")

    # substitui o video principal pelo com sonoplastia
    backup = OUT / f"_sem_sonoplastia_{lang}.mp4"
    shutil.copyfile(video, backup)
    shutil.move(str(saida), str(video))
    print(f"video principal atualizado; backup: {backup.name}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=["pt", "es", "en"])
    main(ap.parse_args().lang)
