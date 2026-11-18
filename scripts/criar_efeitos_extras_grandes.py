# -*- coding: utf-8 -*-
"""criar_efeitos_extras_grandes.py - testes de estrelinhas, abelhas, coracoes,
ossinhos, racao, ZZZ e chuva, com overlay PNG animado."""
import subprocess, sys, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FF=r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"
P=pathlib.Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
SCENES=P/"assets/images/gemini/scenes"
OUT=pathlib.Path(r"C:\videomaker\efeitos_extras_grandes"); OUT.mkdir(exist_ok=True)
A=pathlib.Path(r"C:\videomaker\efeitos_teste2")
W,H,DUR=960,540,3
imgs=sorted(SCENES.glob("*.jpg"))

# (nome, png, [ (x_expr,y_expr,scale), ... ])
EFEITOS=[
 ("estrelinhas","estrela.png",[("120+60*sin(t*1.1)","80+50*cos(t*0.9)",20),("700+50*sin(t+2)","150+40*sin(t*1.3)",16),("400+40*cos(t*0.8)","60+30*sin(t)",24)]),
 ("abelhinhas","abelha.png",[("-30+220*t","120+50*sin(t*2)",22),("990-180*t","300+40*cos(t*1.5)",36)]),
 ("coracoes","coracao.png",[("300+50*sin(t*0.9)","520-130*t",28),("650+40*cos(t*0.7)","540-110*t",44)]),
 ("ossinhos","osso.png",[("200+60*sin(t*0.8)","520-140*t",26),("750+50*cos(t*1.1)","530-120*t",40)]),
 ("racao","racao.png",[("180+40*sin(t*1.2)","500-120*t",14),("520+35*cos(t)","510-100*t",12),("800+30*sin(t+1)","505-110*t",32)]),
 ("soninho_zzz","zzz.png",[("600+30*sin(t*0.6)","180-90*t",80)]),
 ("chuva","gota.png",[("100+20*sin(t)","-20+600*t",10),("300+20*sin(t+1)","-20+580*t",10),("500+20*sin(t+2)","-20+620*t",10),("700+20*cos(t)","-20+560*t",10),("900+20*cos(t+1)","-20+610*t",20)]),
]

def main():
    for i,(nome,png,particulas) in enumerate(EFEITOS):
        img=imgs[i%len(imgs)]
        out=OUT/f"{nome}.mp4"
        cmd=[FF,"-y","-v","error","-loop","1","-i",str(img)]
        for _ in particulas:
            cmd+=["-loop","1","-i",str(A/png)]
        filt=[]; maps=[]
        for j,(x,y,s) in enumerate(particulas):
            lbl=f"p{j}"
            filt.append(f"[{j+1}:v]scale={s}:{s}[{lbl}]")
        # overlay encadeado
        prev="0:v"
        for j,(x,y,s) in enumerate(particulas):
            o=f"o{j}"
            filt.append(f"[{prev}][p{j}]overlay=x='{x}':y='{y}'[{o}]")
            prev=o
        filt.append(f"[{prev}]null[out]")
        cmd+=["-filter_complex",";".join(filt),"-map","[out]","-t",str(DUR),"-r","24",
              "-c:v","libx264","-pix_fmt","yuv420p","-preset","fast",str(out)]
        r=subprocess.run(cmd,capture_output=True,text=True)
        print(f"{nome:14s} rc={r.returncode} {out.stat().st_size if out.exists() else 0}B")
        if r.returncode!=0: print("  ERRO:",r.stderr[:220])
    # folha antes/depois
    from PIL import Image, ImageDraw, ImageFont
    sh=Image.new("RGB",(W*2,(H+26)*len(EFEITOS)),(15,15,15)); dr=ImageDraw.Draw(sh); font=ImageFont.load_default()
    for i,(nome,_,_) in enumerate(EFEITOS):
        for j,t in enumerate(["0.3","2.5"]):
            f=OUT/f"f_{nome}_{j}.png"
            subprocess.run([FF,"-y","-v","error","-ss",t,"-i",str(OUT/f"{nome}.mp4"),"-frames:v","1",str(f)])
            if f.exists():
                im=Image.open(f).convert("RGB"); im.thumbnail((W-4,H-4)); sh.paste(im,(j*W+2,i*(H+26)+2))
        dr.text((4,i*(H+26)+H+4),nome+" [t=0.3 | t=2.5]",font=font,fill=(255,255,255))
    sh.save(OUT/"EFEITOS_GRANDES.jpg",quality=88)
    print("folha:",OUT/"EFEITOS_GRANDES.jpg")
if __name__=="__main__": main()
