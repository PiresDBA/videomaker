# -*- coding: utf-8 -*-
"""
Gera a narracao com Gemini TTS (Google AI Studio) secao por secao.

Diferente do fluxo antigo (chunks + align_narration), este script sintetiza
uma secao por vez, gravando assets/audio/narration/<id>.wav e o
artifacts/narration_timing.json com a duracao real de cada secao. Assim ele
funciona exatamente como o gen_narration_edge.py, mas usando as vozes do
Google AI Studio (Achernar, Leda, Kore, Zephyr, etc.).

A chave vem da variavel de ambiente em config.tts.key_env (padrao
GOOGLE_TTS_API_KEY no .env da raiz do Videomaker).

Uso:
  python scripts/gen_narration_gemini_sections.py --proj <dir>
  python scripts/gen_narration_gemini_sections.py --proj <dir> --voice Leda
  python scripts/gen_narration_gemini_sections.py --proj <dir> --only s0,s1 --force
"""
import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

from narration_contract import apply_contract, validate_contract
from gen_narration_edge import limpar_e_preparar_texto, load_json
from env_keys import load_env_key

HERE = Path(__file__).resolve().parent
API = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_RETRIES = 5
# O free tier do Gemini TTS tem cota DIARIA por modelo (ex: 10 req/dia no
# gemini-3.8-flash-tts). Um video com 12 secoes estoura essa cota; por isso a
# geracao alterna para o proximo modelo quando o atual esgota a cota do dia.
DEFAULT_FALLBACK_MODELS = ["gemini-3.8-flash-lite-tts"]

# Substituicoes de pronunciacao por idioma (evitar TTS ler nomes de forma errada).
# Em ingles, "Luninha" (apelido da Luna) deve soar como "little Luna".
PRONUNCIATION_MAP = {
    "pt": [
        (r"\bgatinha\b", "cachorrinha"),
        (r"\bgatinho\b", "cachorro"),
        (r"\bgatos\b", "cachorros"),
        (r"\bgata\b", "cadela"),
        (r"\bgato\b", "cachorro"),
    ],
    "en": [
        (r"\bLuninha\b", "little Luna"),
        (r"\bluninha\b", "little Luna"),
        (r"\bgatinha\b", "puppy"),
        (r"\bgatinho\b", "puppy"),
    ],
    "es": [
        (r"\bLuninha\b", "pequeña Luna"),
        (r"\bluninha\b", "pequeña Luna"),
    ],
}


def build_model_chain(primary, fallbacks):
    chain = []
    for m in [primary] + list(fallbacks or []):
        if m and m not in chain:
            chain.append(m)
    return chain


def collect_keys(key_env):
    """Reunir candidatas de chave de API: GOOGLE_TTS_API_KEY e GOOGLE_TTS_API_KEY_1..N.

    Le do ambiente e do .env (UTF-8 ou UTF-16) via load_env_key. Nao expoe valores no log.
    """
    keys = []
    seen = set()

    def add(key):
        if not key or key in seen:
            return
        seen.add(key)
        keys.append(key)

    # Chave unica nomeada no config (padrao GOOGLE_TTS_API_KEY)
    add(os.environ.get(key_env, ""))
    if load_env_key:
        try:
            add(load_env_key(key_env) or "")
        except Exception:
            pass

    # Variaveis numeradas para rotacao: _1, _2, _3 ...
    i = 1
    while True:
        val = os.environ.get("%s_%d" % (key_env, i), "")
        if not val and load_env_key:
            try:
                val = load_env_key("%s_%d" % (key_env, i)) or ""
            except Exception:
                val = ""
        if not val:
            break
        add(val)
        i += 1

    # Fallback legado: GOOGLE_API_KEY
    add(os.environ.get("GOOGLE_API_KEY", ""))
    if load_env_key:
        try:
            add(load_env_key("GOOGLE_API_KEY") or "")
        except Exception:
            pass

    return keys


def is_daily_quota(msg):
    """429 por cota DIARIA (RESOURCE_EXHAUSTED 'per day') nao adianta repetir; troca de chave/modelo."""
    low = (msg or "").lower()
    return "per day" in low or "perday" in low or "daily" in low


def synthesize(key, model, voice, text, style=None, timeout=300):
    url = "%s/models/%s:generateContent?key=%s" % (API, model, key)
    # Nota: o campo "instructions" em speechConfig nao e suportado pelo
    # modelo gemini-3.8-flash-tts (causa HTTP 400). Mantemos o parametro
    # style aceito na assinatura para nao quebrar a CLI, mas nao o enviamos.
    speech = {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}
    body = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": speech}}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req, timeout=timeout))
    cand = data["candidates"][0]
    part = cand["content"]["parts"][0]
    inline = part.get("inlineData") or part.get("inline_data")
    if not inline or "data" not in inline:
        raise RuntimeError("resposta sem audio (finish=%s)" % cand.get("finishReason"))
    return base64.b64decode(inline["data"]), cand.get("finishReason")


