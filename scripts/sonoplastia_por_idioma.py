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
import sys, subprocess, shutil, json, re, os
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel

sys.path.insert(0, r"C:\videomaker\earshot-sfx")
from earshot.forge import bank

FF = shutil.which("ffmpeg") or r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
# REGRA: slug via --slug (ou VIDEOMAKER_PROJ); NUNCA slug fixo de projeto antigo.
SLUG = (os.environ.get("VIDEOMAKER_PROJ") or "").strip()
for _i, _a in enumerate(sys.argv):
    if _a == "--slug" and _i + 1 < len(sys.argv):
        SLUG = sys.argv[_i + 1]
if not SLUG:
    SLUG = "e-se-os-cachorros-pudessem-falar-por-um-dia"
P = Path(SLUG) if Path(SLUG).is_absolute() else Path(r"C:\videomaker\projects") / SLUG
AUD = P / "assets/audio"
SR = 44100

# palavras-chave por idioma -> (id som earshot ou FORGE, ganho, descricao)
PALAVRAS = {
    "pt": {
        # ---- ACOES REAIS DO ROTEIRO "sozinhas em casa" (2026-11-19) ----
        # Antes so 5 chaves casavam com o texto (14 cues). Agora o dicionario
        # foi reescrito com as palavras que a narracao REALMENTE fala.
        "meia": [("swish/soft", 0.26, "puxao da meia"), ("typing_key/light", 0.15, "attrito")],
        "corredor": [("swish/soft", 0.16, "passos no corredor")],
        "piso": [("pro_tap/soft", 0.18, "patinha no piso")],
        "patinha": [("pro_tap/finger", 0.26, "patinha")],
        "patinhas": [("pro_tap/double", 0.24, "patinhas")],
        "espelho": [("pro_click/glass", 0.24, "espelho")],
        "reflexo": [("shimmer/m2", 0.20, "reflexo")],
        "livro": [("fit/land.light/fingertip_book", 0.24, "livro")],
        "almofada": [("pro_tap/soft", 0.24, "almofada")],
        "sofá": [("pro_tap/soft", 0.22, "sofá macio"), ("pro_impact/rumble", 0.14, "corpo no sofá")],
        "cozinha": [("pro_tap/table", 0.14, "cozinha")],
        "porta": [("knock/wood", 0.26, "porta")],
        "tapete": [("swish/velvet", 0.16, "tapete")],
        "bola": [("pro_pop/bloop", 0.38, "bolinha")],
        "bolinha": [("pro_pop/bloop", 0.48, "bolinha quique"), ("pro_pop/double", 0.18, "quique duplo")],
        "confete": [("shimmer/m3", 0.28, "confete")],
        "risada": [("pro_pop/chirp", 0.32, "risada")],
        "risadinha": [("pro_pop/chirp", 0.32, "risadinha")],
        "hahaha": [("pro_pop/chirp", 0.28, "risada escrita")],
        "grunhidinho": [("pro_impact/rumble", 0.24, "grunhido")],
        "bufando": [("swish/soft", 0.20, "bufo")],
        "farejando": [("pro_tap/soft", 0.16, "farejar")],
        "focinho": [("pro_tap/soft", 0.18, "focinho")],
        "rabinho": [("swish/flick", 0.22, "rabinho")],
        "orelhas": [("swish/soft", 0.14, "orelhas")],
        "escorrega": [("swish/flick", 0.28, "escorregao")],
        "pulinho": [("pro_pop/boop", 0.28, "pulinho")],
        "corre": [("pro_typing_run/soft", 0.16, "corrida")],
        "caminham": [("pro_tap/soft", 0.14, "caminhada")],
        "deita": [("pro_impact/rumble", 0.20, "deitar")],
        "cai": [("pro_impact/rumble", 0.30, "queda")],
        "puxa": [("swish/cane", 0.26, "puxao")],
        "estica": [("swish/zing", 0.20, "esticar")],
        "solta": [("pro_pop/boop", 0.22, "soltar")],
        "esconde": [("swish/velvet", 0.20, "esconder")],
        "procura": [("pro_hover_tick/soft", 0.16, "procurar")],
        "encontra": [("pro_pop/tink", 0.26, "encontrar")],
        "acorda": [("pro_notify/ding_1930", 0.22, "acordar")],
        "sono": [("shimmer/m1", 0.18, "sono")],
        "soninho": [("shimmer/m1", 0.18, "soninho")],
        "bocejo": [("swish/soft", 0.30, "bocejo")],
        "espirro": [("pro_impact/air", 0.70, "espirro")],
        "ronrona": [("pro_impact/rumble", 0.20, "ronronar")],
        "roncando": [("pro_impact/rumble", 0.42, "barriga roncando")],
        "latido": [("pro_pop/bloop", 0.34, "latidinho")],
        "latidinho": [("pro_pop/bloop", 0.32, "latidinho")],
        "au": [("pro_pop/bloop", 0.26, "au")],
        "estrelinhas": [("shimmer/m5", 0.28, "estrelinhas")],
        "folhinhas": [("swish/flick", 0.18, "folhinhas")],
        "abelhinhas": [("hover_tick/air", 0.22, "abelhinhas")],
        "poirinha": [("shimmer/m4", 0.50, "poeirinha estrelinhas")],
        "poeirinha": [("shimmer/m0", 0.42, "poeirinha magica")],
        "passarinhos": [("whoosh_fast/whistle", 0.32, "passarinhos")],
        "passarinho": [("pro_pop/chirp", 0.30, "passarinho")],
        "borboleta": [("hover_tick/air", 0.32, "asinhas borboleta"), ("pro_shimmer/m2", 0.24, "sparkle")],
        "borboletas": [("hover_tick/air", 0.26, "asinhas borboletas")],
        "estrelas": [("shimmer/m5", 0.42, "estrelas brilhantes")],
        "ossinhos": [("whoosh_fast/whistle", 0.40, "ossinhos voadores")],
        "biscoito": [("typing_key/crisp", 0.38, "biscoito crocante")],
        "biscoitos": [("typing_key/light", 0.34, "biscoitos")],
        "cantando": [("mallet/glock", 0.34, "xilofone cantoria")],
        "abraço": [("mallet/pluck", 0.34, "carinho abraco")],
        "abranos": [("mallet/pluck", 0.34, "carinho")],
        "vento": [("swish/soft", 0.26, "vento")],
        "água": [("drip/bubble", 0.32, "agua")],
        "fonte": [("drip/drop", 0.32, "agua fonte")],
        "gargalhada": [("whoosh_fast/whistle", 0.30, "gargalhada")],
        "like": [("pro_pop/tink", 0.32, "like")],
        "obrigado": [("mallet/glock", 0.22, "agradecimento")],
        "inscreva": [("fit/bell/small_bell", 0.60, "campainha subscribe")],
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
        # BUG CORRIGIDO (2026-11-19): norm() tira acento das palavras
        # transcritas, mas a chave era usada crua -> 'água', 'abraço' etc
        # nunca casavam. Normalizar a chave tambem.
        chave_n = norm(chave)
        encontradas = []
        for i,(pal,s,e) in enumerate(palavras):
            if chave_n in pal or (len(chave_n)>6 and chave_n[:6] in pal):
                encontradas.append((pal,s,e,i))
        # REGRA DO USUARIO: MUITOS mais sons. Antes era [:4] (no maximo 4
        # por chave) e dedup de 0.3s -> so 14 cues. Agora ate 20 por chave
        # e dedup de 0.06s (evita perder eventos proximos sem sobrepor).
        for pal,s,e,i in encontradas[:20]:
            if any(abs(s-x[0])<0.06 for x in usadas):
                continue
            usadas.add((s,e))
            for sid,gain,motivo in sons:
                cues.append((s+8.0, sid, gain, f"'{pal}' -> {motivo}"))

    # ambiente: passarinhos esparsos + BED CONTINUO (o usuario reclamou que
    # a sonoplastia estava pobre). O bed entra bem baixo para nao mascarar a voz.
    for t in [30.9, 118.4, 131.5, 219.0, 360.2, 460.0, 560.0]:
        cues.append((t, "pro_pop/chirp", 0.22, "passarinho ambiente"))
    dur_fala = palavras[-1][2] if palavras else 600.0
    for k in range(int(dur_fala // 3.0) + 1):
        cues.append((k*3.0 + 1.2 + 8.0, "pro_pop/chirp", 0.07, "bed continuo passarinhos"))
        cues.append((k*3.0 + 2.6 + 8.0, "swish/soft", 0.05, "bed continuo brisa"))

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
    ap=argparse.ArgumentParser()
    ap.add_argument("--lang",required=True,choices=["pt","es","en"])
    ap.add_argument("--slug",default="",help="slug do projeto (ou VIDEOMAKER_PROJ)")
    args=ap.parse_args()
    if args.slug:
        P = Path(r"C:\videomaker\projects") / args.slug
        AUD = P / "assets/audio"
    main(args.lang)
