# -*- coding: utf-8 -*-
"""auditoria_visual.py - auditoria REAL das imagens do video (2026-11-20).

Por que a antiga nao funcionava:
  * check_personagens_imagens.py era um STUB (auditar() = NotImplementedError)
  * make_contact_sheet.py tinna SCENES fixo de OUTRO projeto
  * nenhuma das duas rodava no Hook antes de publicar

O que faz:
  1. varre TODAS as imagens de cena do projeto
  2. detecta FOLHA DE REFERENCIA (fundo branco + muito texto/bordas)
  3. detecta duplicatas por hash e imagens suspeitas (muito largas)
  4. gera folhas de contato em <proj>/conferencia/auditoria_visual/
  5. grava artifacts/auditoria_visual_<lang>.json com status e caminhos

O campo `revisado_por_agente` so vira true depois que o agente REALMENTE
abrir e olhar as folhas de contato (ferramenta de leitura de imagem).
O Hook bloqueia publicacao se status != PASS ou revisado_por_agente != true.

Uso:
  python scripts/auditoria_visual.py --slug <slug> --lang pt|en|es
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJ = ROOT / "projects"


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def metricas(path):
    """Folha de referencia: muito branco + bordas (texto) + aspecto largo."""
    try:
        import numpy as np
        from PIL import Image
        im = Image.open(path).convert("RGB")
        w, h = im.size
        small = im.resize((160, 90))
        a = np.asarray(small, dtype=np.float32)
        branco = float((a.min(axis=2) > 200).mean())
        g = np.asarray(small.convert("L"), dtype=np.float32)
        bordas = float((np.abs(np.diff(g, axis=1)) > 40).mean())
        return {"branco": round(branco, 3), "bordas": round(bordas, 3),
                "aspecto": round(w / max(h, 1), 2)}
    except Exception as e:
        return {"erro": str(e)}


def gerar_contatos(imgs, out_dir, cols=5, rows=4):
    from PIL import Image, ImageDraw
    out_dir.mkdir(parents=True, exist_ok=True)
    tw, th, label_h = 300, 200, 34
    per = cols * rows
    paths = []
    for page in range((len(imgs) + per - 1) // per):
        chunk = imgs[page * per:(page + 1) * per]
        sheet = Image.new("RGB", (cols * tw, rows * (th + label_h)), (18, 18, 18))
        d = ImageDraw.Draw(sheet)
        for j, f in enumerate(chunk):
            r, c = divmod(j, cols)
            x, y = c * tw, r * (th + label_h)
            try:
                im = Image.open(f).convert("RGB")
                im.thumbnail((tw - 6, th - 6))
                sheet.paste(im, (x + 3, y + 3))
            except Exception:
                pass
            d.rectangle((x, y + th, x + tw, y + th + label_h), fill=(0, 0, 0))
            d.text((x + 4, y + th + 2), f.name[:42], fill=(255, 220, 80))
        p = out_dir / f"contato_{page + 1:02d}.jpg"
        sheet.save(p, quality=86)
        paths.append(str(p))
    return paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--lang", default="pt", choices=["pt", "en", "es"])
    ap.add_argument("--revisar", action="store_true",
                    help="marca revisado_por_agente=true (so apos olhar os contatos)")
    a = ap.parse_args()
    P = PROJ / a.slug
    d = P / "assets" / "images" / "gemini" / "scenes"
    imgs = sorted(f for f in d.glob("*.jpg") if not f.name.startswith("_"))
    if not imgs:
        print("NENHUMA IMAGEM ENCONTRADA")
        return 1

    erros, avisos = [], []
    hashes = {}
    for f in imgs:
        m = metricas(f)
        if m.get("branco", 0) > 0.60 and m.get("bordas", 0) > 0.055:
            erros.append(f"FOLHA DE REFERENCIA: {f.name} {m}")
        if m.get("aspecto", 1) > 2.3:
            avisos.append(f"imagem muito larga (possivel colagem): {f.name} {m}")
        h = md5(f)
        if h in hashes:
            erros.append(f"DUPLICATA: {f.name} == {hashes[h]}")
        else:
            hashes[h] = f.name

    contatos = gerar_contatos(imgs, P / "conferencia" / "auditoria_visual")

    out = P / "artifacts" / f"auditoria_visual_{a.lang}.json"
    prev = {}
    if out.exists():
        try:
            prev = json.loads(out.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    revisado = bool(prev.get("revisado_por_agente")) if not a.revisar else True
    dados = {
        "slug": a.slug,
        "lang": a.lang,
        "status": "PASS" if not erros else "FALHA",
        "total_imagens": len(imgs),
        "erros": erros,
        "avisos": avisos,
        "contatos": contatos,
        "revisado_por_agente": revisado,
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"=== AUDITORIA VISUAL {a.lang.upper()} ===")
    print(f"imagens: {len(imgs)} | status: {dados['status']}")
    for e in erros[:20]:
        print("  ERRO:", e)
    for av in avisos[:10]:
        print("  AVISO:", av)
    print("contatos:")
    for c in contatos:
        print("  ", c)
    print(f"revisado_por_agente: {revisado}")
    print(f"relatorio: {out}")
    return 0 if not erros else 1


if __name__ == "__main__":
    sys.exit(main())
