# -*- coding: utf-8 -*-
r"""ajustar_final_pt.py - ajustes finais no MP4 renderizado (PT):

1. Aumenta a VOZ DO INTRO (primeiros 8s) em +11 dB com limiter, para ficar
   no mesmo nivel da narracao (intro -30dB -> -19dB, narracao -17dB).
2. Corta o vídeo em 691s (11:31), removendo os ~14s de tela escura com musica
   que havia entre o subscribe e o fim.

Uso: python scripts/ajustar_final_pt.py
(para EN/ES, trocar SUFIXO e DUR_FINAL conforme necessario)
"""
import subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FF = r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"
OUTDIR = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar\output")
SUFIXO = "_pt"
DUR_FINAL = 691.0  # corta aqui (subscribe termina ~691s)
GANHO_INTRO_DB = 11.0


def main():
    src = OUTDIR / f"a-caminha-nova-que-ninguem-quer-usar{SUFIXO}.mp4"
    tmp = Path(r"C:\videomaker\_ajuste_tmp.mp4")
    filtro = (f"[0:a]volume={GANHO_INTRO_DB}dB:enable='lt(t,8)',"
              f"alimiter=limit=0.92[a]")
    subprocess.run([FF, "-y", "-v", "error", "-i", str(src),
                    "-filter_complex", filtro, "-map", "0:v", "-map", "[a]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", str(DUR_FINAL), str(tmp)], check=True)
    tmp.replace(src)
    print("ajustado:", src, src.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
