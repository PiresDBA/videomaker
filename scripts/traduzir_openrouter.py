# -*- coding: utf-8 -*-
"""traduzir_openrouter.py - Traduz script.json -> script_<lang>.json via
OpenRouter API (confiavel, substitui o Gemini WEB que travou).

Traduz title, label, text e delivery_cues.emphasis_words mantendo o formato.
"""
from __future__ import annotations
import os, json, sys, urllib.request, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
SRC = P / "artifacts/script.json"
API = "https://openrouter.ai/api/v1/chat/completions"
KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = "openai/gpt-4o-mini"  # rapido e barato

NOMES = {"es": "espanhol", "en": "inglês"}


def chamar(messages, max_tokens=4000):
    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(API, data=payload, headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://videomaker.local",
        "X-Title": "FridaLuna Translator",
    })
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                out = json.load(r)
            return out["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  tentativa {tentativa+1} falhou: {e}", flush=True)
            time.sleep(3)
    raise RuntimeError("OpenRouter falhou apos 3 tentativas")


def traduzir(lang):
    print(f"=== traduzindo para {NOMES[lang]} ===", flush=True)
    src = json.load(open(SRC, encoding="utf-8"))
    out = dict(src)
    out["title"] = chamar([
        {"role": "system", "content": f"Traduza o titulo para {NOMES[lang]}. Responda SÓ com a tradução, sem aspas nem explicação."},
        {"role": "user", "content": src["title"]},
    ], 100).strip().strip('"')
    print(f"  titulo: {out['title']}", flush=True)

    novas = []
    for i, sec in enumerate(src["sections"]):
        prompt = f"""Traduza para {NOMES[lang]} Maintain EXATAMENTE o mesmo formato JSON.
Regras:
- Mantenha os campos id e label como estao? NAO: traduza o label.
- Converta o texto para {NOMES[lang]} mantendo o tom alegre, infantil e a MESMA extensão aproximada.
- delivery_cues: mantenha pace/energy/pause_after_seconds iguais; traduza emphasis_words.
- Responda SÓ com o JSON da seção, sem markdown.

Seção original:
{json.dumps(sec, ensure_ascii=False)}"""
        resp = chamar([
            {"role": "system", "content": "Você é um tradutor de roteiros infantis. Responda SÓ com JSON válido."},
            {"role": "user", "content": prompt},
        ], 1200)
        resp = resp.strip()
        # limpa markdown
        if resp.startswith("```"):
            resp = resp.split("```")[1]
            if resp.startswith("json"): resp = resp[4:]
        try:
            trad = json.loads(resp)
        except Exception:
            print(f"  AVISO secao {i}: JSON invalido, usando texto original", flush=True)
            trad = dict(sec)
            trad["text"] = chamar([
                {"role": "system", "content": f"Traduza para {NOMES[lang]}. Responda SÓ com a tradução."},
                {"role": "user", "content": sec["text"]},
            ], 800).strip()
        trad["id"] = sec["id"]  # ID nunca muda
        novas.append(trad)
        print(f"  [{i+1}/{len(src['sections'])}] {sec['id']}: {trad.get('text','')[:60]}", flush=True)

    out["sections"] = novas
    if src.get("style_notes"):
        out["style_notes"] = chamar([
            {"role": "system", "content": f"Traduza para {NOMES[lang]}. Responda SÓ com a tradução."},
            {"role": "user", "content": src["style_notes"]},
        ], 200).strip()

    destino = P / f"artifacts/script_{lang}.json"
    json.dump(out, open(destino, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"OK: {destino}", flush=True)


if __name__ == "__main__":
    if not KEY:
        print("ERRO: OPENROUTER_API_KEY nao encontrada")
        sys.exit(1)
    for lang in ["es", "en"]:
        traduzir(lang)
