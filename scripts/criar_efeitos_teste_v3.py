# -*- coding: utf-8 -*-
r"""criar_efeitos_teste_v3.py - efeitos com PNGs redondos via overlay (bonitos)."""
import subprocess, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FF = r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"
P = pathlib.Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
SCENES = P / "assets/images/gemini/scenes"
OUT = pathlib.Path(r"C:\videomaker\efeitos_teste3")
OUT.mkdir(exist_ok=True)
ASSETS = pathlib.Path(r"C:\videomaker\efeitos_teste2")
W, H, DUR = 960, 540, 3
imgs = sorted(SCENES.glob("*.jpg"))[:5]

efeitos = [
    ("bolinhas_sabao", "bolinhas de sabao REDONDAS subindo"),
    ("folhinhas_vento", "folhinhas no vento"),
    ("fumacinha", "neblina suave"),
    ("passarinho", "passarinho no ceu"),
    ("poeira_dourada", "poeira dourada cintilante"),
]

def cmd_para(tipo, img, out):
    base = [FF,"-y","-v","error","-loop","1","-i",str(img)]
    if tipo == "bolinhas_sabao":
        for i,(x,y,s) in enumerate([("120+50*sin(t*0.9)","520-170*t","1"),
                                     ("450+60*sin(t*0.7+2)","540-140*t","0.75"),
                                     ("760+40*cos(t*0.8)","530-120*t","0.9")]):
            base += ["-loop","1","-i",str(ASSETS/"bolha.png")]
        filt = (f"[1:v]scale=48:48,format=rgba[b0];"
                f"[2:v]scale=36:36,format=rgba[b1];"
                f"[3:v]scale=44:44,format=rgba[b2];"
                f"[0:v][b0]overlay=x='{x}':y='{y}':enable='gte(t,0)'[o0];"
                f"[o0][b1]overlay=x='{x}':y='{y}'[o1];"
                f"[o1][b2]overlay=x='{x}':y='{y}'[out]")
        # simplifica: 3 overlays independentes com posicoes diferentes
        filt = (f"[1:v]scale=44:44[bb0];[2:v]scale=32:32[bb1];[3:v]scale=40:40[bb2];"
                f"[0:v][bb0]overlay=x='150+50*sin(t*0.9)':y='520-170*t'[o0];"
                f"[o0][bb1]overlay=x='450+60*sin(t*0.7+2)':y='540-140*t'[o1];"
                f"[o1][bb2]overlay=x='760+40*cos(t*0.8)':y='530-120*t'[out]")
        return base + ["-filter_complex",filt,"-map","[out]","-t",str(DUR),"-r","24",
                       "-c:v","libx264","-pix_fmt","yuv420p","-preset","fast",str(out)]
    if tipo == "folhinhas_vento":
        for _ in range(2): base += ["-loop","1","-i",str(ASSETS/"folha.png")]
        filt=("[1:v]scale=24:14[f0];[2:v]scale=18:10[f1];"
              "[0:v][f0]overlay=x='-30+200*t':y='100+40*sin(t*1.5)'[o0];"
              "[o0][f1]overlay=x='-20+160*t':y='230+50*sin(t+1)'[out]")
        return base+["-filter_complex",filt,"-map","[out]","-t",str(DUR),"-r","24",
                     "-c:v","libx264","-pix_fmt","yuv420p","-preset","fast",str(out)]
    if tipo == "passarinho":
        for _ in range(2): base += ["-loop","1","-i",str(ASSETS/"passaro.png")]
        filt=("[1:v]scale=22:11[p0];[2:v]scale=16:8[p1];"
              "[0:v][p0]overlay=x='-40+220*t':y='70+30*sin(t*2)'[o0];"
              "[o0][p1]overlay=x='-30+180*t':y='130+35*sin(t*1.5+1)'[out]")
        return base+["-filter_complex",filt,"-map","[out]","-t",str(DUR),"-r","24",
                     "-c:v","libx264","-pix_fmt","yuv420p","-preset","fast",str(out)]
    if tipo == "poeira_dourada":
        for _ in range(3): base += ["-loop","1","-i",str(ASSETS/"brilho.png")]
        filt=("[1:v]scale=8:8[g0];[2:v]scale=6:6[g1];[3:v]scale=10:10[g2];"
              "[0:v][g0]overlay=x='180+40*sin(t*1.2)':y='500-140*t'[o0];"
              "[o0][g1]overlay=x='520+35*cos(t*1.4)':y='510-120*t'[o1];"
              "[o1][g2]overlay=x='790+30*sin(t+1)':y='505-130*t'[out]")
        return base+["-filter_complex",filt,"-map","[out]","-t",str(DUR),"-r","24",
                     "-c:v","libx264","-pix_fmt","yuv420p","-preset","fast",str(out)]
    if tipo == "fumacinha":
        filt=("drawbox=x='250+30*sin(t*0.6)':y='480-70*t':w=140:h=70:color=white@0.10:t=fill,"
              "drawbox=x='620+35*cos(t*0.5)':y='500-60*t':w=170:h=80:color=white@0.08:t=fill")
        return [FF,"-y","-v","error","-loop","1","-i",str(img),"-t",str(DUR),
                "-vf",f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{filt}",
                "-r","24","-c:v","libx264","-pix_fmt","yuv420p","-preset","fast",str(out)]

def main():
    for (nome,desc),img in zip(efeitos,imgs):
        out=OUT/f"{nome}.mp4"
        r=subprocess.run(cmd_para(nome,img,out),capture_output=True,text=True)
        print(f"{nome:18s} rc={r.returncode} {out.stat().st_size if out.exists() else 0}B {desc}")
        if r.returncode!=0: print("  ERRO:",r.stderr[:250])
    # folha de contato com 2 frames/efeito para ver movimento
    from PIL import Image, ImageDraw, ImageFont
    sheet=Image.new("RGB",(W*2,(H+26)*len(efeitos)),(15,15,15))
    dr=ImageDraw.Draw(sheet); font=ImageFont.load_default()
    for i,(nome,_) in enumerate(efeitos):
        for j,t in enumerate(["0.3","2.5"]):
            f=OUT/f"f_{nome}_{j}.png"
            subprocess.run([FF,"-y","-v","error","-ss",t,"-i",str(OUT/f"{nome}.mp4"),"-frames:v","1",str(f)])
            if f.exists():
                im=Image.open(f).convert("RGB"); im.thumbnail((W-4,H-4))
                sheet.paste(im,(j*W+2,i*(H+26)+2))
        dr.text((4,i*(H+26)+H+4),nome+"  [t=0.3 | t=2.5]",font=font,fill=(255,255,255))
    sheet.save(OUT/"ANTES_DEPOIS.jpg",quality=88)
    print("folha:",OUT/"ANTES_DEPOIS.jpg")

if __name__=="__main__": main()
