# -*- coding: utf-8 -*-
r"""criar_efeitos_teste_v2.py - efeitos VISIVEIS mas elegantes (nao roubam a cena).

Bolinhas de sabao com contorno (drawbox + borda), folhinhas, neblina, passaro,
poeira dourada. Opacidade media (~0.35-0.55) para o movimento ser perceptivel.
"""
import subprocess, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FF = r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"
P = pathlib.Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
SCENES = P / "assets/images/gemini/scenes"
OUT = pathlib.Path(r"C:\videomaker\efeitos_teste2")
OUT.mkdir(exist_ok=True)
W, H, DUR = 960, 540, 3
imgs = sorted(SCENES.glob("*.jpg"))[:5]

efeitos = [
    ("bolinhas_sabao", "bolinhas de sabao subindo (visiveis)"),
    ("folhinhas_vento", "folhinhas no vento"),
    ("fumacinha", "neblina suave"),
    ("passarinho", "passarinho no ceu"),
    ("poeira_dourada", "poeira dourada cintilante"),
]

def bolha(x, y, s, a):
    # quadrado com borda branca = bolha de sabao
    return (f"drawbox=x='{x}':y='{y}':w={s}:h={s}:color=white@{a}:t=fill,"
            f"drawbox=x='{x}':y='{y}':w={s}:h={s}:color=white@0.7:t=3")

def filtro(tipo):
    if tipo == "bolinhas_sabao":
        return (bolha("150+40*sin(t*0.9)", "480-150*t", 22, "0.35") + "," +
                bolha("450+50*sin(t*0.7+2)", "500-120*t", 16, "0.30") + "," +
                bolha("760+35*cos(t*0.8)", "490-100*t", 26, "0.28"))
    if tipo == "folhinhas_vento":
        return ("drawbox=x='-30+200*t':y='90+40*sin(t*1.5)':w=16:h=8:color=0x7CB342@0.55:t=fill,"
                "drawbox=x='-20+160*t':y='210+50*sin(t+1)':w=12:h=6:color=0x8BC34A@0.45:t=fill,"
                "drawbox=x='-25+130*t':y='330+35*cos(t*1.2)':w=18:h=9:color=0x689F38@0.40:t=fill")
    if tipo == "fumacinha":
        return ("drawbox=x='250+30*sin(t*0.6)':y='480-70*t':w=140:h=70:color=white@0.12:t=fill,"
                "drawbox=x='620+35*cos(t*0.5)':y='500-60*t':w=170:h=80:color=white@0.10:t=fill")
    if tipo == "passarinho":
        return ("drawbox=x='-40+220*t':y='70+30*sin(t*2)':w=14:h=5:color=0x222222@0.55:t=fill,"
                "drawbox=x='-30+180*t':y='130+35*sin(t*1.5+1)':w=10:h=4:color=0x333333@0.45:t=fill")
    if tipo == "poeira_dourada":
        return ("drawbox=x='180+40*sin(t*1.2)':y='500-140*t':w=8:h=8:color=0xFFD700@0.75:t=fill,"
                "drawbox=x='520+35*cos(t*1.4)':y='510-120*t':w=6:h=6:color=0xFFE57A@0.65:t=fill,"
                "drawbox=x='790+30*sin(t+1)':y='505-130*t':w=9:h=9:color=0xFFC107@0.60:t=fill")

def main():
    for (nome, desc), img in zip(efeitos, imgs):
        out = OUT / f"{nome}.mp4"
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{filtro(nome)}"
        r = subprocess.run([FF,"-y","-v","error","-loop","1","-i",str(img),"-t",str(DUR),
                            "-vf",vf,"-r","24","-c:v","libx264","-pix_fmt","yuv420p",
                            "-preset","fast",str(out)],capture_output=True,text=True)
        print(f"{nome:18s} rc={r.returncode} {out.stat().st_size if out.exists() else 0}B {desc}")
        if r.returncode!=0: print("  ERRO:",r.stderr[:200])
    # folha de contato (frame t=1.5)
    from PIL import Image, ImageDraw, ImageFont
    sheet=Image.new("RGB",(W, (H+30)*len(efeitos)),(20,20,20))
    dr=ImageDraw.Draw(sheet); font=ImageFont.load_default()
    for i,(nome,_) in enumerate(efeitos):
        f=OUT/f"f_{nome}.png"
        subprocess.run([FF,"-y","-v","error","-ss","1.5","-i",str(OUT/f"{nome}.mp4"),"-frames:v","1",str(f)])
        if f.exists():
            im=Image.open(f).convert("RGB"); im.thumbnail((W-4,H-4)); sheet.paste(im,(2,i*(H+30)+2))
        dr.text((6,i*(H+30)+H+6),nome,font=font,fill=(255,255,255))
    sheet.save(OUT/"TODOS_EFEITOS.jpg",quality=90)
    print("folha:",OUT/"TODOS_EFEITOS.jpg")

if __name__=="__main__": main()
