# -*- coding: utf-8 -*-
"""finalizar_es.py - remix do intro ES (voz alta + musica) e corte em 722s."""
import subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FF = r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"
PROJ = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar")
OUT = PROJ / "output"
final = OUT / "a-caminha-nova-que-ninguem-quer-usar_es.mp4"
voz = PROJ / "assets/images/gemini/scenes/intro_8s_es.mp4"
mus = PROJ / "assets/audio/intro_music.m4a"
tmp = Path(r"C:\videomaker\_es_final_tmp.mp4")
novo8 = Path(r"C:\videomaker\_es_novo8.wav")
resto = Path(r"C:\videomaker\_es_resto.wav")
afinal = Path(r"C:\videomaker\_es_afinal.wav")
lista = Path(r"C:\videomaker\_es_lista.txt")

subprocess.run([FF,"-y","-v","error","-i",str(voz),"-i",str(mus),
  "-filter_complex","[0:a]volume=25dB,alimiter=limit=0.95[v];[1:a]volume=-2dB[m];"
  "[v][m]amix=inputs=2:duration=first:dropout_transition=0:weights=1 1,alimiter=limit=0.95[out]",
  "-map","[out]","-t","8","-ar","44100","-ac","2",str(novo8)],check=True)
subprocess.run([FF,"-y","-v","error","-ss","8","-i",str(final),"-vn","-ar","44100","-ac","2",str(resto)],check=True)
lista.write_text(f"file '{novo8.as_posix()}'\nfile '{resto.as_posix()}'\n",encoding="utf-8")
subprocess.run([FF,"-y","-v","error","-f","concat","-safe","0","-i",str(lista),
  "-ar","44100","-ac","2",str(afinal)],check=True)
subprocess.run([FF,"-y","-v","error","-i",str(final),"-i",str(afinal),
  "-map","0:v","-map","1:a","-c:v","copy","-c:a","aac","-b:a","192k",
  "-t","722",str(tmp)],check=True)
tmp.replace(final)
print("ES finalizado:",final,final.stat().st_size)
