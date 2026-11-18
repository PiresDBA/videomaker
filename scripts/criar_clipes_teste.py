# -*- coding: utf-8 -*-
"""criar_clipes_teste.py - Gera clipes curtos com o novo mix de sonoplastia
para o usuario ouvir e aprovar ANTES de renderizar o video inteiro.
"""
from __future__ import annotations
import subprocess, shutil
from pathlib import Path

FF = shutil.which("ffmpeg") or r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
OUT = P / "output"
MIX = P / "assets/audio/final_mix_sonoplastia_earshot.m4a"
VIDEO_SEM = OUT / "e-se-os-cachorros-pudessem-falar-por-um-dia_pt.mp4"  # sem sonoplastia

# (nome, start, dur) - trechos com os efeitos que o usuario pediu
CLIPES = [
    ("TESTE_01_manha_poeirinha_espirro.mp4", 28.0, 50.0),   # passarinhos(31), borboletas(51.5), poeirinha(61.8), espirro(67.6)
    ("TESTE_02_borboleta.mp4",              328.0, 20.0),   # borboleta(331.6), conversa(338.3), dança(342.2)
    ("TESTE_03_carro_pomba.mp4",            272.0, 50.0),   # BUZINA(275/280/285), POMBA(296/299/310/316)
    ("TESTE_04_osso_cantoria.mp4",          611.0, 24.0),   # ossinhos(619), passarinhos(630)
    ("TESTE_05_final_subscribe.mp4",        915.0, 20.0),   # confete(915), inscreva-se(929.9)
]


def main():
    for nome, start, dur in CLIPES:
        dst = OUT / nome
        # pega video do MP4 sem sonoplastia e audio do novo mix
        cmd = [FF, "-y", "-v", "error",
               "-ss", str(start), "-t", str(dur), "-i", str(VIDEO_SEM),
               "-ss", str(start), "-t", str(dur), "-i", str(MIX),
               "-map", "0:v:0", "-map", "1:a:0",
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
               "-c:a", "aac", "-b:a", "192k", "-shortest", str(dst)]
        subprocess.run(cmd, check=True)
        print(f"{nome}: {dst.stat().st_size} bytes ({start}s +{dur}s)")


if __name__ == "__main__":
    main()
