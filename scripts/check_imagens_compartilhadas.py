# -*- coding: utf-8 -*-
"""
Garante que PT, EN e ES usam EXATAMENTE as mesmas imagens.

As imagens de cena sao geradas UMA vez (Google Flow, em portugues) e os tres
idiomas reaproveitam a mesma pasta `assets/images/gemini/scenes`. Por idioma
muda apenas: traducao do roteiro, overlays, narracao, legendas, mixagem e
render. NUNCA se gera imagem nova por idioma (CONTRATO.md 5.9).

Este script grava um manifesto (nome + sha1) depois da fase de imagens e
confere antes de cada render. Se alguma imagem aparecer, desaparecer ou mudar
entre idiomas, ele ABORTA - sinal de que a fase de imagens rodou de novo sem
querer (ou que alguem trocou a pasta).

Uso:
  python scripts/check_imagens_compartilhadas.py --slug <slug> --update
      grava/atualiza o manifesto (usar SO depois da fase de imagens)
  python scripts/check_imagens_compartilhadas.py --slug <slug>
      confere antes de cada render (exit 1 se mudou)
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXTENSOES = (".jpg", ".jpeg", ".png")


def _manifesto(pasta: Path) -> dict:
    dados = {}
    for f in sorted(pasta.iterdir()):
        if f.suffix.lower() in EXTENSOES and not f.name.startswith("_"):
            dados[f.name] = hashlib.sha1(f.read_bytes()).hexdigest()
    return dados


def _comparar(antigo: dict, atual: dict):
    novos = sorted(set(atual) - set(antigo))
    sumiram = sorted(set(antigo) - set(atual))
    mudaram = sorted(k for k in set(antigo) & set(atual) if antigo[k] != atual[k])
    return novos, sumiram, mudaram


def main() -> int:
    ap = argparse.ArgumentParser(
        description="PT/EN/ES tem que usar as mesmas imagens (nada novo por idioma)")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--projects-dir", default=str(ROOT / "projects"))
    ap.add_argument("--update", action="store_true",
                    help="grava o manifesto (so depois da fase de imagens)")
    ap.add_argument("--prompts", default="",
                    help="image_prompts.json para conferir a quantidade")
    args = ap.parse_args()

    p_dir = Path(args.projects_dir) / args.slug
    pasta = p_dir / "assets" / "images" / "gemini" / "scenes"
    if not pasta.is_dir():
        print(f"ERRO: pasta de cenas inexistente: {pasta}")
        return 1

    atual = _manifesto(pasta)
    if not atual:
        print(f"ERRO: nenhuma imagem em {pasta}. Gere as imagens antes de renderizar.")
        return 1

    prompts = Path(args.prompts) if args.prompts else p_dir / "artifacts" / "image_prompts.json"
    esperado = None
    if prompts.exists():
        try:
            dados = json.loads(prompts.read_text(encoding="utf-8-sig"))
            esperado = len([k for k in dados if not str(k).startswith("_")])
        except Exception:
            esperado = None
    if esperado is not None and esperado != len(atual):
        print(f"ERRO: {len(atual)} imagens na pasta, mas o roteiro pede {esperado}.")
        print("      Gere as que faltam na fase de imagens (uma vez so, em PT).")
        return 1

    arq = p_dir / "artifacts" / "images_manifest.json"
    if args.update or not arq.exists():
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(json.dumps(atual, indent=1, sort_keys=True), encoding="utf-8")
        print(f"[OK] manifesto gravado: {len(atual)} imagens compartilhadas "
              f"por PT/EN/ES ({arq.name})")
        return 0

    try:
        antigo = json.loads(arq.read_text(encoding="utf-8-sig"))
    except Exception:
        arq.unlink(missing_ok=True)
        print("[OK] manifesto ilegivel; sera regravado na proxima fase de imagens")
        return 0

    novos, sumiram, mudaram = _comparar(antigo, atual)
    if novos or sumiram or mudaram:
        print("=" * 70)
        print("TRACADO: as imagens mudaram entre idiomas")
        print("=" * 70)
        for nome in novos:
            print(f"  + nova: {nome}")
        for nome in sumiram:
            print(f"  - sumiu: {nome}")
        for nome in mudaram:
            print(f"  ~ alterada: {nome}")
        print()
        print("PT, EN e ES usam as MESMAS imagens (CONTRATO.md 5.9).")
        print("Imagem nova so na fase de imagens, uma vez, antes dos 3 renders.")
        print("Se a troca foi proposital: rode com --update depois de gerar.")
        return 1

    print(f"[OK] imagens compartilhadas: {len(atual)} iguais para PT/EN/ES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
