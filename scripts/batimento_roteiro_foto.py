# -*- coding: utf-8 -*-
r"""batimento_roteiro_foto.py - CHECK DE CONSISTENCIA roteiro <-> imagem.

Para cada CENA/beat do roteiro, compara o que a NARRACAO pede com o que a
IMAGEM mostra, e emite um relatorio de BATIMENTO (bate / nao bate / suspeito).

Uso futuro (quando houver inconsistencia entre fala e imagem):
  python scripts/batimento_roteiro_foto.py --slug <projeto>
  python scripts/batimento_roteiro_foto.py --slug <projeto> --html   # gera contato

Como funciona:
  1. Le artifacts/script.json (texto falado) + artifacts/scenes.json (beats,
     imagens e tempos) + artifacts/image_prompts.json (prompt da imagem).
  2. Extrai palavras-chave de ACAO do texto do beat (ex: "cheirou", "pulou",
     "bolinha", "susto", "acenando", "olhinhos") via DICIONARIO_ACAO.
  3. Compara com o nome do arquivo da imagem e com o prompt. Imagens baixadas
     do Flow tem nomes descritivos (Two_dogs_looking_at_ball, ...), o que
     permite casar por semantica.
  4. Classifica cada par:
       OK      - palavras de acao casam com o nome/prompt da imagem
       SUSPEITO- nome generico ou baixa sobreposicao (revisar visualmente)
       ERRADO  - imagem de OUTRO tema (parque/trofeu/festa/floresta)

Este script NAO modifica nada: apenas relata. Use junto com
make_contact_sheet.py para inspecao visual.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(r"C:\videomaker")

# Palavras do texto PT -> termos esperados no nome/prompt da imagem
DICIONARIO_ACAO = {
    "cheir": ["inspect", "smell", "near", "looking_at_bed", "nose"],
    "farej": ["inspect", "smell", "near"],
    "investig": ["inspect", "exploring", "looking"],
    "volta": ["inspect", "near", "around"],
    "bolinha": ["ball", "tennis"], "bola": ["ball", "tennis"], "tênis": ["ball"],
    "jog": ["jumping", "throw", "ball"], "quic": ["ball", "jumping"],
    "resgat": ["ball", "reaching", "jumping"], "pegar": ["ball", "reaching"],
    "rastej": ["near", "crawling", "low"], "aproxim": ["near", "approach"],
    "salto": ["jumping", "leaving"], "pul": ["jumping"], "susto": ["reacting", "jumping"],
    "assustad": ["reacting", "jumping"], "parado": ["in_bed", "resting", "still"],
    "imóvel": ["in_bed", "resting", "still"], "silêncio": ["in_bed", "resting"],
    "olhinho": ["opening_eyes", "looking", "eyes"], "arregalad": ["opening_eyes", "eyes"],
    "patinha": ["paws", "waving", "reacting"],
    "monstro": ["reacting", "looking", "bed"], "engolir": ["reacting", "bed"],
    "reunião": ["sharing_ideas", "sitting", "together"], "debat": ["sharing_ideas"],
    "convers": ["sharing_ideas", "together"], "orelhinha": ["sharing_ideas", "reacting"],
    "briga": ["fighting", "over_bed"], "disput": ["fighting"],
    "cozinha": ["kitchen", "treat_jar"], "pint": ["painting"],
    "dorm": ["resting", "sleeping", "in_bed", "waking"], "acord": ["waking", "opening_eyes"],
    "sono": ["resting", "sleeping", "in_bed"], "tarde": ["resting", "afternoon_sun"],
    "sol": ["afternoon_sun", "resting"], "espregui": ["waking", "resting"],
    "fofinho": ["pillow", "in_bed", "bed"], "macio": ["pillow", "in_bed"],
    "travesseiro": ["pillow", "bed"], "almofada": ["pillow"],
    "lição": ["sharing_ideas", "waving", "together"], "aprend": ["sharing_ideas"],
    "julgar": ["in_bed", "sharing", "looking"], "estranho": ["reacting", "looking"],
    "lugar favorito": ["on_bed", "in_bed", "resting"],
    "obrigado": ["waving", "sitting"], "like": ["waving"], "inscreva": ["waving", "sitting"],
    "beijo": ["waving", "pillow", "together"], "coração": ["pillow", "bed", "together"],
    "final": ["relaxing", "resting", "waving"], "acabou": ["relaxing", "resting", "leaving"],
    "acen": ["waving"], "fique": ["waving", "sitting"], "próximos": ["waving", "sitting"],
    "amiguinhos": ["together", "sitting"], "entrando": ["running", "jumping"],
    "correndo": ["running"], "saindo": ["leaving"],
}
TERMOS_ERRADOS = ["parque", "trofeu", "trophy", "medal", "floresta", "forest",
                  "festa", "party", "cake", "bolo", "stage", "palco"]


def extrair_alvos(texto):
    tl = texto.lower()
    alvos = set()
    for pt, ens in DICIONARIO_ACAO.items():
        if pt in tl:
            alvos.update(ens)
    alvos.update(["dog", "bed"])  # genericos sempre presentes
    return alvos


def classificar(texto, nome_arquivo, prompt):
    alvos = extrair_alvos(texto)
    nl = nome_arquivo.lower().replace("- copia", "").replace("- copia (2)", "")
    pl = (prompt or "").lower()
    base = nl + " " + pl
    # imagem de outro tema?
    for t in TERMOS_ERRADOS:
        if t in nl:
            return "ERRADO", [t]
    hits = sorted(a for a in alvos if a in base and a not in ("dog", "bed"))
    if not hits:
        return "SUSPEITO", []
    return "OK", hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--html", action="store_true", help="gera folha de contato HTML")
    args = ap.parse_args()
    p = ROOT / "projects" / args.slug
    scr = json.load(open(p / "artifacts/script.json", encoding="utf-8"))
    sc = json.load(open(p / "artifacts/scenes.json", encoding="utf-8"))
    pr = json.load(open(p / "artifacts/image_prompts.json", encoding="utf-8"))
    # Nome descritivo original das imagens trocadas (plano_trocas.json), para
    # casar por semantica mesmo depois do arquivo ter sido renomeado p/ cena.
    plano_path = ROOT / "plano_trocas.json"
    nome_original = {}
    if plano_path.exists():
        for x in json.load(open(plano_path, encoding="utf-8")):
            nome_original[x["errada"]] = x["nova"]
    cont = {"OK": 0, "SUSPEITO": 0, "ERRADO": 0}
    linhas = []
    for s in scr["sections"]:
        sid = s["id"]
        c = sc.get(sid, {})
        if not isinstance(c, dict):
            continue
        imgs = [i for i in c.get("images", []) if not i.endswith(".mp4")]
        beats = c.get("beats", [])
        for i, b in enumerate(beats):
            if i >= len(imgs):
                break
            nome = imgs[i]
            txt = b.get("text", "")
            # usa o nome descritivo original (se trocado) para casar semantica
            nome_desc = nome_original.get(nome, nome)
            prompt = pr.get(Path(nome).stem, "")
            status, hits = classificar(txt, nome_desc, prompt)
            cont[status] += 1
            marca = {"OK": "  ", "SUSPEITO": "??", "ERRADO": "XX"}[status]
            linhas.append(f' {marca} {sid}[{i}] {nome:38s} <- {txt[:68]}  [{",".join(hits[:4])}]')
    print("\n".join(linhas))
    print("\n=== RESUMO DO BATIMENTO ===", cont)
    out = p / "artifacts" / "batimento_roteiro_foto.txt"
    out.write_text("\n".join(linhas) + f"\n\nRESUMO: {cont}\n", encoding="utf-8")
    print("relatorio:", out)
    if args.html:
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "scripts/make_contact_sheet.py"),
                        "*.jpg", "batimento", "6", "5"])


if __name__ == "__main__":
    main()
