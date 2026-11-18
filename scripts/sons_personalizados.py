# -*- coding: utf-8 -*-
"""sons_personalizados.py - Sons que o banco earshot NAO tem, criados com
o Forge (sintese numpy): buzina de carro 'bibi' e pomba 'burr-bru'.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import soundfile as sf

SR = 44100
OUT = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia\assets\audio\sons")
OUT.mkdir(parents=True, exist_ok=True)


def env(n, a=0.01, r=0.1):
    na, nr = int(SR*a), int(SR*r)
    ns = max(0, n-na-nr)
    e = np.concatenate([np.linspace(0,1,na), np.ones(ns), np.linspace(1,0,nr)])
    if len(e) < n: e = np.pad(e,(0,n-len(e)))
    return e[:n]


def buzina():
    """Buzina de carro 'bi-bi': dois tons (fá# + lá), 2 toques curtos."""
    dur=0.75; t=np.arange(int(SR*dur))/SR
    x=np.zeros_like(t)
    for s0 in [0.0, 0.32]:
        i=int(s0*SR); n=int(SR*0.22)
        tt=np.arange(n)/SR
        # buzina: dois tons-harmonicos (440 + 554 = terça) com raspinho
        tone=(np.sin(2*np.pi*440*tt)+0.7*np.sin(2*np.pi*554*tt)+
              0.3*np.sin(2*np.pi*880*tt))
        tone*=env(n,0.012,0.06)*0.55
        if i+n<=len(x): x[i:i+n]+=tone
    m=np.max(np.abs(x)); x=x/m*0.9 if m else x
    sf.write(OUT/"buzina_bibi.wav", x.astype(np.float32), SR)
    print("buzina_bibi.wav", dur,"s")


def pomba():
    """Pomba 'burr-bru': coo grave com vibrato e duas silabas."""
    dur=0.85; x=np.zeros(int(SR*dur))
    for s0,f0 in [(0.0,230),(0.38,200)]:
        i=int(s0*SR); n=int(SR*0.34); tt=np.arange(n)/SR
        # 'coo': seno com vibrato + harmonicos suaves, pitch caindo
        f=f0*(1-0.12*tt/0.34)*(1+0.02*np.sin(2*np.pi*7*tt))
        coo=(np.sin(2*np.pi*np.cumsum(f)/SR)+
             0.35*np.sin(2*np.pi*np.cumsum(2*f)/SR)+
             0.12*np.sin(2*np.pi*np.cumsum(3*f)/SR))
        coo*=env(n,0.05,0.12)*0.6
        if i+n<=len(x): x[i:i+n]+=coo
    m=np.max(np.abs(x)); x=x/m*0.9 if m else x
    sf.write(OUT/"pomba_coo.wav", x.astype(np.float32), SR)
    print("pomba_coo.wav", dur,"s")


if __name__=="__main__":
    buzina(); pomba()
    print("OK ->", OUT)
