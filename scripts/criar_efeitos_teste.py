# -*- coding: utf-8 -*-
r"""criar_efeitos_teste.py - 5 mini-videos (3s) com efeitos SUTEIS de movimento
para o usuario aprovar. Opacidades baixas, movimentos lentos - nao roubam a cena.

1. micro bolinhas de sabao subindo
2. folhinhas suaves no vento
3. neblina/fumacinha muito leve
4. passarinho distante no ceu
5. poeira dourada cintilante + leve brilho
"""
import subprocess, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FF = r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"
P = pathlib.Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
SCENES = P / "assets/images/gemini/scenes"
OUT = pathlib.Path(r"C:\videomaker\efeitos_teste")
OUT.mkdir(exist_ok=True)
W, H, DUR = 960, 540, 3
imgs = sorted(SCENES.glob("*.jpg"))[:5]

efeitos = [
    ("bolinhas_sabao", "micro bolinhas de sabao subindo"),
    ("folhinhas_vento", "folhinhas suaves no vento"),
    ("fumacinha", "neblina muito leve"),
    ("passarinho", "passarinho distante no ceu"),
    ("poeira_dourada", "poeira dourada cintilante"),
]

def filtro(tipo):
    if tipo == "bolinhas_sabao":
        return ("drawbox=x='120+25*sin(t*0.8)':y='500-130*t':w=10:h=10:color=white@0.18:t=fill,"
                "drawbox=x='430+30*sin(t*0.6+2)':y='520-100*t':w=7:h=7:color=white@0.15:t=fill,"
                "drawbox=x='720+20*cos(t*0.7)':y='510-90*t':w=12:h=12:color=white@0.12:t=fill")
    if tipo == "folhinhas_vento":
        return ("drawbox=x='-30+180*t':y='100+30*sin(t*1.2)':w=10:h=5:color=0x7CB342@0.25:t=fill,"
                "drawbox=x='-20+140*t':y='220+40*sin(t+1)':w=8:h=4:color=0x8BC34A@0.20:t=fill")
    if tipo == "fumacinha":
        return ("drawbox=x='250+20*sin(t*0.5)':y='480-60*t':w=100:h=40:color=white@0.04:t=fill,"
                "drawbox=x='620+25*cos(t*0.4)':y='495-45*t':w=120:h=50:color=white@0.03:t=fill")
    if tipo == "passarinho":
        return ("drawbox=x='-40+180*t':y='80+20*sin(t*1.5)':w=8:h=3:color=0x222222@0.35:t=fill,"
                "drawbox=x='-30+150*t':y='130+25*sin(t+1)':w=6:h=2:color=0x333333@0.28:t=fill")
    if tipo == "poeira_dourada":
        return ("drawbox=x='180+30*sin(t)':y='510-110*t':w=4:h=4:color=0xFFD700@0.40:t=fill,"
                "drawbox=x='520+25*cos(t*1.2)':y='520-95*t':w=3:h=3:color=0xFFE57A@0.35:t=fill,"
                "drawbox=x='790+20*sin(t+1)':y='515-100*t':w=5:h=5:color=0xFFC107@0.30:t=fill")

def main():
    for (nome, desc), img in zip(efeitos, imgs):
        out = OUT / f"{nome}.mp4"
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{filtro(nome)}"
        r = subprocess.run([FF,"-y","-v","error","-loop","1","-i",str(img),"-t",str(DUR),
                            "-vf",vf,"-r","24","-c:v","libx264","-pix_fmt","yuv420p",
                            "-preset","fast",str(out)],capture_output=True,text=True)
        print(f"{nome:18s} {desc:32s} rc={r.returncode} {out.stat().st_size if out.exists() else 0}B")
        if r.returncode!=0: print("  ERRO:",r.stderr[:160])

if __name__=="__main__": main()
