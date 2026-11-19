# -*- coding: utf-8 -*-
"""hulk_validator.py - O HULK: guarda das regras do CONTRATO.

Roda ANTES de publicar (e pode ser chamado a qualquer momento). Se alguma
regra foi quebrada, ELE AVISA e bloqueia. Regras verificadas:

 1. imagens: nenhuma duplicata (hash igual)
 2. batimento roteiro/foto: 0 ERRADOS
 3. personagens: prompts/scenes usam @Frida/@Luna (arro, sem colchetes)
 4. sintaxe proibida: @[Frida]/@[Luna] (colchetes) = ERRADO
 5. 3 clipes do meio + intro + final presentes
 6. sonoplastia: obrigatoria (nao desligada)
 7. Flow guard: Gemini so apos Flow esgotar
 8. ciclo limpo: tema nao repetido de outro video
 9. espera 2min no Flow (pausa >= 120)

Uso:
  python scripts/hulk_validator.py --slug <slug>
  python scripts/hulk_validator.py --slug <slug> --strict   # bloqueia se erro
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:\videomaker")
PROJETOS = ROOT / "projects"
SCRIPTS = ROOT / "scripts"


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main(slug, strict):
    P = PROJETOS / slug
    erros, avisos, oks = [], [], []
    print(f"=== HULK - VALIDANDO {slug} ===")

    # 1) duplicatas de imagem
    d = P / "assets/images/gemini/scenes"
    imgs = list(d.glob("*.jpg")) if d.exists() else []
    hashes = {}
    dups = []
    for im in imgs:
        h = md5(im)
        if h in hashes:
            dups.append((hashes[h].name, im.name))
        else:
            hashes[h] = im
    if dups:
        erros.append(f"IMAGENS DUPLICADAS: {dups}")
    else:
        oks.append(f"{len(imgs)} imagens, 0 duplicatas")

    # 2) batimento
    bat = P / "artifacts/batimento_roteiro_foto.txt"
    if bat.exists():
        txt = bat.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"'ERRADO':\s*(\d+)", txt)
        n_err = int(m.group(1)) if m else 0
        if n_err:
            erros.append(f"BATIMENTO: {n_err} ERRADOS")
        else:
            oks.append("batimento: 0 ERRADOS")
    else:
        avisos.append("batimento nao rodou ainda")

    # 3/4) sintaxe de personagens
    ip = P / "artifacts/image_prompts.json"
    sc = P / "artifacts/scenes.json"
    textos = ""
    for f in (ip, sc):
        if f.exists():
            textos += f.read_text(encoding="utf-8", errors="replace")
    colchetes = len(re.findall(r"@\[(?:Frida|Luna)\]", textos, re.I))
    sem = len(re.findall(r"@(?:Frida|Luna)", textos, re.I))
    if colchetes:
        erros.append(f"SINTAXE ERRADA: {colchetes} ocorrencias de @[Frida]/@[Luna] (use so @Frida/@Luna)")
    else:
        oks.append(f"sintaxe @Frida/@Luna OK ({sem} ocorrencias, 0 com colchetes)")

    # 5) clipes
    if d.exists():
        vids = [v.name for v in d.glob("*.mp4")]
        meio = [v for v in vids if "meio" in v]
        intro = [v for v in vids if "intro" in v]
        final = [v for v in vids if "final" in v]
        if len(meio) >= 3 and intro and final:
            oks.append(f"clipes: intro={len(intro)} meio={len(meio)} final={len(final)}")
        else:
            avisos.append(f"clipes incompletos: intro={len(intro)} meio={len(meio)} final={len(final)}")

    # 6) sonoplastia
    for f in (SCRIPTS / "sonoplastia_por_idioma.py", SCRIPTS / "gerar_sonoplastia.py"):
        if not f.exists():
            erros.append(f"sonoplastia faltando: {f.name}")
    if not erros:
        oks.append("sonoplastia no pipeline")

    # 7) flow guard
    fb = (SCRIPTS / "flow_agent_batch.py").read_text(encoding="utf-8", errors="replace")
    if "FLOW_GUARD" not in fb or "TENTATIVAS_TAM1" not in fb:
        erros.append("FLOW_GUARD ausente no flow_agent_batch.py")
    else:
        oks.append("FLOW_GUARD presente (Gemini so apos Flow esgotar)")

    # 8) ciclo limpo (topics)
    tp = (SCRIPTS / "topics.txt").read_text(encoding="utf-8", errors="replace")
    if slug in tp or (P / "artifacts/script.json").exists() and \
       json.loads((P / "artifacts/script.json").read_text(encoding="utf-8")).get("title", "") in tp:
        oks.append("tema registrado em topics.txt (ciclo limpo)")
    else:
        avisos.append("tema pode nao estar registrado em topics.txt")

    # 9) pausa 2min
    pl = (SCRIPTS / "pipeline.py").read_text(encoding="utf-8", errors="replace")
    if 'default=120' not in pl:
        erros.append("pausa padrao do pipeline nao e 120s (regra dos 2 min)")
    else:
        oks.append("pausa padrao 120s (2 min) OK")

    print("\n".join(f"  OK  {x}" for x in oks))
    print("\n".join(f"  AVISO  {x}" for x in avisos))
    print("\n".join(f"  ERRO  {x}" for x in erros))
    print(f"\n=== RESULTADO: {len(erros)} erro(s), {len(avisos)} aviso(s) ===")
    if erros:
        print("HULK: NAO PODE SEGUIR. Corrija os erros acima.")
    if strict and (erros or avisos):
        sys.exit(1)
    return 1 if erros else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    sys.exit(main(a.slug, a.strict))