def probe_duration(ffprobe, path):
    out = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                         capture_output=True, text=True).stdout.strip()
    try:
        return round(float(out), 3)
    except Exception:
        return 0.0


def _text_hash(text):
    return hashlib.md5((text or "").encode("utf-8")).hexdigest()[:12]


_ASR = None


def _norm_word(word):
    w = unicodedata.normalize("NFKD", (word or "").lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", w)


def _get_asr(model_name):
    global _ASR
    if _ASR is None:
        from faster_whisper import WhisperModel
        _ASR = WhisperModel(model_name, device="cpu", compute_type="int8")
    return _ASR


def transcribe_words(path, ffmpeg, model_name):
    import numpy as np
    raw = subprocess.run([ffmpeg, "-v", "error", "-i", str(path),
                          "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True).stdout
    audio = np.frombuffer(raw, dtype=np.float32)
    model = _get_asr(model_name)
    segs, _ = model.transcribe(audio, language="pt", vad_filter=True,
                               word_timestamps=True)
    return [w.word for s in segs for w in (s.words or [])]


def find_duplicated_speech(path, expected_text, ffmpeg, model_name, n=4):
    """Detecta fala repetida no audio que NAO existe no texto do roteiro.

    O Gemini TTS as vezes repete o paragrafo inteiro (ou o comeco de uma frase)
    no proprio audio. Comparar a contagem de n-gramas ouvidos com a do texto
    esperado pega esse caso sem marcar repeticoes naturais do roteiro.
    """
    try:
        import numpy  # noqa: F401
        from faster_whisper import WhisperModel  # noqa: F401
    except Exception:
        return []
    try:
        heard = transcribe_words(path, ffmpeg, model_name)
    except Exception as e:
        print("  [dup-check] indisponivel (%s); seguindo sem verificar" % str(e)[:80])
        return []
    exp = [w for w in (_norm_word(x) for x in expected_text.split()) if w]
    h = [w for w in (_norm_word(x) for x in heard) if w]
    if not exp or not h:
        return []
    from collections import Counter
    exp_counts = Counter(tuple(exp[i:i + n]) for i in range(max(0, len(exp) - n + 1)))
    h_counts = Counter(tuple(h[i:i + n]) for i in range(max(0, len(h) - n + 1)))
    dups = []
    seen = set()
    for gram, count in h_counts.items():
        base = exp_counts.get(gram, 0)
        if (base >= 1 and count > base) or (base == 0 and count >= 2):
            chave = " ".join(gram)
            if chave not in seen:
                seen.add(chave)
                dups.append(chave)
    return dups


def generate_to_path(keys, chain, retries, voice, style, texto, dst, ffprobe,
                     ffmpeg, verify, asr_model, sid="?"):
    """Sintetiza texto em dst tentando chaves x modelos.

    Se verify, transcreve o WAV e regenera quando detectar fala duplicada.
    Retorna (ok, modelo_usado, chave_usada).
    """
    for ki, key in enumerate(keys):
        pular_chave = False
        for mdl in chain:
            if pular_chave:
                break
            for attempt in range(retries):
                try:
                    raw, finish = synthesize(key, mdl, voice, texto, style=style)
                    dst.write_bytes(raw)
                    dur = probe_duration(ffprobe, dst)
                    if dur <= 0.05:
                        # Alguns modelos devolvem PCM cru sem cabecalho RIFF.
                        try:
                            dst.unlink()
                        except OSError:
                            pass
                        print("%s: audio invalido (duracao %.2fs) em %s com chave %d/%d; tentando proximo"
                              % (sid, dur, mdl, ki + 1, len(keys)))
                        pular_chave = True
                        break
                    if verify:
                        dups = find_duplicated_speech(dst, texto, ffmpeg, asr_model)
                        if dups:
                            print("%s: narracao DUPLICADA em %s (chave %d/%d, tentativa %d/%d): "
                                  "%s; regenerando"
                                  % (sid, mdl, ki + 1, len(keys), attempt + 1, retries,
                                     "; ".join(dups[:3])))
                            time.sleep(1.5)
                            continue
                    print("%-6s %7.2fs  OK (%s) voz=%s modelo=%s chave=%d/%d"
                          % (sid, dur, finish, voice, mdl, ki + 1, len(keys)))
                    return True, mdl, ki + 1
                except urllib.error.HTTPError as e:
                    msg = e.read().decode("utf-8", "ignore")
                    print("%s: HTTP %s %s (modelo=%s, chave=%d/%d, tentativa %d/%d)"
                          % (sid, e.code, msg[:120].replace("\n", " "),
                             mdl, ki + 1, len(keys), attempt + 1, retries))
                    if is_daily_quota(msg):
                        print("%s: cota diaria esgotada na chave %d/%d (%s); pulando para proxima chave"
                              % (sid, ki + 1, len(keys), mdl))
                        pular_chave = True
                        break
                    if e.code in (400, 401, 403, 404):
                        pular_chave = True
                        break
                    time.sleep(4 * (attempt + 1))
                except Exception as e:
                    print("%s: erro %s (modelo=%s, chave=%d/%d, tentativa %d/%d)"
                          % (sid, str(e)[:100], mdl, ki + 1, len(keys), attempt + 1, retries))
                    time.sleep(4 * (attempt + 1))
    return False, None, None


def synthesize_in_sentences(keys, chain, retries, voice, style, texto, dst,
                            ffprobe, ffmpeg, asr_model, sid):
    """Ultimo recurso: sintetiza frase a frase e concatena.

    Paragrafos longos sao o gatilho mais comum de repeticao do Gemini TTS;
    separar em frases curtas evita a duplicacao do bloco inteiro.
    """
    frases = [p.strip() for p in re.split(r"(?<=[.!?])\s+", texto.strip()) if p.strip()]
    if len(frases) < 2:
        return False
    tmp_dir = Path(tempfile.mkdtemp(prefix="tts_%s_" % sid))
    try:
        partes = []
        for i, frase in enumerate(frases):
            p = tmp_dir / ("part%02d.wav" % i)
            ok, _, _ = generate_to_path(keys, chain, retries, voice, style, frase,
                                        p, ffprobe, ffmpeg, verify=False,
                                        asr_model=asr_model, sid="%s.%d" % (sid, i + 1))
            if not ok:
                return False
            partes.append(p)
        listfile = tmp_dir / "concat.txt"
        listfile.write_text("\n".join("file '%s'" % p.as_posix() for p in partes),
                            encoding="utf-8")
        r = subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0",
                            "-i", str(listfile), "-c", "copy", str(dst)],
                           capture_output=True, text=True)
        if r.returncode != 0 or probe_duration(ffprobe, dst) <= 0.05:
            return False
        dups = find_duplicated_speech(dst, texto, ffmpeg, asr_model)
        if dups:
            print("%s: ainda com duplicacao apos sintese frase a frase: %s"
                  % (sid, "; ".join(dups[:3])))
            return False
        print("%s: narracao gerada frase a frase (sem duplicacao)" % sid)
        return True
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", default=None, help="diretorio do projeto")
    ap.add_argument("--lang", default="pt", help="idioma da narracao (pt, en, es). padrao: pt")
    ap.add_argument("--voice", default=None, help="voz Gemini (ex: Leda, Achernar)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--only", default=None, help="ids separados por virgula")
    ap.add_argument("--force", action="store_true", help="regenera mesmo se o wav existe")
    ap.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    ap.add_argument("--style", default=None,
                    help="instrucao de estilo para a voz Gemini (ex: 'divertida e alegre para criancas')")
    ap.add_argument("--no-verify", action="store_true",
                    help="nao verifica/refaz narracao duplicada (mais rapido)")
    ap.add_argument("--asr-model", default="small",
                    help="modelo faster-whisper usado na checagem de duplicacao")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    tts = cfg.get("tts", {})
    proj = (Path(args.proj) if args.proj else (HERE / cfg.get("project_dir", ".."))).resolve()
    artifacts = proj / "artifacts"
    ffprobe = str(Path(cfg["ffmpeg_dir"]) / "ffprobe.exe")
    ffmpeg = str(Path(cfg["ffmpeg_dir"]) / "ffmpeg.exe")

    key_env = tts.get("key_env", "GOOGLE_TTS_API_KEY")
    keys = collect_keys(key_env)
    if not keys:
        raise SystemExit("chave nao encontrada: defina %s (ou %s_1, _2, _3) no .env" % (key_env, key_env))

    model = args.model or tts.get("model", "gemini-3.8-flash-tts")
    lang = (args.lang or "pt").lower().strip()

    # Voz por idioma (sobrescrita por --voice se informada).
    if args.voice:
        voice = args.voice
    elif lang == "en":
        voice = tts.get("voice_en", "Achernar")
    elif lang == "es":
        voice = tts.get("voice_es", "Leda")
    else:
        voice = tts.get("voice", "Leda")
    style = args.style or tts.get("narration_style", None)
    fallbacks = tts.get("model_fallbacks", DEFAULT_FALLBACK_MODELS)
    chain = build_model_chain(model, fallbacks)

    # Escolhe o arquivo de script pelo idioma (script_<lang>.json, cai para script.json).
    script_path = artifacts / ("script_%s.json" % lang) if lang != "pt" else artifacts / "script.json"
    if not script_path.exists():
        script_path = artifacts / "script.json"
    script = load_json(script_path)
    script, mudancas = apply_contract(script, theme=script.get("title") or "")
    if mudancas:
        print("== CONTRATO narracao: " + "; ".join(mudancas))
        with open(script_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
    problemas = validate_contract(script)
    if problemas:
        print("== AVISO contrato de narracao:", "; ".join(problemas))

    # Substituicoes de pronunciacao por idioma (ex: Luninha -> little Luna em ingles).
    texto_map = PRONUNCIATION_MAP.get(lang, [])

    def limpar_com_pronuncia(text: str) -> str:
        t = limpar_e_preparar_texto(text)
        for pat, repl in texto_map:
            t = re.sub(pat, repl, t, flags=re.I)
        return " ".join(t.split())

    out = proj / "assets" / "audio" / "narration" / lang
    out.mkdir(parents=True, exist_ok=True)
    only = {x.strip() for x in args.only.split(",")} if args.only else None

    timing_path = artifacts / ("narration_timing_%s.json" % lang) if lang != "pt" else artifacts / "narration_timing.json"
    anterior = {}
    if timing_path.exists():
        for item in load_json(timing_path):
            anterior[item["id"]] = item

    results = []
    falhas = 0
    for s in script["sections"]:
        sid = s["id"]
        if only and sid not in only:
            if sid in anterior:
                results.append(anterior[sid])
            continue

        texto = limpar_com_pronuncia(s.get("text", "").strip())
        if not texto:
            continue

        dst = out / ("%s.wav" % sid)
        anterior_sid = anterior.get(sid, {})
        mesma_voz = anterior_sid.get("voice") == voice
        hash_atual = _text_hash(texto)
        mesmo_texto = anterior_sid.get("text_hash") in (None, hash_atual)
        if dst.exists() and dst.stat().st_size > 1000 and mesma_voz and mesmo_texto and not args.force:
            dur = probe_duration(ffprobe, dst)
            print("%-6s %7.2fs  (ja existe, voz %s)" % (sid, dur, voice))
            results.append({"id": sid, "path": str(dst), "duration": dur,
                            "voice": voice, "model": model,
                            "key": anterior_sid.get("key"), "text_hash": hash_atual})
            continue

        verify = not args.no_verify
        ok, modelo_usado, chave_usada = generate_to_path(
            keys, chain, args.retries, voice, style, texto, dst,
            ffprobe, ffmpeg, verify, args.asr_model, sid=sid)
        if not ok and verify:
            print("%s: tentando sintese frase a frase para evitar duplicacao" % sid)
            ok = synthesize_in_sentences(
                keys, chain, args.retries, voice, style, texto, dst,
                ffprobe, ffmpeg, args.asr_model, sid)
            if ok:
                modelo_usado = "sentences"
                chave_usada = None

        if ok:
            dur = probe_duration(ffprobe, dst)
            results.append({"id": sid, "path": str(dst), "duration": dur,
                            "voice": voice, "model": modelo_usado,
                            "key": chave_usada, "text_hash": hash_atual})
        else:
            falhas += 1
            print("%s: FALHA ao gerar com Gemini TTS (todas as %d chave(s) x modelos %s)"
                  % (sid, len(keys), ", ".join(chain)))
        time.sleep(1.5)

    ordem = [s["id"] for s in script["sections"]]
    results.sort(key=lambda r: ordem.index(r["id"]))
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total = sum(r["duration"] for r in results)
    chaves_usadas = sorted({r.get("key") for r in results if r.get("key")})
    print("TOTAL %.1fs  (voz %s, modelos %s, chaves %s)"
          % (total, voice, ", ".join(chain), ", ".join(str(c) for c in chaves_usadas) if chaves_usadas else "nenhuma"))

    if falhas:
        print("== Gemini TTS: %d secao(oes) falharam. O pipeline deve usar o fallback Edge-TTS." % falhas)
        return 3
    if not results:
        print("== Gemini TTS: nenhuma secao gerada. O pipeline deve usar o fallback Edge-TTS.")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
