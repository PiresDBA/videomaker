# -*- coding: utf-8 -*-
"""traduzir_gemini_secoes.py - Traduz script.json seção por seção usando
gemini_fetch.py direto (o translate_script.py trava em chamadas sequenciais).

Cada seção e uma chamada curta ao Gemini WEB; le a resposta do .md, extrai
a traducao (primeira linha util) e monta script_<lang>.json no formato esperto.
"""
from __future__ import annotations
import json, sys, subprocess, re, time
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(r"C:\videomaker\scripts")
P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
SRC = P / "artifacts/script.json"
GEM = P / "artifacts/gemini"
PY = sys.executable

DIOMA = {"es": "espanhol", "en": "inglês"}


def gemini_text(prompt, nome, wait=75):
    """Chama gemini_fetch --kind text e retorna o texto do .md."""
    outmd = GEM / f"{nome}.md"
    if outmd.exists():
        outmd.unlink()
    cmd = [PY, str(HERE / "gemini_fetch.py"), "--kind", "text",
           "--prompt", prompt, "--name", nome, "--wait", str(wait)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=150)
    except subprocess.TimeoutExpired:
        return ""
    if not outmd.exists():
        return ""
    txt = outmd.read_text(encoding="utf-8", errors="replace").strip()
    return txt


def limpar_traducao(txt):
    """Extrai a frase traduzida: remove cabeçalhos, notas, markdown."""
    linhas = [l.strip() for l in txt.splitlines() if l.strip()]
    # descarta linhas de rotulo
    descartar = ("traducci", "traduc", "registro", "variaci", "suger", "nota",
                 "tradução", "versão", "opção", "alternativ", "formal", "informal")
    for l in linhas:
        low = l.lower()
        if any(d in low for d in descartar):
            continue
        l = re.sub(r"^[\*\-#>\d\.\)]+\s*", "", l).strip('"').strip("«»").strip()
        if len(l) > 12:
            return l
    return linhas[0] if linhas else txt[:120]


def traduzir(lang):
    print(f"=== {lang.upper()} ===", flush=True)
    src = json.load(open(SRC, encoding="utf-8"))
    nome_idioma = DIOMA[lang]

    # titulo
    t = limpar_traducao(gemini_text(
        f"Traduza este título para {nome_idioma}. Responda apenas com o título traduzido, sem explicações: {src['title']}",
        f"titulo_{lang}"))
    print(f"  titulo: {t}", flush=True)

    secoes = []
    for i, sec in enumerate(src["sections"]):
        texto = sec["text"]
        prompt = (f"Traduza EXATAMENTE este texto infantil para {nome_idioma}, "
                  f"mantendo o tom alegre e o mesmo tamanho aproximado. "
                  f"Responda apenas com a tradução, sem notas nem explicações:\n\n{texto}")
        tr = limpar_traducao(gemini_text(prompt, f"{sec['id']}_{lang}"))
        if not tr or len(tr) < 10:
            # retry uma vez
            tr = limpar_traducao(gemini_text(prompt, f"{sec['id']}_{lang}_r2", wait=90))
        if not tr or len(tr) < 10:
            print(f"  AVISO {sec['id']}: usando texto original", flush=True)
            tr = texto
        nova = dict(sec)
        nova["text"] = tr
        if "label" in sec:
            nova["label"] = limpar_traducao(gemini_text(
                f"Traduza para {nome_idioma}. Responda apenas a tradução: {sec['label']}",
                f"label_{sec['id']}_{lang}")) or sec["label"]
        secoes.append(nova)
        print(f"  [{i+1}/{len(src['sections'])}] {sec['id']}: {tr[:70]}", flush=True)

    out = dict(src)
    out["title"] = t
    out["sections"] = secoes
    destino = P / f"artifacts/script_{lang}.json"
    json.dump(out, open(destino, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"OK: {destino}", flush=True)


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "es"
    traduzir(lang)
