# -*- coding: utf-8 -*-
"""sonoplastia_por_idioma.py - Gera sonoplastia SINCRONIZADA com a narração
de cada idioma (PT/ES/EN), usando o banco earshot (252 sons) + sons Forge.

Diferente do sonoplastia_earshot.py (fixo em PT), este:
  1. Transcreve a narração do idioma (faster-whisper word timestamps)
  2. Encontra as palavras-chave NO IDIOMA (dict por lang)
  3. Coloca o som EXATAMENTE no instante da palavra (regra de ouro §65)

Uso: python scripts/sonoplastia_por_idioma.py --lang es
Saida: assets/audio/final_mix_sonoplastia_<lang>.m4a
"""
from __future__ import annotations
import sys, subprocess, shutil, json, re
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

sys.path.insert(0, r"C:\videomaker\earshot-sfx")
from earshot.forge import bank

FF = shutil.which("ffmpeg") or r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
AUD = P / "assets/audio"
SR = 44100

# palavras-chave por idioma -> (id som earshot ou FORGE, ganho, descricao)
PALAVRAS = {
    "pt": {
        "espirro": [("pro_impact/air", 0.90, "espirro")],
        "poirinha": [("shimmer/m4", 0.70, "poeirinha estrelinhas")],
        "poeirinha": [("shimmer/m0", 0.55, "poeirinha magica")],
        "carros": [("BUZINA", 0.55, "buzina carros"), ("whoosh_big/gust", 0.35, "passada")],
        "bombeiros": [("BUZINA", 0.50, "buzina bombeiros")],
        "pombo": [("POMBA", 0.60, "pomba burr-bru")],
        "borboleta": [("hover_tick/air", 0.40, "asinhas borboleta"), ("pro_shimmer/m2", 0.30, "sparkle")],
        "borboletas": [("hover_tick/air", 0.28, "asinhas borboletas")],
        "passarinhos": [("whoosh_fast/whistle", 0.40, "passarinhos")],
        "passarinho": [("pro_pop/chirp", 0.35, "passarinho")],
        "estrelas": [("shimmer/m5", 0.55, "estrelas brilhantes")],
        "ossinhos": [("whoosh_fast/whistle", 0.50, "ossinhos voadores")],
        "bolinha": [("pro_pop/bloop", 0.65, "bolinha quique")],
        "biscoito": [("typing_key/crisp", 0.45, "biscoito crocante")],
        "biscoitos": [("typing_key/light", 0.40, "biscoitos")],
        "gargalhada": [("whoosh_fast/whistle", 0.35, "gargalhada")],
        "risadinha": [("pro_pop/chirp", 0.45, "risadinha")],
        "roncando": [("pro_impact/rumble", 0.50, "barriga roncando")],
        "cantando": [("mallet/glock", 0.40, "xilofone cantoria")],
        "abraço": [("mallet/pluck", 0.40, "carinho abraco")],
        "abranos": [("mallet/pluck", 0.40, "carinho")],
        "bocejo": [("swish/soft", 0.35, "bocejo sopro")],
        "fonte": [("drip/drop", 0.35, "agua fonte")],
        "água": [("drip/bubble", 0.35, "agua")],
        "vento": [("swish/soft", 0.30, "vento")],
        "latido": [("pro_pop/bloop", 0.45, "latidinho")],
        "inscreva": [("fit/bell/small_bell", 0.80, "campainha subscribe")],
    },
    "es": {
        "estornudo": [("pro_impact/air", 0.90, "estornudo")],
        "polvo": [("shimmer/m4", 0.70, "polvo estrellitas")],  # fallback
        "polvillo": [("shimmer/m0", 0.55, "polvillo magico")],
        "polvo de oro": [("shimmer/m4", 0.70, "polvo dorado")],
        "coches": [("BUZINA", 0.55, "bocina coches"), ("whoosh_big/gust", 0.35, "paso")],
        "carros": [("BUZINA", 0.55, "bocina carros")],
        "bomberos": [("BUZINA", 0.50, "bocina bomberos")],
        "paloma": [("POMBA", 0.60, "paloma arrullo")],
        "mariposa": [("hover_tick/air", 0.40, "alas mariposa"), ("pro_shimmer/m2", 0.30, "brillo")],
        "pajaritos": [("whoosh_fast/whistle", 0.40, "pajaritos")],
        "pájaro": [("pro_pop/chirp", 0.35, "pajaro")],
        "estrellas": [("shimmer/m5", 0.55, "estrellas")],
        "huesitos": [("whoosh_fast/whistle", 0.50, "huesitos voladores")],
        "pelota": [("pro_pop/bloop", 0.65, "pelota bote")],
        "galleta": [("typing_key/crisp", 0.45, "galleta crujiente")],
        "risa": [("pro_pop/chirp", 0.45, "risa")],
        "carcajada": [("whoosh_fast/whistle", 0.35, "carcajada")],
        "ronroneo": [("pro_impact/rumble", 0.50, "barriga")],
        "cantando": [("mallet/glock", 0.40, "xilofono")],
        "abrazo": [("mallet/pluck", 0.40, "carino")],
        "bostezo": [("swish/soft", 0.35, "bostezo")],
        "fuente": [("drip/drop", 0.35, "agua fuente")],
        "suscríbete": [("fit/bell/small_bell", 0.80, "campana suscribete")],
    },
    "en": {
        "sneeze": [("pro_impact/air", 0.90, "sneeze")],
        "sparkling": [("shimmer/m4", 0.70, "sparkling dust")],
        "dust": [("shimmer/m0", 0.55, "magic dust")],
        "cars": [("BUZINA", 0.55, "car horn"), ("whoosh_big/gust", 0.35, "pass by")],
        "firefighters": [("BUZINA", 0.50, "firefighter horn")],
        "pigeon": [("POMBA", 0.60, "pigeon coo")],
        "butterfly": [("hover_tick/air", 0.40, "butterfly wings"), ("pro_shimmer/m2", 0.30, "sparkle")],
        "birds": [("whoosh_fast/whistle", 0.40, "birds")],
        "bird": [("pro_pop/chirp", 0.35, "bird chirp")],
        "stars": [("shimmer/m5", 0.55, "stars")],
        "bones": [("whoosh_fast/whistle", 0.50, "flying bones")],
        "ball": [("pro_pop/bloop", 0.65, "ball bounce")],
        "biscuit": [("typing_key/crisp", 0.45, "crunchy biscuit")],
        "laugh": [("pro_pop/chirp", 0.45, "laugh")],
        "rumbling": [("pro_impact/rumble", 0.50, "tummy rumble")],
        "singing": [("mallet/glock", 0.40, "xylophone")],
        "hug": [("mallet/pluck", 0.40, "hug")],
        "yawn": [("swish/soft", 0.35, "yawn")],
        "fountain": [("drip/drop", 0.35, "water fountain")],
        "subscribe": [("fit/bell/small_bell", 0.80, "subscribe bell")],
    },
}


