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

# ATENCAO: existem DOIS pacotes chamados `earshot`:
#   1) C:\videomaker\earshot-sfx -> earshot.forge.bank (banco de 252 sons)
#   2) earshot 1.2.2 (pip) -> Detector.predict_i16 (VAD para ducking)
# Carregamos o bank PRIMEIRO com o path do earshot-sfx, removemos o modulo
# do cache e so entao importamos o earshot do pip para o VAD.
_EARSHOT_SFX = r"C:\videomaker\earshot-sfx"
sys.path.insert(0, _EARSHOT_SFX)
from earshot.forge import bank
# remove o path do earshot-sfx para o proximo import resolver o earshot do pip
if _EARSHOT_SFX in sys.path:
    sys.path.remove(_EARSHOT_SFX)
sys.modules.pop("earshot", None)
import earshot  # pip 1.2.2 - VAD

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


def mascara_voz_earshot(base: np.ndarray, sr: int) -> np.ndarray:
    """Detecta VOZ com earshot e devolve uma mascara suave [0..1] no tamanho
    de `base`. 1 = voz presente (efeitos devem ser atenuados), 0 = sem voz.

    O earshot exige 16 kHz/int16/frames de 256 amostras. Reamostramos o base
    (44,1 kHz) para 16 kHz, pontuamos cada frame com predict_i16 e suavizamos
    a transicao para nao gerar 'pump' audivel no ducking.
    """
    try:
        n16 = int(len(base) * 16000 / sr)
        a16 = np.interp(np.linspace(0, len(base), n16), np.arange(len(base)), base)
        a16 = np.clip(a16 * 32767.0, -32768, 32767).astype(np.int16)
        det = earshot.Detector()
        scores = np.zeros(len(a16) // 256 + 1, dtype=np.float32)
        for i in range(len(a16) // 256):
            scores[i] = det.predict_i16(a16[i * 256:(i + 1) * 256])
        # suaviza: limiar 0.5 + rampa de 0.15s para entrar/sair do ducking
        binario = (scores > 0.5).astype(np.float32)
        janela = max(1, int(0.15 / 0.016))  # 150ms em frames de 16ms
        kernel = np.ones(janela, dtype=np.float32) / janela
        suave = np.convolve(binario, kernel, mode="same")
        # expande de volta para o tamanho do base
        mascara = np.interp(np.arange(len(base)),
                            np.linspace(0, len(base), len(suave)), suave)
        return np.clip(mascara, 0.0, 1.0).astype(np.float32)
    except Exception as e:
        print(f"  AVISO earshot VAD: {e} (ducking desativado)", flush=True)
        return np.zeros(len(base), dtype=np.float32)

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
        "cozinha": [("tap/table", 0.14, "cozinha")],
        "porta": [("knock/wood", 0.26, "porta")],
        "tapete": [("swipe/velvet", 0.16, "tapete")],
        "bola": [("pro_pop/bloop", 0.38, "bolinha")],
        "bolinha": [("bola_quique", 0.38, "bolinha quique real"), ("pro_pop/bloop", 0.28, "quique"), ("pro_pop/double", 0.18, "quique duplo")],
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
        "esconde": [("swipe/velvet", 0.20, "esconder")],
        "procura": [("pro_hover_tick/soft", 0.16, "procurar")],
        "encontra": [("pro_pop/tink", 0.26, "encontrar")],
        "acorda": [("pro_notify/ding_1930", 0.22, "acordar")],
        "sono": [("shimmer/m1", 0.18, "sono")],
        "soninho": [("shimmer/m1", 0.18, "soninho")],
        "bocejo": [("swish/soft", 0.30, "bocejo")],
        "espirro": [("espirro", 0.42, "espirro real"), ("pro_impact/air", 0.30, "espirro")],
        "ronrona": [("pro_impact/rumble", 0.20, "ronronar")],
        "roncando": [("pro_impact/rumble", 0.42, "barriga roncando")],
        "latido": [("pro_pop/bloop", 0.34, "latidinho")],
        "latidinho": [("pro_pop/bloop", 0.32, "latidinho")],
        "au": [("pro_pop/bloop", 0.26, "au")],
        "estrelinhas": [("estrelinha", 0.28, "estrelinhas reais"), ("shimmer/m5", 0.18, "brilho")],
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
        # ---- "sozinhas em casa" — sons por ACAO REAL da cena ----
        "solitas": [("mallet/celesta", 0.20, "complicidade")],
        "casa": [("tap/soft", 0.10, "casa tranquila")],
        "puerta": [("knock/wood", 0.24, "puerta"), ("toggle/rocker", 0.12, "cerradura")],
        "clic": [("click/soft", 0.24, "clic de la puerta")],
        "alfombra": [("swipe/velvet", 0.14, "alfombra suave")],
        "rabito": [("swish/flick", 0.20, "rabito")],
        "patitas": [("pro_tap/soft", 0.20, "patitas")],
        "patita": [("pro_tap/finger", 0.18, "patita")],
        "ladridito": [("pro_pop/bloop", 0.30, "ladridito")],
        "ladrar": [("pro_pop/bloop", 0.26, "ladrido")],
        "paso": [("pro_typing_run/soft", 0.14, "paso pesado")],
        "resbala": [("swish/flick", 0.22, "resbalon")],
        "escorrega": [("swish/flick", 0.22, "resbalon")],
        "sofa": [("pro_impact/rumble", 0.22, "caida en el sofa"), ("pro_tap/soft", 0.16, "almohadon")],
        "salto": [("pro_pop/boop", 0.24, "saltito")],
        "cay": [("pro_impact/rumble", 0.28, "caida")],
        "barriga": [("pro_impact/rumble", 0.18, "barriguita")],
        "almohada": [("pro_tap/soft", 0.20, "almohada")],
        "risa": [("mallet/celesta", 0.20, "risa compartida")],
        "risitas": [("mallet/celesta", 0.18, "risitas")],
        "reloj": [("click/soft", 0.16, "tic tac")],
        "tique": [("click/soft", 0.20, "tic tac")],
        "libro": [("fit/land.light/fingertip_book", 0.22, "libro")],
        "estornudo": [("espirro", 0.42, "estornudo real"), ("pro_impact/air", 0.30, "estornudo")],
        "reflejo": [("pro_click/glass", 0.20, "reflejo en el cristal")],
        "espejo": [("pro_click/glass", 0.20, "espejo")],
        "pasillo": [("pro_typing_run/soft", 0.14, "pasos por el pasillo")],
        "fareja": [("pro_tap/soft", 0.14, "olfatear")],
        "media": [("swipe/cloth", 0.20, "media"), ("swish/cane", 0.14, "tirar de la media")],
        "tira": [("swish/cane", 0.20, "tiron")],
        "estira": [("swish/flick", 0.16, "estirar")],
        "suelta": [("pro_pop/boop", 0.18, "soltar")],
        "cocina": [("tap/table", 0.12, "cocina")],
        "agua": [("drip/bubble", 0.24, "agua"), ("drip/drop", 0.16, "gotitas")],
        "salpica": [("drip/drop", 0.24, "salpicadura")],
        "ventana": [("swish/soft", 0.10, "brisa en la ventana")],
        "sombra": [("swish/soft", 0.12, "sombra en el piso")],
        "dormitorio": [("tap/soft", 0.10, "habitacion")],
        "cama": [("pro_tap/soft", 0.18, "cama mullida")],
        "taburete": [("tap/finger", 0.16, "taburete")],
        "juguete": [("pro_pop/bloop", 0.22, "juguete")],
        "bote": [("pro_pop/boop", 0.24, "rebote")],
        "bostezo": [("reverse_swell/breath", 0.22, "bostezo")],
        "bolita": [("pro_pop/bloop", 0.30, "bolita")],
        "rueda": [("pro_pop/tink", 0.16, "bola que rueda")],
        "gira": [("swish/flick", 0.18, "pirueta")],
        "grunidito": [("pro_impact/rumble", 0.20, "grunidito")],
        "suspiro": [("reverse_swell/breath", 0.20, "suspiro")],
        "lamidita": [("fit/pop/mouth_plop", 0.24, "lamidita cariñosa")],
        "abrazo": [("mallet/pluck", 0.22, "carino")],
        "unida": [("mallet/pluck", 0.18, "dupla unida")],
        "like": [("pro_pop/tink", 0.22, "me gusta")],
        "solas": [("mallet/celesta", 0.18, "las dos solitas")],
        "jajaja": [("mallet/celesta", 0.18, "risa compartida")],
        "risas": [("mallet/celesta", 0.18, "risas")],
        "riendo": [("mallet/celesta", 0.18, "riendo juntas")],
        "salon": [("tap/soft", 0.10, "salon tranquilo")],
        "hocico": [("pro_tap/soft", 0.16, "hocico")],
        "nariz": [("pro_tap/soft", 0.14, "nariz")],
        "colita": [("swish/flick", 0.20, "colita")],
        "vuelta": [("swish/flick", 0.14, "vuelta")],
        "huele": [("pro_tap/soft", 0.14, "olfatear")],
        "juntas": [("mallet/pluck", 0.16, "juntas")],
        "corazon": [("mallet/pluck", 0.18, "corazon caliente")],
        "cario": [("mallet/pluck", 0.18, "cariño")],
        "acoge": [("mallet/pluck", 0.18, "acoge con cariño")],
        "rebota": [("pro_pop/boop", 0.22, "rebote")],
        "cae": [("pro_impact/rumble", 0.24, "caida")],
        "banquito": [("tap/finger", 0.16, "banquito")],
        "tic": [("click/soft", 0.18, "tic tac del reloj")],
        "suscribete": [("fit/bell/small_bell", 0.40, "campana suscribete")],
    },
    "en": {
        # ---- "home alone" — sounds matched to the REAL on-screen action ----
        "alone": [("mallet/celesta", 0.20, "together alone")],
        "home": [("tap/soft", 0.10, "quiet house")],
        "door": [("knock/wood", 0.24, "door"), ("toggle/rocker", 0.12, "latch")],
        "click": [("click/soft", 0.24, "door click")],
        "rug": [("swipe/velvet", 0.14, "soft rug")],
        "tail": [("swish/flick", 0.20, "tail wag")],
        "paws": [("pro_tap/soft", 0.20, "paws")],
        "paw": [("pro_tap/finger", 0.18, "paw pat")],
        "bark": [("pro_pop/bloop", 0.30, "little bark")],
        "barking": [("pro_pop/bloop", 0.26, "bark")],
        "step": [("pro_typing_run/soft", 0.14, "heavy step")],
        "slips": [("swish/flick", 0.22, "slip")],
        "couch": [("pro_impact/rumble", 0.22, "flop on couch"), ("pro_tap/soft", 0.16, "cushion")],
        "sofa": [("pro_impact/rumble", 0.22, "flop on sofa")],
        "jump": [("pro_pop/boop", 0.24, "little jump")],
        "fell": [("pro_impact/rumble", 0.28, "fall")],
        "belly": [("pro_impact/rumble", 0.18, "tummy")],
        "cushion": [("pro_tap/soft", 0.20, "cushion")],
        "laugh": [("mallet/celesta", 0.20, "shared laugh")],
        "giggles": [("mallet/celesta", 0.18, "giggles")],
        "clock": [("click/soft", 0.16, "tick tock")],
        "tick": [("click/soft", 0.20, "tick tock")],
        "book": [("fit/land.light/fingertip_book", 0.22, "book")],
        "sneeze": [("espirro", 0.42, "real sneeze"), ("pro_impact/air", 0.30, "sneeze")],
        "reflection": [("pro_click/glass", 0.20, "reflection in glass")],
        "mirror": [("pro_click/glass", 0.20, "mirror")],
        "hallway": [("pro_typing_run/soft", 0.14, "paws in hallway")],
        "sniff": [("pro_tap/soft", 0.14, "sniffing")],
        "sock": [("swipe/cloth", 0.20, "sock"), ("swish/cane", 0.14, "tug the sock")],
        "pulls": [("swish/cane", 0.20, "tug")],
        "stretches": [("swish/flick", 0.16, "stretch")],
        "lets": [("pro_pop/boop", 0.18, "let go")],
        "kitchen": [("tap/table", 0.12, "kitchen")],
        "water": [("drip/bubble", 0.24, "water"), ("drip/drop", 0.16, "droplets")],
        "splash": [("drip/drop", 0.24, "splash")],
        "window": [("swish/soft", 0.10, "breeze at window")],
        "shadow": [("swish/soft", 0.12, "shadow on floor")],
        "bedroom": [("tap/soft", 0.10, "bedroom")],
        "bed": [("pro_tap/soft", 0.18, "soft bed")],
        "stool": [("tap/finger", 0.16, "little stool")],
        "toy": [("pro_pop/bloop", 0.22, "toy")],
        "bounces": [("pro_pop/boop", 0.24, "bounce")],
        "yawns": [("reverse_swell/breath", 0.22, "yawn")],
        "ball": [("bola_quique", 0.38, "real ball bounce"), ("pro_pop/bloop", 0.22, "bounce")],
        "rolls": [("pro_pop/tink", 0.16, "rolling ball")],
        "spin": [("swish/flick", 0.18, "silly spin")],
        "grunt": [("pro_impact/rumble", 0.20, "little grunt")],
        "sigh": [("reverse_swell/breath", 0.20, "sigh")],
        "lick": [("fit/pop/mouth_plop", 0.24, "affectionate lick")],
        "hug": [("mallet/pluck", 0.22, "cuddle")],
        "together": [("mallet/pluck", 0.18, "best friends")],
        "like": [("pro_pop/tink", 0.22, "like")],
        "subscribe": [("fit/bell/small_bell", 0.40, "subscribe bell")],
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
    SONS_LOCAIS = {"BUZINA": "buzina_bibi.wav", "POMBA": "pomba_coo.wav",
                  "bola_quique": "bola_quique.wav", "espirro": "espirro.wav",
                  "estrelinha": "estrelinha.wav", "pomba_coo": "pomba_coo.wav",
                  "buzina_bibi": "buzina_bibi.wav"}
    if sid in SONS_LOCAIS:
        nome = SONS_LOCAIS[sid]
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


# Sons que soam como "laser"/eletronico e NAO combinam com cenas domesticas
# fofas. O usuario reclamou de muito "barulhinho de laser" (2026-11-20).
SONS_PROIBIDOS = ("zap", "glitch", "zing", "whistle", "pro_logo_sting",
                  "downlifter", "riser", "sub_drop", "glitch/chirp",
                  "osso_assobio")  # apito puro 1454Hz = "laser"


def som_permitido(sid):
    s = sid.lower()
    return not any(p in s for p in SONS_PROIBIDOS)


def ambient_bed(dur, sr, seed=7):
    """Leito ambiente CONTINUO e suave (brisa), gerado uma unica vez.

    Substitui o antigo 'bed' de 204 chirps + 204 swishes a cada 3s — que
    soava como um laser apitando sem parar. Ruido marrom filtrado + modulacao
    lenta, em ganho muito baixo: nao chama atencao, so preenche o silencio.
    """
    rng = np.random.default_rng(seed)
    n = int(dur * sr)
    if n <= 0:
        return np.zeros(1, dtype=np.float32)
    w = rng.standard_normal(n).astype(np.float32)
    b = np.cumsum(w)
    b -= b.mean()
    b /= (np.max(np.abs(b)) + 1e-9)
    k = max(1, int(0.25 * sr))  # low-pass ~0.25 s -> brisa, nao aspero
    b = np.convolve(b, np.ones(k, dtype=np.float32) / k, mode="same")
    t = np.arange(n, dtype=np.float32) / sr
    env = 0.55 + 0.45 * np.sin(2 * np.pi * 0.045 * t)
    return (b * env).astype(np.float32)


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
            if any(abs(s-x[0])<0.10 for x in usadas):
                continue
            usadas.add((s,e))
            for sid,gain,motivo in sons:
                if not som_permitido(sid):
                    continue  # nunca usar som de laser/eletronico em cena fofa
                cues.append((s+8.0, sid, gain, f"'{pal}' -> {motivo}"))

    # AMBIENTE (CORRIGIDO 2026-11-20): antes havia 204 chirps + 204 swishes
    # repetidos a cada 3s — soava como laser apitando sem parar. Agora:
    #   - leito continuo de brisa (ruido filtrado, ganho 0.03) cobre o video
    #   - passarinhos esparsos e VARIADOS (12 eventos em ~10 min, nao 204)
    dur_fala = palavras[-1][2] if palavras else 600.0
    dur_total = max(dur_fala + 8.0 + 12.0, 630.0)
    passaros = ["pro_pop/chirp", "pro_pop/tink", "hover_tick/air", "notify/m1"]
    for i in range(12):
        t = 14.0 + i * (dur_total - 30.0) / 12 + (i % 3) * 1.7
        cues.append((t, passaros[i % len(passaros)], 0.16, "passarinho esparso"))

    cues.sort()
    print(f"cues gerados: {len(cues)}", flush=True)

    # RASTREABILIDADE: salva a lista de cues para auditoria de sonoplastia.
    # Permite cruzar efeitos com segmentos de voz (earshot) e achar buracos.
    try:
        cues_json = (P / "artifacts" / f"cues_sonoplastia_{lang}.json")
        cues_json.parent.mkdir(parents=True, exist_ok=True)
        cues_json.write_text(json.dumps(
            [{"t": round(t, 3), "id": sid, "gain": round(g, 3), "motivo": mot}
             for t, sid, g, mot in cues], ensure_ascii=False, indent=2),
            encoding="utf-8")
        print(f"cues salvos: {cues_json}", flush=True)
    except Exception as e:
        print(f"AVISO: nao salvou JSON de cues: {e}", flush=True)

    # mix base
    subprocess.run([FF,"-y","-v","error","-i",str(AUD/f"final_mix.m4a"),
                    "-ar",str(SR),"-ac","1","-c:a","pcm_s16le",str(AUD/"_base_tmp.wav")],check=True)
    base,_=sf.read(AUD/"_base_tmp.wav",dtype="float32")
    # Efeitos sao acumulados SEPARADAMENTE para aplicar ducking com earshot.
    efeitos=np.zeros(len(base),dtype=np.float32); cache={}
    for t,sid,gain,motivo in cues:
        i0=int(t*SR)
        if i0>=len(efeitos): continue
        try: y=render_cue(sid,cache)
        except Exception as e:
            print(f"  ERRO {sid}: {e}"); continue
        n=min(len(y),len(efeitos)-i0)
        efeitos[i0:i0+n]+=y[:n]*gain
    # LEITO AMBIENTE: brisa continua e suave, cobre todo o video (inclusive
    # os antigos buracos 0-9s e 620-629s) sem nenhum "apito" repetitivo.
    bed = ambient_bed(len(base) / SR, SR)
    if len(bed) < len(base):
        bed = np.pad(bed, (0, len(base) - len(bed)))
    else:
        bed = bed[:len(base)]
    efeitos += bed * 0.03
    # DUCKING com earshot: a voz tem prioridade, mas os efeitos continuam
    # audiveis (55% do ganho) e ACIMA da musica de fundo. Fora da fala, 100%.
    mascara = mascara_voz_earshot(base, SR)
    reducao = (1.0 - 0.45 * mascara).astype(np.float32)
    efeitos *= reducao
    out = base + efeitos
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
