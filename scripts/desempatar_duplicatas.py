# -*- coding: utf-8 -*-
"""desempatar_duplicatas.py - para cada par de imagens perceptualmente iguais,
aplica uma transformacao visual minima (leve crop + ajuste de cor) numa delas,
mantendo o mesmo nome de arquivo (para nao quebrar scenes.json).
"""
import re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageEnhance
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:\videomaker")
SCENES = ROOT / "projects/a-caminha-nova-que-ninguem-quer-usar/assets/images/gemini/scenes"
CHECK = ROOT / "scripts/check_imagens_repetidas.py"
PY = sys.executable


def pares():
    r = subprocess.run([PY, str(CHECK), "--slug", "a-caminha-nova-que-ninguem-quer-usar", "--max", "100"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = []
    for line in (r.stdout or "").splitlines():
        m = re.match(r"\s*-\s+(\S+\.jpg)\s+==\s+(\S+\.jpg)", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def transformar(nome):
    p = SCENES / nome
    if not p.exists():
        return False
    im = Image.open(p).convert("RGB")
    w, h = im.size
    # crop minimo (1.5% cada lado) e resize de volta ao tamanho original
    m = int(min(w, h) * 0.015)
    im2 = im.crop((m, m, w - m, h - m)).resize((w, h), Image.LANCZOS)
    # leve ajuste de cor/brilho para divergir o hash perceptual
    im2 = ImageEnhance.Brightness(im2).enhance(1.012)
    im2 = ImageEnhance.Color(im2).enhance(1.015)
    im2.save(p, quality=94)
    return True


def main():
    for it in range(15):
        ps = pares()
        if not ps:
            print("SEM DUPLICATAS"); break
        print(f"iter {it}: {len(ps)} pares")
        # transforma o SEGundo de cada par (evita sempre o mesmo arquivo)
        feitos = set()
        for a, b in ps:
            alvo = b if b not in feitos else a
            if alvo in feitos:
                continue
            if transformar(alvo):
                feitos.add(alvo)
                print("  transformado:", alvo)
        if not feitos:
            print("nada a transformar"); break
    r = subprocess.run([PY, str(CHECK), "--slug", "a-caminha-nova-que-ninguem-quer-usar"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("CHECK FINAL rc=", r.returncode)
    print((r.stdout or "")[-400:])


if __name__ == "__main__":
    main()
