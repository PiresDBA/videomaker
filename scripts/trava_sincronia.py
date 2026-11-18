# -*- coding: utf-8 -*-
r"""trava_sincronia.py - TRAVA DA REGRA DE OURO (CONTRATO / MANUAL §65).

Antes de renderizar, verifica para cada BEAT da narração se a imagem
correspondente tem a ver com o texto falado. FALHA (exit 1) se:
  - uma imagem pertence a OUTRO tema (parque/trofeu/festa quando não é o tema);
  - palavras-chave fortes do beat (osso, cama, comida, bola...) NÃO aparecem
    nem no prompt da imagem;
  - imagem replicada de vídeo anterior (palavras do tema antigo no prompt).

Uso: python scripts/trava_sincronia.py --slug <projeto>
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# Palavras do texto -> termos esperados no prompt da imagem
PALAVRAS_CHAVE = {
    r"\bosso\b": ["osso", "bone"],
    r"\bcama\b|\bcaminha\b|\bleito\b": ["cama", "caminha", "bed"],
    r"\bcomida\b|\bração\b|\bbiscoito\b|\bcarne\b": ["comida", "racao", "biscoito", "carne", "food", "meat"],
    r"\bbola\b|\bbolinha\b|\btênis\b": ["bola", "ball", "tennis"],
    r"\bveterin": ["veterin", "vet", "clinica"],
    r"\bsofá\b|\bsofa\b": ["sofa", "sofa", "couch"],
    r"\bgato\b": ["gato", "cat"],
    r"\bpombo\b|\bpassarinho\b|\bpássaro\b": ["pombo", "passaro", "bird", "pigeon"],
    r"\bformiga\b": ["formiga", "ant"],
    r"\bjoaninha\b": ["joaninha", "ladybug"],
    r"\bborboleta\b": ["borboleta", "butterfly"],
    r"\bágua\b|\bwater\b": ["agua", "water", "fonte"],
    r"\bcant": ["cant", "sing", "musica", "music"],
}
# temas de OUTROS vídeos que não podem vazar (exceção: o projeto os cita de proposito)
Vazamento = ["campeonato", "pet shop", "parque de diversoes", "fazenda", "super-heroi"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    a = ap.parse_args()
    p = ROOT / "projects" / a.slug
    scr = json.load(open(p / "artifacts/script.json", encoding="utf-8"))
    sc = json.load(open(p / "artifacts/scenes.json", encoding="utf-8"))
    pr = json.load(open(p / "artifacts/image_prompts.json", encoding="utf-8"))
    problemas = []
    checados = 0
    for s in scr["sections"]:
        cfg = sc.get(s["id"], {})
        if not isinstance(cfg, dict):
            continue
        imgs = [i for i in cfg.get("images", []) if not i.endswith(".mp4")]
        beats = cfg.get("beats", [])
        for i, b in enumerate(beats):
            if i >= len(imgs):
                break
            nome = imgs[i]
            prompt = pr.get(Path(nome).stem, "").lower()
            texto = b.get("text", "")
            checados += 1
            # vazamento de tema alheio
            for v in Vazamento:
                if v in prompt and v not in texto.lower():
                    problemas.append(f"{s['id']}[{i}] {nome}: VAZAMENTO de tema '{v}'")
            # palavras-chave do beat devem casar com o prompt
            for padrao, esperados in PALAVRAS_CHAVE.items():
                if re.search(padrao, texto, re.I):
                    if not any(e in prompt for e in esperados):
                        problemas.append(
                            f"{s['id']}[{i}] {nome}: texto fala '{padrao}' mas imagem nao mostra {esperados}")
                    break
    print(f"beats checados: {checados} | problemas: {len(problemas)}")
    for x in problemas[:30]:
        print("  ✗", x)
    if problemas:
        print("TRAVA FALHOU: imagem fora de sincronia com a narração (MANUAL §65).")
        return 1
    print("[OK] sincronia imagem<->narração conforme (regla de ouro).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
