# -*- coding: utf-8 -*-
"""finalizar_novo.py - ajustes finais do projeto 'cachorros falaram':
1. remix intro PT (voz +25dB, musica -2dB) nos primeiros 8s
2. corte em 744s (remove tela escura final)
"""
import subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FF = r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"
PROJ = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
OUT = PROJ / "output"
final = OUT / "e-se-os-cachorros-pudessem-falar-por-um-dia_pt.mp4"
voz = PROJ / "assets/images/gemini/scenes/intro_8s_pt.mp4"
mus = PROJ / "assets/audio/intro_music.m4a"
tmp = Path(r"C:\videomaker\_novo_final_tmp.mp4")
novo8 = Path(r"C:\videomaker\_novo_novo8.wav")
resto = Path(r"C:\videomaker\_novo_resto.wav")
afinal = Path(r"C:\videomaker\_novo_afinal.wav")
lista = Path(r"C:\videomaker\_novo_lista.txt")

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
  "-t","744",str(tmp)],check=True)
tmp.replace(final)
print("finalizado:",final,final.stat().st_size)
