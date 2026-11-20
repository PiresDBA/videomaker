# -*- coding: utf-8 -*-
"""sintetizar_sons.py - Biblioteca de efeitos sonoros REAIS sintetizados com
numpy. Cada som e gerado com forma de onda, harmonicos, envelope ADSR e
modulacao apropriados para soar como o objeto da cena (nao ruido aleatorio).

Saida: assets/audio/sons/*.wav (44100 Hz mono).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import soundfile as sf
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SR = 44100
OUT = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia\assets\audio\sons")
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(2026)


def t_axis(dur):
    return np.linspace(0, dur, int(SR*dur), endpoint=False)


def env_adsr(n, a=0.01, d=0.1, s=0.6, r=0.2):
    """Envelope ADSR simples."""
    na, nd, nr = int(SR*a), int(SR*d), int(SR*r)
    ns = max(0, n - na - nd - nr)
    atk = np.linspace(0, 1, na)
    dec = np.linspace(1, s, nd)
    sus = np.full(ns, s)
    rel = np.linspace(s, 0, nr)
    e = np.concatenate([atk, dec, sus, rel])
    if len(e) < n:
        e = np.pad(e, (0, n-len(e)))
    return e[:n]


def sine(freq, dur, vol=1.0, vibrato=0.0, vib_freq=5.0, glide=0.0):
    t = t_axis(dur)
    f = freq * (1 + glide*t/dur) if glide else np.full_like(t, freq)
    if vibrato:
        f = f * (1 + vibrato*np.sin(2*np.pi*vib_freq*t))
    return (vol*np.sin(2*np.pi*np.cumsum(f)/SR)).astype(np.float64)


def noise(dur, color="white"):
    n = int(SR*dur)
    w = rng.standard_normal(n)
    if color == "pink":
        # filtro pink simplificado (Paul Kellet)
        b0=b1=b2=b3=b4=b5=b6=0.0
        out=np.empty(n)
        for i,x in enumerate(w):
            b0=0.99886*b0+x*0.0555179; b1=0.99332*b1+x*0.0750759
            b2=0.96900*b2+x*0.1538520; b3=0.86650*b3+x*0.3104856
            b4=0.55000*b4+x*0.5329522; b5=-0.7616*b5-x*0.0168980
            out[i]=(b0+b1+b2+b3+b4+b5+b6+x*0.5362)*0.11
            b6=x*0.115926
        return out
    return w


def lowpass(x, cutoff):
    # filtro one-pole (suave o suficiente)
    a = np.exp(-2*np.pi*cutoff/SR)
    y = np.empty_like(x); prev=0.0
    for i,v in enumerate(x):
        prev = (1-a)*v + a*prev
        y[i]=prev
    return y


def bandpass(x, lo, hi):
    return lowpass(x, hi) - lowpass(x, lo)


def normalize(x, peak=0.9):
    m = np.max(np.abs(x))
    return x/m*peak if m>0 else x


def salvar(nome, x):
    sf.write(OUT / f"{nome}.wav", normalize(x).astype(np.float32), SR)
    print(f"  {nome}.wav  {len(x)/SR:.2f}s")


# ---------------------------------------------------------------- sons
def espirro():
    """Espirro cartoon: inspiracao curta + 'A-' forte + 'tchim' estourado."""
    x = np.zeros(int(SR*0.9))
    # 'A' aberto: ruido filtrado 800-2500 Hz com pitch/formante descendente
    a = noise(0.18, "white")
    a = bandpass(a, 700, 2600) * env_adsr(len(a), 0.005, 0.05, 0.3, 0.08)
    x[:len(a)] += a*1.2
    # componente sonora (cordas vocais) com glide descendente
    x[:len(a)] += sine(320, 0.18, 0.5, glide=-0.45)[:len(a)]*env_adsr(len(a),0.005,0.06,0.2,0.08)
    # 'tchim' estourado: burst de ruido + transiente
    b = noise(0.12, "white") * np.exp(-np.arange(int(SR*0.12))/(SR*0.025))
    b = bandpass(b, 1500, 6000)
    s0 = int(SR*0.20)
    x[s0:s0+len(b)] += b*1.5
    x[s0:s0+len(b)] += sine(900, 0.12, 0.6, glide=-0.5)*np.exp(-np.arange(len(b))/(SR*0.03))
    return salvar("espirro", x)


def estrelinha():
    """Tilintar de estrelinha/poeira brilhante: sino com parciais inarmonicos."""
    dur=1.1; t=t_axis(dur)
    # parciais inarmonicos de sino (bell-like)
    partials=[(1.0,0.6),(2.76,0.35),(5.4,0.2),(8.9,0.12)]
    x=np.zeros_like(t)
    for f,amp in partials:
        x += amp*np.sin(2*np.pi*880*f*t)*np.exp(-t*(1.2+0.3*f))
    # some 'shimmer' --
    x += 0.06*noise(dur,"white")*np.exp(-t*3)
    return salvar("estrelinha", x)


def bola_quique():
    """Quique de bola de tenis: 'boing' com pitch subindo + click de contato."""
    dur=0.45; t=t_axis(dur)
    # pitch sobe rapido (caracteristico de bola)
    f = 180 + 260*np.clip(t/0.12,0,1)
    x = 0.7*np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*9)
    # harmonico para corpo
    x += 0.25*np.sin(2*np.pi*np.cumsum(2*f)/SR)*np.exp(-t*12)
    # click inicial
    x[:int(SR*0.008)] += noise(0.008)*np.linspace(1,0,int(SR*0.008))*0.5
    return salvar("bola_quique", x)


def osso_assobio():
    """Osso voador: assobio agudo com vibrato + 'plop' na grama."""
    dur=0.9; t=t_axis(dur)
    assobio = sine(1400, 0.6, 0.6, vibrato=0.02, vib_freq=6, glide=0.25)
    x=np.zeros(int(SR*dur))
    x[:len(assobio)]=assobio*env_adsr(len(assobio),0.03,0.05,0.7,0.15)
    # plop: seno descendente curto + ruido macio
    plop=sine(300,0.15,0.8,glide=-0.7)*np.exp(-np.arange(int(SR*0.15))/(SR*0.04))
    s0=int(SR*0.6)
    x[s0:s0+len(plop)]+=plop
    x[s0:s0+len(plop)]+=lowpass(noise(0.15),800)[:len(plop)]*0.3*np.exp(-np.arange(len(plop))/(SR*0.03))
    return salvar("osso_assobio", x)


def biscoito_crunch():
    """Biscoito crocante: series de transientes curtos (crunch)."""
    dur=0.5; x=np.zeros(int(SR*dur))
    for _ in range(14):
        pos=rng.integers(0,int(SR*0.35))
        ldur=rng.uniform(0.008,0.025)
        ln=int(SR*ldur)
        burst=noise(ldur)*np.exp(-np.arange(ln)/(SR*0.006))
        burst=bandpass(burst,1200,5000)
        x[pos:pos+ln]+=burst*rng.uniform(0.5,1.0)
    return salvar("biscoito_crunch", x)


def carro_passando():
    """Carro: whoosh de passada com Doppler + buzina curta ao longe."""
    dur=1.4; t=t_axis(dur)
    # whoosh: ruido filtrado com volume em arco (passada)
    arco=np.sin(np.pi*np.clip(t/dur,0,1))**2
    whoosh=bandpass(noise(dur,"pink"),200,1200)*arco*1.5
    # buzina distante (dois tons)
    buz=0.18*(np.sin(2*np.pi*420*t)+np.sin(2*np.pi*520*t))*np.exp(-((t-0.7)/0.18)**2)
    x=whoosh+buz
    return salvar("carro_passando", x)


def risadinha():
    """Risadinha infantil 'hehehe' com flite fallback: sintese formante."""
    dur=0.7; t=t_axis(dur)
    # 3 'he' com pitch descendente e formantes
    x=np.zeros_like(t)
    for i,(f0,amp) in enumerate([(330,1.0),(350,0.85),(300,0.7)]):
        s0=int(SR*(0.06+i*0.18))
        seg=t[:int(SR*0.16)]
        voice=(np.sin(2*np.pi*f0*seg)+0.5*np.sin(2*np.pi*2*f0*seg)+0.25*np.sin(2*np.pi*3*f0*seg))
        voice*=env_adsr(len(seg),0.01,0.03,0.4,0.08)
        # adicionar ruido para 'h'
        voice+=0.15*noise(0.16)*np.exp(-np.arange(len(seg))/(SR*0.02))
        if s0+len(seg)<=len(x): x[s0:s0+len(seg)]+=voice*amp
    return salvar("risadinha", x)


def latido():
    """Latido mansinho 'woof': harmonico com formante descendente."""
    dur=0.45; t=t_axis(dur)
    f=260-120*np.clip(t/0.15,0,1)
    x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*6)
    x+=0.4*np.sin(2*np.pi*np.cumsum(f*2)/SR)*np.exp(-t*8)
    x+=0.15*bandpass(noise(dur),600,1800)*np.exp(-t*10)
    return salvar("latido", x)


def vento():
    """Vento suave: ruido pink filtrado com LFO de amplitude."""
    dur=2.0; t=t_axis(dur)
    lfo=0.5+0.5*np.sin(2*np.pi*0.7*t)
    x=lowpass(noise(dur,"pink"),900)*(0.4+0.6*lfo)
    return salvar("vento", x)


def agua_goteira():
    """Agua caindo: borbulhios (senos com pitch ascendente rapido)."""
    dur=1.2; x=np.zeros(int(SR*dur))
    for _ in range(10):
        pos=int(rng.uniform(0,0.9)*SR)
        ln=int(SR*0.09); tt=np.arange(ln)/SR
        f=400+900*tt/0.09
        g=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-tt*22)
        if pos+ln<len(x): x[pos:pos+ln]+=g*0.6
    return salvar("agua_goteira", x)


def passarinho():
    """Pio de passarinho: seno com pitch ascendente/descendente rapido."""
    dur=0.35; t=t_axis(dur)
    # pio: sobe rapido e desce
    f=2000+2500*np.sin(np.pi*np.clip(t/0.2,0,1))
    x=np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-t*7)
    x+=0.2*np.sin(2*np.pi*np.cumsum(2*f)/SR)*np.exp(-t*9)
    return salvar("passarinho", x)


def campainha():
    """Campainha de subscribe: sino brilhante (ding)."""
    dur=1.0; t=t_axis(dur)
    x=np.zeros_like(t)
    for f,amp,dec in [(1046,0.6,2.5),(1568,0.3,3.0),(2093,0.15,4.0)]:
        x+=amp*np.sin(2*np.pi*f*t)*np.exp(-t*dec)
    return salvar("campainha", x)


def passos_patinhas():
    """Passos macios de patinhas na grama: taps abafados."""
    dur=1.0; x=np.zeros(int(SR*dur))
    for i in range(8):
        pos=int(SR*(0.05+i*0.11))
        ln=int(SR*0.05)
        tap=lowpass(noise(0.05),500)*np.exp(-np.arange(ln)/(SR*0.012))
        if pos+ln<len(x): x[pos:pos+ln]+=tap*0.8
    return salvar("passos_patinhas", x)


def barriga_roncando():
    """Ronco de barriga (gurgle): ruido modulado em banda baixa."""
    dur=0.9; t=t_axis(dur)
    x=lowpass(noise(dur,"pink"),250)*(0.5+0.5*np.sin(2*np.pi*8*t))
    x*=np.sin(np.pi*np.clip(t/dur,0,1))
    return salvar("barriga_roncando", x)


if __name__ == "__main__":
    print("Sintetizando biblioteca de sons:")
    espirro(); estrelinha(); bola_quique(); osso_assobio(); biscoito_crunch()
    carro_passando(); risadinha(); latido(); vento(); agua_goteira()
    passarinho(); campainha(); passos_patinhas(); barriga_roncando()
    print("OK ->", OUT)
