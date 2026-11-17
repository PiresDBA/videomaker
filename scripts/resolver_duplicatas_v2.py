# -*- coding: utf-8 -*-
"""resolver_duplicatas_v2.py - remove duplicatas VISUAIS respeitando SEMANTICA.

Para cada par perceptualmente igual, escolhe uma substituta dentre as novas
que: (1) case com o TEXTO do beat (mesmo dicionario do batimento) e (2) seja
visualmente distante de todas as imagens atuais. Preserva nomes de arquivo.
"""
import re, subprocess, sys, json, shutil
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_imagens_repetidas as chk
from batimento_roteiro_foto import DICIONARIO_ACAO, extrair_alvos

ROOT = Path(r"C:\videomaker")
SCENES = ROOT / "projects/a-caminha-nova-que-ninguem-quer-usar/assets/images/gemini/scenes"
NOVAS = SCENES.parent / "_novas_baixadas"
CHECK = ROOT / "scripts/check_imagens_repetidas.py"
PY = sys.executable
plano_path = ROOT / "plano_trocas.json"


def pares():
    r = subprocess.run([PY, str(CHECK), "--slug", "a-caminha-nova-que-ninguem-quer-usar", "--max", "100"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = []
    for line in (r.stdout or "").splitlines():
        m = re.match(r"\s*-\s+(\S+\.jpg)\s+==\s+(\S+\.jpg)", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def assinatura(p):
    return chk._assinatura(p)


def texto_da_cena(nome_arquivo, sc, scr):
    # nome_arquivo -> sid/beat via scenes.json
    for s in scr["sections"]:
        sid = s["id"]
        c = sc.get(sid, {})
        if not isinstance(c, dict):
            continue
        imgs = [i for i in c.get("images", []) if not i.endswith(".mp4")]
        beats = c.get("beats", [])
        for i, im in enumerate(imgs):
            if im == nome_arquivo and i < len(beats):
                return beats[i].get("text", "")
    return ""


def main():
    P = ROOT / "projects/a-caminha-nova-que-ninguem-quer-usar"
    sc = json.load(open(P / "artifacts/scenes.json", encoding="utf-8"))
    scr = json.load(open(P / "artifacts/script.json", encoding="utf-8"))
    plano = json.load(open(plano_path, encoding="utf-8"))
    # nome da cena -> texto do beat
    textos = {}
    for s in scr["sections"]:
        sid = s["id"]; c = sc.get(sid, {})
        if not isinstance(c, dict): continue
        imgs = [i for i in c.get("images", []) if not i.endswith(".mp4")]
        for i, im in enumerate(imgs):
            if i < len(c.get("beats", [])):
                textos[im] = c["beats"][i].get("text", "")

    candidatas = sorted(NOVAS.glob("*.jpg"))
    for it in range(25):
        ps = pares()
        if not ps:
            print("SEM DUPLICATAS"); break
        print(f"iter {it}: {len(ps)} pares")
        feitos = set()
        for a, b in ps:
            # escolhe a vitima: de preferencia a que veio do plano (tem texto)
            alvo = b if b in textos else (a if a in textos else b)
            if alvo in feitos:
                continue
            txt = textos.get(alvo, "")
            alvos = extrair_alvos(txt) if txt else set()
            # assinaturas atuais (sem o alvo)
            atuais = {}
            for f in SCENES.glob("*.jpg"):
                if f.name != alvo:
                    try: atuais[f.name] = assinatura(f)
                    except: pass
            melhor, melhor_score = None, -1e9
            for c in candidatas:
                nl = c.name.lower().replace("- copia", "").replace("- copia (2)", "")
                sem = sum(1 for a_ in alvos if a_ in nl and a_ not in ("dog", "bed"))
                if sem == 0 and txt:  # exige casamento semantico quando ha texto
                    continue
                sc_c = assinatura(c)
                mind = min((chk._distancia(sc_c, s) for s in atuais.values()), default=999)
                score = sem * 10 + mind / 10
                if score > melhor_score:
                    melhor, melhor_score = c, score
            if melhor is None:
                continue
            shutil.copy2(str(melhor), str(SCENES / alvo))
            feitos.add(alvo)
            print(f"  {alvo[:32]:34s} <- {melhor.name[:40]:42s} sem+dist={melhor_score:.1f}")
            # atualiza plano se essa imagem veio do plano
            for x in plano:
                if x["errada"] == alvo:
                    x["nova"] = melhor.name
        if not feitos:
            print("nada feito"); break
    json.dump(plano, open(plano_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    r = subprocess.run([PY, str(CHECK), "--slug", "a-caminha-nova-que-ninguem-quer-usar"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("CHECK rc=", r.returncode)

if __name__ == "__main__":
    main()