def norm(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def transcrever(lang):
    """Transcreve a narração do idioma e retorna palavras com tempo."""
    wav = AUD / f"_trans_{lang}.wav"
    narr = AUD / f"narration_full_{lang}.wav"
    if not narr.exists():
        narr = AUD / "narration_full.wav"  # fallback
    subprocess.run([FF, "-y", "-v", "error", "-i", str(narr),
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)],
                   check=True)
    x, sr = sf.read(wav, dtype="float32")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(x, language=lang, beam_size=5, word_timestamps=True)
    palavras = []
    for s in segs:
        for w in (s.words or []):
            if w.word.strip():
                palavras.append((norm(w.word.strip().strip(".,!?¡¿")), w.start, w.end))
    return palavras


def render_cue(sid, cache):
    if sid in cache:
        return cache[sid]
    if sid in ("BUZINA", "POMBA"):
        nome = "buzina_bibi.wav" if sid == "BUZINA" else "pomba_coo.wav"
        y, sr = sf.read(AUD / "sons" / nome, dtype="float32")
        if sr != SR:
            n = int(len(y)*SR/sr); y = np.interp(np.linspace(0,len(y),n), np.arange(len(y)), y)
        y = y.astype(np.float32)
    else:
        y, meta = bank.render(sid)
        if getattr(y,"ndim",1)==2: y=y.mean(axis=1)
        if meta.get("sr",SR)!=SR:
            n=int(len(y)*SR/meta["sr"]); y=np.interp(np.linspace(0,len(y),n),np.arange(len(y)),y)
        y=y.astype(np.float32)
    cache[sid]=y
    return y


def main(lang):
    print(f"=== sonoplastia {lang.upper()} ===", flush=True)
    palavras = transcrever(lang)
    print(f"palavras transcritas: {len(palavras)}", flush=True)

    # monta cues: para cada palavra-chave, no tempo da palavra (+8s capa no video)
    cues = []
    usadas = set()
    regras = PALAVRAS[lang]
    # ordena regras por especificidade (frases multi-palavra primeiro)
    for chave, sons in sorted(regras.items(), key=lambda x: -len(x[0])):
        encontradas = []
        for i,(pal,s,e) in enumerate(palavras):
            if chave in pal or (len(chave)>6 and chave[:6] in pal):
                encontradas.append((pal,s,e,i))
        # limita repeticoes (ex.: 'carros' aparece 2x) e evita sobrepor
        for pal,s,e,i in encontradas[:4]:
            if any(abs(s-x[0])<0.3 for x in usadas):
                continue
            usadas.add((s,e))
            for sid,gain,motivo in sons:
                cues.append((s+8.0, sid, gain, f"'{pal}' -> {motivo}"))

    # also ambiente: passarinhos esparsos na pracinha (tempos fixos +8)
    for t in [30.9, 118.4, 131.5, 219.0, 360.2]:
        cues.append((t, "pro_pop/chirp", 0.22, "passarinho ambiente"))

    cues.sort()
    print(f"cues gerados: {len(cues)}", flush=True)

    # mix base
    subprocess.run([FF,"-y","-v","error","-i",str(AUD/f"final_mix.m4a"),
                    "-ar",str(SR),"-ac","1","-c:a","pcm_s16le",str(AUD/"_base_tmp.wav")],check=True)
    base,_=sf.read(AUD/"_base_tmp.wav",dtype="float32")
    out=base.copy(); cache={}
    for t,sid,gain,motivo in cues:
        i0=int(t*SR)
        if i0>=len(out): continue
        try: y=render_cue(sid,cache)
        except Exception as e:
            print(f"  ERRO {sid}: {e}"); continue
        n=min(len(y),len(out)-i0)
        out[i0:i0+n]+=y[:n]*gain
    pk=np.max(np.abs(out))
    if pk>0.99: out=out/pk*0.99
    tmp=AUD/"_sono_tmp.wav"
    sf.write(tmp,out.astype(np.float32),SR)
    saida=AUD/f"final_mix_sonoplastia_{lang}.m4a"
    subprocess.run([FF,"-y","-v","error","-i",str(tmp),"-c:a","aac","-b:a","192k",str(saida)],check=True)
    tmp.unlink(missing_ok=True); (AUD/"_base_tmp.wav").unlink(missing_ok=True)
    print(f"OK: {saida} ({saida.stat().st_size} bytes)", flush=True)


if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--lang",required=True,choices=["pt","es","en"])
    main(ap.parse_args().lang)
