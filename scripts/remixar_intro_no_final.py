# -*- coding: utf-8 -*-
r"""remixar_intro_no_final.py - corrige SO o audio dos primeiros 8s do video
final, sem re-renderizar:

Problema: no render, voz do intro (-37dB) ficou ABAIXO da musica (-31dB),
entao nao se ouvia. O ajuste anterior (volume=+11dB no MP4) subiu voz E
musica juntas. Aqui separamos as fontes:
  - voz: intro_8s_{lang}.mp4  -> ganho +25dB (ate ~-16dB, nivel da narracao)
  - musica: intro_music.m4a   -> ganho -8dB (fica bem baixinha, so fundo)
  - mixam e substituem os 0-8s do audio final; o resto (8s-691s) fica intacto.
"""
import subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FF = r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"
PROJ = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar")
OUTDIR = PROJ / "output"
SCENES = PROJ / "assets/images/gemini/scenes"
MUSICA = PROJ / "assets/audio/intro_music.m4a"
SUFIXO = sys.argv[1] if len(sys.argv) > 1 else "_pt"


def main():
    final = OUTDIR / f"a-caminha-nova-que-ninguem-quer-usar{SUFIXO}.mp4"
    voz = SCENES / f"intro_8s{SUFIXO.replace('_pt','_pt').replace('_es','_es')}.mp4"
    # intro original para EN (nao ha dublagem)
    if not voz.exists():
        voz = SCENES / "intro_8s.mp4"
    tmp = Path(r"C:\videomaker\_remix_tmp.mp4")

    # 1) novo audio dos primeiros 8s (voz alta + musica baixa)
    novo8 = Path(r"C:\videomaker\_novo8.wav")
    subprocess.run([FF, "-y", "-v", "error", "-i", str(voz), "-i", str(MUSICA),
                    "-filter_complex",
                    "[0:a]volume=25dB,alimiter=limit=0.95[v];"
                    "[1:a]volume=-8dB[m];"
                    "[v][m]amix=inputs=2:duration=first:dropout_transition=0:"
                    "weights=1 1,alimiter=limit=0.95[out]",
                    "-map", "[out]", "-t", "8", "-ar", "44100", "-ac", "2",
                    str(novo8)], check=True)

    # 2) audio do resto (8s -> fim) do video final
    resto = Path(r"C:\videomaker\_resto.wav")
    subprocess.run([FF, "-y", "-v", "error", "-ss", "8", "-i", str(final),
                    "-vn", "-ar", "44100", "-ac", "2", str(resto)], check=True)

    # 3) concatena novo8 + resto
    lista = Path(r"C:\videomaker\_lista_audio.txt")
    lista.write_text(f"file '{novo8.as_posix()}'\nfile '{resto.as_posix()}'\n",
                     encoding="utf-8")
    audio_final = Path(r"C:\videomaker\_audio_final.wav")
    subprocess.run([FF, "-y", "-v", "error", "-f", "concat", "-safe", "0",
                    "-i", str(lista), "-ar", "44100", "-ac", "2",
                    str(audio_final)], check=True)

    # 4) substitui o audio no video (video intacto)
    subprocess.run([FF, "-y", "-v", "error", "-i", str(final), "-i", str(audio_final),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(tmp)], check=True)
    tmp.replace(final)
    print("remixado:", final, final.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
