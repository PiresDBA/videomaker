# -*- coding: utf-8 -*-
r"""criar_efeitos_final.py - efeitos FINAIS: 10x mais elementos, todos visiveis,
numa unica pasta. Racao com varios formatos. Opacidades ajustadas.
"""
import subprocess, sys, math, random, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw
FF=r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"
P=pathlib.Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
SCENES=P/"assets/images/gemini/scenes"
OUT=pathlib.Path(r"C:\videomaker\efeitos_FINAL"); OUT.mkdir(exist_ok=True)
A=OUT/"assets"; A.mkdir(exist_ok=True)
random.seed(42)
W,H,DUR=960,540,3
imgs=sorted(SCENES.glob("*.jpg"))

def rgba(im): im.convert("RGBA")

# ---- cria assets ----
def bolha(tam=40):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([2,2,tam-3,tam-3],fill=(225,242,255,75),outline=(255,255,255,190),width=2)
    d.ellipse([8,8,18,18],fill=(255,255,255,200))
    return im

def folha(tam=20):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([1,tam//4,tam-1,3*tam//4],fill=(150,205,90,225),outline=(110,170,60,255))
    d.line([3,tam//2,tam-3,tam//2],fill=(80,140,40,220),width=1)
    return im

def estrela(tam=22,cor=(255,230,90,235)):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    pts=[]; c=tam/2; ro=tam/2-2; ri=ro*0.45
    for i in range(10):
        a=math.pi/2+i*math.pi/5; r=ro if i%2==0 else ri
        pts.append((c+r*math.cos(a),c-r*math.sin(a)))
    d.polygon(pts,fill=cor); return im

def coracao(tam=26):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    c=(255,95,125,225); h=tam//2
    d.ellipse([2,2,h+2,h+2],fill=c); d.ellipse([h-2,2,tam-2,h+2],fill=c)
    d.polygon([(2,h),(tam-2,h),(h,tam-2)],fill=c); return im

def abelha(tam=24):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([6,9,tam-5,tam-3],fill=(255,200,40,240),outline=(40,30,10,255))
    for x in (9,15): d.line([x,10,x,2],fill=(235,235,245,230),width=1)
    return im

def osso(tam=28):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    c=(248,240,220,235); d.rectangle([7,11,tam-7,tam-11],fill=c)
    for x in (4,tam-11):
        for y in (7,tam-13): d.ellipse([x,y,x+8,y+8],fill=c)
    return im

def racao_formato(tipo,tam=16):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    c=(160,95,45,235), (110,60,25,255)
    if tipo=="bola": d.ellipse([2,2,tam-2,tam-2],fill=c[0],outline=c[1])
    elif tipo=="quad": d.rectangle([3,3,tam-3,tam-3],fill=c[0],outline=c[1])
    elif tipo=="tri": d.polygon([(tam//2,1),(tam-1,tam-2),(1,tam-2)],fill=c[0],outline=c[1])
    elif tipo=="oval": d.ellipse([1,4,tam-1,tam-4],fill=c[0],outline=c[1])
    elif tipo=="gota": d.ellipse([4,1,tam-4,tam-1],fill=c[0],outline=c[1]); d.polygon([(tam//2,0),(tam-2,tam-3),(2,tam-3)],fill=c[0])
    return im

def zzz(tam=34):
    im=Image.new("RGBA",(tam*2,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.text((0,0),"z",fill=(150,195,255,240)); d.text((13,9),"Z",fill=(175,210,255,245))
    d.text((27,18),"Z",fill=(195,225,255,250)); return im

def gota(tam=14):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.polygon([(tam//2,0),(tam,tam-2),(0,tam-2)],fill=(130,190,250,210)); return im

def fumaca(tam=120):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    for r,(x,y) in zip([55,42,30,20],[(60,60),(45,55),(70,50),(55,70)]):
        d.ellipse([x-r,y-r,x+r,y+r],fill=(255,255,255,26))
    return im

for nome,fn in [("bolha",bolha),("folha",folha),("estrela",estrela),("coracao",coracao),
                ("abelha",abelha),("osso",osso),("zzz",zzz),("gota",gota),("fumaca",fumaca)]:
    fn().save(A/f"{nome}.png")
for t in ["bola","quad","tri","oval","gota"]:
    racao_formato(t).save(A/f"racao_{t}.png")

# ---- geradores de comando (10x elementos) ----
def overlays(prefixo, qtd, xf, yf, escalas, seed=0):
    """Gera lista de (x_expr,y_expr,scale,png) com posicoes variadas."""
    rnd=random.Random(seed); out=[]
    for i in range(qtd):
        sx=rnd.choice(escalas)
        out.append((xf(i,rnd),yf(i,rnd),sx,f"{prefixo}.png"))
    return out

EFEITOS=[]
# bolinhas: 30
EFEITOS.append(("bolinhas_sabao", overlays("bolha",30,
    lambda i,r: f"{r.randint(20,940)}+{r.randint(20,70)}*sin(t*{r.uniform(0.5,1.5):.1f}+{i})",
    lambda i,r: f"{540+r.randint(0,100)}-{r.randint(80,220)}*t*{r.uniform(0.7,1.3):.1f}",
    [28,34,40,46],1)))
# folhinhas: 50, verdes claros
EFEITOS.append(("folhinhas_vento", overlays("folha",50,
    lambda i,r: f"-40+{r.randint(120,260)}*t*{r.uniform(0.7,1.4):.1f}",
    lambda i,r: f"{r.randint(30,510)}+{r.randint(20,60)}*sin(t*{r.uniform(1,2.5):.1f}+{i})",
    [12,16,20,24],2)))
# estrelinhas: 30
EFEITOS.append(("estrelinhas", overlays("estrela",30,
    lambda i,r: f"{r.randint(30,930)}+{r.randint(15,50)}*sin(t*{r.uniform(0.8,1.6):.1f}+{i})",
    lambda i,r: f"{r.randint(30,500)}+{r.randint(15,40)}*cos(t*{r.uniform(0.8,1.5):.1f}+{i})",
    [14,18,22,26],3)))
# abelhinhas: 12
EFEITOS.append(("abelhinhas", overlays("abelha",12,
    lambda i,r: f"-40+{r.randint(180,300)}*t*{r.uniform(0.8,1.3):.1f}",
    lambda i,r: f"{r.randint(60,480)}+{r.randint(25,60)}*sin(t*2+{i})",
    [18,22,26],4)))
# coracoes: 25
EFEITOS.append(("coracoes", overlays("coracao",25,
    lambda i,r: f"{r.randint(40,920)}+{r.randint(20,50)}*sin(t*{r.uniform(0.6,1.2):.1f}+{i})",
    lambda i,r: f"{540+r.randint(0,80)}-{r.randint(90,200)}*t*{r.uniform(0.8,1.2):.1f}",
    [18,22,26,30],5)))
# ossinhos: 20
EFEITOS.append(("ossinhos", overlays("osso",20,
    lambda i,r: f"{r.randint(40,920)}+{r.randint(20,50)}*sin(t+{i})",
    lambda i,r: f"{540+r.randint(0,80)}-{r.randint(100,180)}*t*{r.uniform(0.8,1.2):.1f}",
    [20,24,28,32],6)))
# racao: 40 com formatos mistos
rnd=random.Random(7); racao_parts=[]
for i in range(40):
    t=rnd.choice(["bola","quad","tri","oval","gota"])
    racao_parts.append((f"{rnd.randint(30,930)}+{rnd.randint(15,40)}*sin(t*{rnd.uniform(0.8,1.5):.1f}+{i})",
                        f"{540+rnd.randint(0,80)}-{rnd.randint(80,180)}*t*{rnd.uniform(0.8,1.3):.1f}",
                        rnd.choice([10,14,18]),f"racao_{t}.png"))
EFEITOS.append(("racao_varios_formatos",racao_parts))
# soninho: 6 (mais visiveis)
EFEITOS.append(("soninho_zzz",overlays("zzz",6,
    lambda i,r: f"{r.randint(100,800)}+{r.randint(20,50)}*sin(t*0.7+{i})",
    lambda i,r: f"{300+r.randint(0,100)}-{r.randint(60,140)}*t",
    [40,50,60],8)))
# chuva: 80 gotas
EFEITOS.append(("chuva",overlays("gota",80,
    lambda i,r: f"{(i*37)%960}+{r.randint(5,20)}*sin(t*3+{i})",
    lambda i,r: f"-30+{r.randint(500,800)}*t*{r.uniform(0.9,1.2):.1f}",
    [8,12,16],9)))
# fumaca: 30 nuvens grandes, opacidade via alpha do PNG (26) - aumenta qtd
EFEITOS.append(("fumacinha",overlays("fumaca",30,
    lambda i,r: f"{r.randint(50,900)}+{r.randint(20,60)}*sin(t*0.4+{i})",
    lambda i,r: f"{540+r.randint(0,100)}-{r.randint(50,120)}*t*{r.uniform(0.7,1.2):.1f}",
    [100,140,180],10)))
# passarinho: 20 (mais visiveis - usa estrela escura? cria png passaro)
def passaro(tam=22):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.line([2,3,tam//2,tam//2],fill=(25,25,25,230),width=3)
    d.line([tam//2,tam//2,tam-2,3],fill=(25,25,25,230),width=3)
    return im
passaro().save(A/"passaro.png")
EFEITOS.append(("passarinhos",overlays("passaro",20,
    lambda i,r: f"-50+{r.randint(180,320)}*t*{r.uniform(0.8,1.3):.1f}",
    lambda i,r: f"{r.randint(40,300)}+{r.randint(20,50)}*sin(t*2+{i})",
    [18,24,30],11)))

def build_cmd(nome,parts,img,out):
    cmd=[FF,"-y","-v","error","-loop","1","-i",str(img)]
    for _ in parts: cmd+=["-loop","1","-i",str(A/_[3])]
    filt=[]; prev="0:v"
    for j,(x,y,s,png) in enumerate(parts):
        lbl=f"p{j}"; o=f"o{j}"
        filt.append(f"[{j+1}:v]scale={s}:{s}[{lbl}]")
        filt.append(f"[{prev}][{lbl}]overlay=x='{x}':y='{y}'[{o}]")
        prev=o
    filt.append(f"[{prev}]null[out]")
    cmd+=["-filter_complex",";".join(filt),"-map","[out]","-t",str(DUR),"-r","24",
          "-c:v","libx264","-pix_fmt","yuv420p","-preset","veryfast",str(out)]
    return cmd

def main():
    for i,(nome,parts) in enumerate(EFEITOS):
        out=OUT/f"{nome}.mp4"; img=imgs[i%len(imgs)]
        r=subprocess.run(build_cmd(nome,parts,img,out),capture_output=True,text=True)
        print(f"{nome:24s} {len(parts):3d} elem rc={r.returncode} {out.stat().st_size if out.exists() else 0}B")
        if r.returncode!=0: print("  ERRO:",r.stderr[:200])
    # folha contato (2 frames/efeito)
    from PIL import Image, ImageDraw, ImageFont
    sh=Image.new("RGB",(W*2,(H+24)*len(EFEITOS)),(15,15,15)); dr=ImageDraw.Draw(sh); font=ImageFont.load_default()
    for i,(nome,_) in enumerate(EFEITOS):
        for j,t in enumerate(["0.3","2.5"]):
            f=OUT/f"f_{nome}_{j}.png"
            subprocess.run([FF,"-y","-v","error","-ss",t,"-i",str(OUT/f"{nome}.mp4"),"-frames:v","1",str(f)])
            if f.exists():
                im=Image.open(f).convert("RGB"); im.thumbnail((W-4,H-4)); sh.paste(im,(j*W+2,i*(H+24)+2))
        dr.text((4,i*(H+24)+H+2),nome,font=font,fill=(255,255,255))
    sh.save(OUT/"TODOS_OS_EFEITOS.jpg",quality=88)
    print("folha:",OUT/"TODOS_OS_EFEITOS.jpg")

if __name__=="__main__": main()
