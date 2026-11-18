# -*- coding: utf-8 -*-
r"""criar_efeitos_final_v2.py - efeitos FINAIS v2: distribuicao em TODA a tela
(x e y), fumaça organica (nuvem irregular, nao bolas), mais elementos.

Salva em C:\videomaker\BIBLIOTECA_EFEITOS\ com guia de uso para o pipeline.
"""
import subprocess, sys, math, random, pathlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from PIL import Image, ImageDraw, ImageFilter
FF=r"C:\videomaker\ffmpeg\bin\ffmpeg.exe"
P=pathlib.Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
SCENES=P/"assets/images/gemini/scenes"
OUT=pathlib.Path(r"C:\videomaker\BIBLIOTECA_EFEITOS"); OUT.mkdir(exist_ok=True)
A=OUT/"assets"; A.mkdir(exist_ok=True)
random.seed(123)
W,H,DUR=960,540,3
imgs=sorted(SCENES.glob("*.jpg"))

def salvar(nome,fn): fn().save(A/f"{nome}.png")

def bolha(t=42):
    im=Image.new("RGBA",(t,t),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([2,2,t-3,t-3],fill=(225,242,255,85),outline=(255,255,255,200),width=2)
    d.ellipse([9,9,20,20],fill=(255,255,255,210)); return im

def folha(t=20):
    im=Image.new("RGBA",(t,t),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([1,t//4,t-1,3*t//4],fill=(155,210,95,230),outline=(120,180,70,255))
    d.line([3,t//2,t-3,t//2],fill=(90,150,50,220)); return im

def estrela(t=22,cor=(255,230,90,240)):
    im=Image.new("RGBA",(t,t),(0,0,0,0)); d=ImageDraw.Draw(im); pts=[]; c=t/2; ro=t/2-2; ri=ro*0.45
    for i in range(10):
        a=math.pi/2+i*math.pi/5; r=ro if i%2==0 else ri
        pts.append((c+r*math.cos(a),c-r*math.sin(a)))
    d.polygon(pts,fill=cor); return im

def coracao(t=26):
    im=Image.new("RGBA",(t,t),(0,0,0,0)); d=ImageDraw.Draw(im); c=(255,95,125,230); h=t//2
    d.ellipse([2,2,h+2,h+2],fill=c); d.ellipse([h-2,2,t-2,h+2],fill=c); d.polygon([(2,h),(t-2,h),(h,t-2)],fill=c); return im

def abelha(t=24):
    im=Image.new("RGBA",(t,t),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([6,9,t-5,t-3],fill=(255,205,45,245),outline=(40,30,10,255))
    for x in (9,15): d.line([x,10,x,2],fill=(235,235,245,235))
    return im

def osso(t=28):
    im=Image.new("RGBA",(t,t),(0,0,0,0)); d=ImageDraw.Draw(im); c=(248,240,220,240)
    d.rectangle([7,11,t-7,t-11],fill=c)
    for x in (4,t-11):
        for y in (7,t-13): d.ellipse([x,y,x+8,y+8],fill=c)
    return im

def racao_formato(tipo,t=16):
    im=Image.new("RGBA",(t,t),(0,0,0,0)); d=ImageDraw.Draw(im); c=(160,95,45,240), (110,60,25,255)
    if tipo=="bola": d.ellipse([2,2,t-2,t-2],fill=c[0],outline=c[1])
    elif tipo=="quad": d.rectangle([3,3,t-3,t-3],fill=c[0],outline=c[1])
    elif tipo=="tri": d.polygon([(t//2,1),(t-1,t-2),(1,t-2)],fill=c[0],outline=c[1])
    elif tipo=="oval": d.ellipse([1,4,t-1,t-4],fill=c[0],outline=c[1])
    elif tipo=="gota": d.ellipse([4,1,t-4,t-1],fill=c[0],outline=c[1]); d.polygon([(t//2,0),(t-2,t-3),(2,t-3)],fill=c[0])
    return im

def zzz(t=34):
    im=Image.new("RGBA",(t*2,t),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.text((0,0),"z",fill=(150,195,255,245)); d.text((13,9),"Z",fill=(175,210,255,250)); d.text((27,18),"Z",fill=(195,225,255,255)); return im

def gota(t=14):
    im=Image.new("RGBA",(t,t),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.polygon([(t//2,0),(t,t-2),(0,t-2)],fill=(130,190,250,220)); return im

def passaro(t=22):
    im=Image.new("RGBA",(t,t),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.line([2,3,t//2,t//2],fill=(25,25,25,235),width=3); d.line([t//2,t//2,t-2,3],fill=(25,25,25,235),width=3); return im

def fumaca_organica(t=220):
    """Nuvem irregular com bordas suaves - nao parece bola."""
    im=Image.new("RGBA",(t,t),(0,0,0,0)); d=ImageDraw.Draw(im)
    rnd=random.Random(99)
    # varios ellipses sobrepostos formando nuvem irregular
    for _ in range(14):
        cx=rnd.randint(50,t-50); cy=rnd.randint(60,t-60)
        rx=rnd.randint(25,70); ry=rnd.randint(18,45)
        d.ellipse([cx-rx,cy-ry,cx+rx,cy+ry],fill=(255,255,255,rnd.randint(14,28)))
    im=im.filter(ImageFilter.GaussianBlur(12))  # suave, sem contorno de bola
    return im

for nome,fn in [("bolha",bolha),("folha",folha),("estrela",estrela),("coracao",coracao),
                ("abelha",abelha),("osso",osso),("zzz",zzz),("gota",gota),("passaro",passaro),
                ("fumaca",fumaca_organica)]: salvar(nome,fn)
for t in ["bola","quad","tri","oval","gota"]: salvar(f"racao_{t}",lambda t=t: racao_formato(t))

# ---- efeitos com distribuicao em TODA a tela ----
def espalhados(prefixo,qtd,xf,yf,escalas,seed):
    r=random.Random(seed); return [(xf(i,r),yf(i,r),r.choice(escalas),f"{prefixo}.png") for i in range(qtd)]

EFEITOS=[]
EFEITOS.append(("bolinhas_sabao",espalhados("bolha",45,
    lambda i,r:f"{r.randint(20,940)}+{r.randint(15,55)}*sin(t*{r.uniform(0.5,1.5):.1f}+{i})",
    lambda i,r:f"{540+r.randint(0,120)}-{r.randint(100,260)}*t*{r.uniform(0.7,1.3):.1f}",
    [20,28,36,44],1)))
# 80 folhinhas em TODA a altura, metade vem da direita
def folha_x(i,r):
    if i%2==0: return f"-40+{r.randint(150,300)}*t*{r.uniform(0.8,1.5):.1f}"
    return f"1000-{r.randint(150,300)}*t*{r.uniform(0.8,1.5):.1f}"
EFEITOS.append(("folhinhas_vento",espalhados("folha",80,folha_x,
    lambda i,r:f"{r.randint(20,520)}+{r.randint(20,70)}*sin(t*{r.uniform(1,2.5):.1f}+{i})",
    [10,14,18,22],2)))
EFEITOS.append(("estrelinhas",espalhados("estrela",50,
    lambda i,r:f"{r.randint(20,940)}+{r.randint(15,50)}*sin(t*{r.uniform(0.8,1.6):.1f}+{i})",
    lambda i,r:f"{r.randint(20,520)}+{r.randint(15,45)}*cos(t*{r.uniform(0.8,1.5):.1f}+{i})",
    [12,16,20,24],3)))
EFEITOS.append(("abelhinhas",espalhados("abelha",24,
    lambda i,r:(f"-40+{r.randint(200,340)}*t*{r.uniform(0.8,1.3):.1f}" if i%2==0 else f"1000-{r.randint(200,340)}*t*{r.uniform(0.8,1.3):.1f}"),
    lambda i,r:f"{r.randint(30,510)}+{r.randint(30,70)}*sin(t*2+{i})",
    [16,20,24,28],4)))
EFEITOS.append(("coracoes",espalhados("coracao",40,
    lambda i,r:f"{r.randint(30,930)}+{r.randint(20,55)}*sin(t*{r.uniform(0.6,1.2):.1f}+{i})",
    lambda i,r:f"{540+r.randint(0,100)}-{r.randint(100,230)}*t*{r.uniform(0.8,1.2):.1f}",
    [16,20,26,30],5)))
EFEITOS.append(("ossinhos",espalhados("osso",30,
    lambda i,r:f"{r.randint(30,930)}+{r.randint(20,55)}*sin(t+{i})",
    lambda i,r:f"{540+r.randint(0,100)}-{r.randint(120,220)}*t*{r.uniform(0.8,1.2):.1f}",
    [18,24,30,34],6)))
r=random.Random(7); racao_parts=[]
for i in range(60):
    t=r.choice(["bola","quad","tri","oval","gota"])
    racao_parts.append((f"{r.randint(30,930)}+{r.randint(15,45)}*sin(t*{r.uniform(0.8,1.5):.1f}+{i})",
                        f"{540+r.randint(0,90)}-{r.randint(100,210)}*t*{r.uniform(0.8,1.3):.1f}",
                        r.choice([9,13,17]),f"racao_{t}.png"))
EFEITOS.append(("racao_varios_formatos",racao_parts))
EFEITOS.append(("soninho_zzz",espalhados("zzz",12,
    lambda i,r:f"{r.randint(60,880)}+{r.randint(20,60)}*sin(t*0.7+{i})",
    lambda i,r:f"{r.randint(80,420)}-{r.randint(80,180)}*t",
    [34,44,54],8)))
EFEITOS.append(("chuva",espalhados("gota",140,
    lambda i,r:f"{(i*53)%960}+{r.randint(5,25)}*sin(t*3+{i})",
    lambda i,r:f"-40+{r.randint(560,800)}*t*{r.uniform(0.9,1.2):.1f}",
    [7,11,15],9)))
EFEITOS.append(("fumacinha",espalhados("fumaca",40,
    lambda i,r:f"{r.randint(20,900)}+{r.randint(20,70)}*sin(t*0.4+{i})",
    lambda i,r:f"{540+r.randint(0,120)}-{r.randint(60,150)}*t*{r.uniform(0.7,1.2):.1f}",
    [120,170,220],10)))
EFEITOS.append(("passarinhos",espalhados("passaro",36,
    lambda i,r:(f"-50+{r.randint(200,360)}*t*{r.uniform(0.8,1.3):.1f}" if i%2==0 else f"1010-{r.randint(200,360)}*t*{r.uniform(0.8,1.3):.1f}"),
    lambda i,r:f"{r.randint(20,250)}+{r.randint(20,60)}*sin(t*2+{i})",
    [16,22,28],11)))

def build_cmd(parts,img,out):
    cmd=[FF,"-y","-v","error","-loop","1","-i",str(img)]
    for p in parts: cmd+=["-loop","1","-i",str(A/p[3])]
    filt=[]; prev="0:v"
    for j,(x,y,s,png) in enumerate(parts):
        lbl=f"p{j}"; o=f"o{j}"
        filt.append(f"[{j+1}:v]scale={s}:{s}[{lbl}]")
        filt.append(f"[{prev}][{lbl}]overlay=x='{x}':y='{y}'[{o}]")
        prev=o
    filt.append(f"[{prev}]null[out]")
    cmd+=["-filter_complex",";".join(filt),"-map","[out]","-t",str(DUR),"-r","24","-c:v","libx264","-pix_fmt","yuv420p","-preset","veryfast",str(out)]
    return cmd

def main():
    for i,(nome,parts) in enumerate(EFEITOS):
        out=OUT/f"{nome}.mp4"; img=imgs[i%len(imgs)]
        r=subprocess.run(build_cmd(parts,img,out),capture_output=True,text=True)
        print(f"{nome:24s} {len(parts):3d} elem rc={r.returncode} {out.stat().st_size if out.exists() else 0}B")
        if r.returncode!=0: print("  ERRO:",r.stderr[:160])
    from PIL import Image, ImageDraw, ImageFont
    sh=Image.new("RGB",(W*2,(H+24)*len(EFEITOS)),(15,15,15)); dr=ImageDraw.Draw(sh); font=ImageFont.load_default()
    for i,(nome,_) in enumerate(EFEITOS):
        for j,t in enumerate(["0.3","2.5"]):
            f=OUT/f"f_{nome}_{j}.png"
            subprocess.run([FF,"-y","-v","error","-ss",t,"-i",str(OUT/f"{nome}.mp4"),"-frames:v","1",str(f)])
            if f.exists():
                im=Image.open(f).convert("RGB"); im.thumbnail((W-4,H-4)); sh.paste(im,(j*W+2,i*(H+24)+2))
        dr.text((4,i*(H+24)+H+2),nome,font=font,fill=(255,255,255))
    sh.save(OUT/"BIBLIOTECA.jpg",quality=88)
    print("folha:",OUT/"BIBLIOTECA.jpg")

if __name__=="__main__": main()
