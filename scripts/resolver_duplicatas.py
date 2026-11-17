# -*- coding: utf-8 -*-
"""resolver_duplicatas.py - troca imagens recem-aplicadas que colidem com
outras cenas por novas nao-usadas que nao colidem.

Roda check_imagens_repetidas, pega os pares, e para cada imagem do nosso
plano que aparece num par, escolhe uma substituta dentre as novas nao-usadas
que nao seja parecida com NENHUMA imagem da pasta.
"""
import json, subprocess, sys, shutil, re, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"C:\videomaker")
SCENES = ROOT / "projects/a-caminha-nova-que-ninguem-quer-usar/assets/images/gemini/scenes"
NOVAS = SCENES.parent / "_novas_baixadas"
CHECK = ROOT / "scripts/check_imagens_repetidas.py"
PY = sys.executable
plano = json.load(open(ROOT / "plano_trocas.json", encoding="utf-8"))
usadas = {x["nova"] for x in plano}


def assinatura(p):
    from PIL import Image
    import numpy as np
    im = Image.open(p).convert("RGB").resize((32, 32))
    return np.asarray(im, dtype=float)


def dist(a, b):
    import numpy as np
    return float(np.abs(a - b).mean())


def rodar_check():
    r = subprocess.run([PY, str(CHECK), "--slug", "a-caminha-nova-que-ninguem-quer-usar", "--max", "100"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    pares = []
    for line in (r.stdout or "").splitlines():
        m = re.match(r"\s*-\s+(\S+\.jpg)\s+==\s+(\S+\.jpg)", line)
        if m:
            pares.append((m.group(1), m.group(2)))
    return pares


def main():
    # assinaturas de todas as imagens atuais
    atual = {f.name: assinatura(f) for f in SCENES.glob("*.jpg")}
    # novas nao usadas
    candidatas = [f for f in NOVAS.glob("*.jpg") if f.name not in usadas]
    print("candidatas nao usadas:", len(candidatas))

    # imagem (nome DA CENA, que e o arquivo real) -> plano
    cena_para_plano = {x["errada"]: x for x in plano}

    for it in range(20):
        pares = rodar_check()
        if not pares:
            print("SEM DUPLICATAS"); break
        print(f"iter {it}: {len(pares)} pares")
        # pega uma imagem do plano (pelo nome da cena no arquivo) em algum par
        alvo = None
        for a, b in pares:
            if a in cena_para_plano or b in cena_para_plano:
                alvo = a if a in cena_para_plano else b
                break
        if alvo is None:
            print("nenhum par envolve imagem do plano:", pares[:3]); break
        x = cena_para_plano[alvo]
        arquivo = SCENES / x["errada"]
        if not arquivo.exists():
            print("arquivo ausente:", arquivo); break
        # escolhe candidata que nao colide com NENHUMA imagem atual (exceto a propria alvo)
        melhor, menor = None, None
        for c in candidatas:
            sc = assinatura(c)
            maxd = min((dist(sc, atual[n]) for n in atual if n != x["errada"]), default=999)
            if menor is None or maxd > menor:
                melhor, menor = c, maxd
        if melhor is None:
            print("sem candidatas"); break
        shutil.copy2(str(melhor), str(arquivo))
        atual = {f.name: assinatura(f) for f in SCENES.glob("*.jpg")}
        x["nova"] = melhor.name
        usadas.add(melhor.name)
        if melhor in candidatas:
            candidatas.remove(melhor)
        print("  trocou", x["errada"], "<-", melhor.name[:44], "mindist", round(menor, 1))
    json.dump(plano, open(ROOT / "plano_trocas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("plano salvo")

if __name__ == "__main__":
    main()
