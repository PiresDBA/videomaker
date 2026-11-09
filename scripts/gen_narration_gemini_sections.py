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
import json
import os
import subprocess
import sys
import time
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


def build_model_chain(primary, fallbacks):
    chain = []
    for m in [primary] + list(fallbacks or []):
        if m and m not in chain:
            chain.append(m)
    return chain


def is_daily_quota(msg):
    """429 por cota DIARIA (RESOURCE_EXHAUSTED 'per day') nao adianta repetir; troca de modelo."""
    low = (msg or "").lower()
    return "per day" in low or "perday" in low or "daily" in low


def synthesize(key, model, voice, text, timeout=300):
    url = "%s/models/%s:generateContent?key=%s" % (API, model, key)
    body = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {
                                     "prebuiltVoiceConfig": {"voiceName": voice}}}}}
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proj", default=None, help="diretorio do projeto")
    ap.add_argument("--voice", default=None, help="voz Gemini (ex: Leda, Achernar)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--only", default=None, help="ids separados por virgula")
    ap.add_argument("--force", action="store_true", help="regenera mesmo se o wav existe")
    ap.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    tts = cfg.get("tts", {})
    proj = (Path(args.proj) if args.proj else (HERE / cfg.get("project_dir", ".."))).resolve()
    ffprobe = str(Path(cfg["ffmpeg_dir"]) / "ffprobe.exe")

    key_env = tts.get("key_env", "GOOGLE_TTS_API_KEY")
    key = load_env_key(key_env) or load_env_key("GOOGLE_API_KEY")
    if not key:
        raise SystemExit("chave nao encontrada: defina %s no .env" % key_env)

    model = args.model or tts.get("model", "gemini-3.8-flash-tts")
    voice = args.voice or tts.get("voice", "Leda")
    fallbacks = tts.get("model_fallbacks", DEFAULT_FALLBACK_MODELS)
    chain = build_model_chain(model, fallbacks)

    script = load_json(proj / "artifacts" / "script.json")
    script, mudancas = apply_contract(script, theme=script.get("title") or "")
    if mudancas:
        print("== CONTRATO narracao: " + "; ".join(mudancas))
        with open(proj / "artifacts" / "script.json", "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
    problemas = validate_contract(script)
    if problemas:
        print("== AVISO contrato de narracao:", "; ".join(problemas))

    out = proj / "assets" / "audio" / "narration"
    out.mkdir(parents=True, exist_ok=True)
    only = {x.strip() for x in args.only.split(",")} if args.only else None

    timing_path = proj / "artifacts" / "narration_timing.json"
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

        texto = limpar_e_preparar_texto(s.get("text", "").strip())
        if not texto:
            continue

        dst = out / ("%s.wav" % sid)
        # Reaproveita apenas se o arquivo existir E tiver sido gerado com a
        # mesma voz. Se a voz mudou, regenera (senao a alternancia nao vale).
        mesma_voz = anterior.get(sid, {}).get("voice") == voice
        if dst.exists() and dst.stat().st_size > 1000 and mesma_voz and not args.force:
            dur = probe_duration(ffprobe, dst)
            print("%-6s %7.2fs  (ja existe, voz %s)" % (sid, dur, voice))
            results.append({"id": sid, "path": str(dst), "duration": dur,
                            "voice": voice, "model": model})
            continue

        ok = False
        for mi, mdl in enumerate(chain):
            has_next = mi < len(chain) - 1
            for attempt in range(args.retries):
                try:
                    raw, finish = synthesize(key, mdl, voice, texto)
                    dst.write_bytes(raw)
                    dur = probe_duration(ffprobe, dst)
                    if dur <= 0.05:
                        # Alguns modelos (ex: *-preview) devolvem PCM cru, sem
                        # cabecalho RIFF; gravar como .wav gera duracao 0 e
                        # quebra a timeline. Descarta e tenta o proximo modelo.
                        try:
                            dst.unlink()
                        except OSError:
                            pass
                        print("%s: audio invalido (duracao %.2fs) em %s; tentando proximo"
                              % (sid, dur, mdl))
                        break
                    print("%-6s %7.2fs  OK (%s) voz=%s modelo=%s"
                          % (sid, dur, finish, voice, mdl))
                    results.append({"id": sid, "path": str(dst), "duration": dur,
                                    "voice": voice, "model": mdl})
                    ok = True
                    break
                except urllib.error.HTTPError as e:
                    msg = e.read().decode("utf-8", "ignore")
                    print("%s: HTTP %s %s (modelo=%s, tentativa %d/%d)"
                          % (sid, e.code, msg[:120].replace("\n", " "),
                             mdl, attempt + 1, args.retries))
                    if is_daily_quota(msg) and has_next:
                        print("%s: cota diaria esgotada em %s; trocando de modelo"
                              % (sid, mdl))
                        break
                    if e.code in (400, 401, 403, 404):
                        break
                    time.sleep(4 * (attempt + 1))
                except Exception as e:
                    print("%s: erro %s (modelo=%s, tentativa %d/%d)"
                          % (sid, str(e)[:100], mdl, attempt + 1, args.retries))
                    time.sleep(4 * (attempt + 1))
            if ok:
                break

        if not ok:
            falhas += 1
            print("%s: FALHA ao gerar com Gemini TTS (modelos: %s)"
                  % (sid, ", ".join(chain)))
        time.sleep(1.5)

    ordem = [s["id"] for s in script["sections"]]
    results.sort(key=lambda r: ordem.index(r["id"]))
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    total = sum(r["duration"] for r in results)
    print("TOTAL %.1fs  (voz %s, modelos %s)" % (total, voice, ", ".join(chain)))

    if falhas:
        print("== Gemini TTS: %d secao(oes) falharam. O pipeline deve usar o fallback Edge-TTS." % falhas)
        return 3
    if not results:
        print("== Gemini TTS: nenhuma secao gerada. O pipeline deve usar o fallback Edge-TTS.")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
