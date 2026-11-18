# -*- coding: utf-8 -*-
"""criar_bolha_png2.py - mais PNGs de efeitos tematicos (transparentes)."""
from PIL import Image, ImageDraw
import pathlib
OUT = pathlib.Path(r"C:\videomaker\efeitos_teste2")
OUT.mkdir(exist_ok=True)

def estrela(tam=24, cor=(255,225,80,220)):
    import math
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    pts=[]; cx=cy=tam/2; ro=tam/2-2; ri=ro*0.45
    for i in range(10):
        a=math.pi/2+i*math.pi/5
        r=ro if i%2==0 else ri
        pts.append((cx+r*math.cos(a),cy-r*math.sin(a)))
    d.polygon(pts,fill=cor); return im

def coracao(tam=28, cor=(255,90,120,210)):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([2,2,tam//2+2,tam//2+2],fill=cor)
    d.ellipse([tam//2-2,2,tam-2,tam//2+2],fill=cor)
    d.polygon([(2,tam//2),(tam-2,tam//2),(tam//2,tam-2)],fill=cor)
    return im

def abelha(tam=22):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([5,8,tam-5,tam-3],fill=(255,200,40,230),outline=(40,30,10,255))
    d.line([8,10,8,2],fill=(230,230,240,200),width=1)
    d.line([14,10,14,2],fill=(230,230,240,200),width=1)
    d.polygon([(8,4),(6,0),(11,2)],fill=(255,255,255,220))
    d.polygon([(14,4),(16,0),(11,2)],fill=(255,255,255,220))
    return im

def osso(tam=26):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    c=(248,240,220,230)
    d.rectangle([6,10,tam-6,tam-10],fill=c)
    for x in (4,tam-10):
        for y in (6,tam-12):
            d.ellipse([x,y,x+8,y+8],fill=c)
    return im

def racao(tam=16):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([2,2,tam-2,tam-2],fill=(150,90,45,225),outline=(100,55,25,255))
    return im

def zzz(tam=28):
    im=Image.new("RGBA",(tam*2,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.text((0,0),"z",fill=(150,190,255,230)); d.text((12,8),"Z",fill=(170,205,255,235))
    d.text((26,16),"Z",fill=(190,220,255,240))
    return im

def gota(tam=12):
    im=Image.new("RGBA",(tam,tam),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.polygon([(tam//2,0),(tam,tam-2),(0,tam-2)],fill=(120,180,240,180))
    return im

estrela().save(OUT/"estrela.png")
coracao().save(OUT/"coracao.png")
abelha().save(OUT/"abelha.png")
osso().save(OUT/"osso.png")
racao().save(OUT/"racao.png")
zzz().save(OUT/"zzz.png")
gota().save(OUT/"gota.png")
print("PNGs extras criados")
