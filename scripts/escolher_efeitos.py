# -*- coding: utf-8 -*-
r"""escolher_efeitos.py - INTELIGENCIA do pipeline: le a narracao de cada cena
e escolhe o efeito visual da BIBLIOTECA_EFEITOS que casa com o texto.

Regra: 1 efeito principal por cena (REGRA DE OURO §65 - imagem/fala no mesmo
instante). Gera artifacts/efeitos_por_cena.json: {sid: {efeito, pngs, razao}}.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(r"C:\videomaker")
BIB = ROOT / "BIBLIOTECA_EFEITOS"

# gatilhos -> (efeito, razao)
REGRAS = [
    (r"ossinh?o|osso voador|osso", "ossinhos", "fala de osso"),
    (r"ração|racao|biscoito|carne|comida|almoço|fome|petisco|comidinha", "racao_varios_formatos", "fala de comida/racao"),
    (r"sono|dormir|cochilo|cansa|sonhar|noite|sonolent", "soninho_zzz", "fala de sono"),
    (r"chuva|tempestade|água caindo|goteira", "chuva", "fala de chuva"),
    (r"mágic|magia|feiti|surpresa|misterios|encantad|poeirinha", "estrelinhas", "fala de magia/surpresa"),
    (r"abelha|mel|flor|jardim|primavera", "abelhinhas", "fala de abelhas/flores"),
    (r"coração|coracao|amor|carinho|abraço|abraço|fique com a gente|amizade", "coracoes", "fala de amor/carinho"),
    (r"passarinho|pássaro|passaro|pomb|voar|voo|céu|ceu azul", "passarinhos", "fala de passer/céu"),
    (r"bolinha|bola de tênis|bola", "bolinhas_sabao", "fala de bola/brincadeira"),
    (r"vento|folha|gramado|parque|árvore|arvore", "folhinhas_vento", "cena ao ar livre/vento"),
    (r"neblina|fumaça|fumaca|suspense|calma|suave", "fumacinha", "cena suave/mistério"),
]
# fallback neutro alegre
FALLBACK = ("bolinhas_sabao", "neutro alegre")

# mapeamento efeito -> arquivos PNG na biblioteca (multiplas particulas)
PNGS = {
    "ossinhos": ["osso.png"],
    "racao_varios_formatos": ["racao_bola.png","racao_quad.png","racao_tri.png","racao_oval.png","racao_gota.png"],
    "soninho_zzz": ["zzz.png"],
    "chuva": ["gota.png"],
    "estrelinhas": ["estrela.png"],
    "abelhinhas": ["abelha.png"],
    "coracoes": ["coracao.png"],
    "passarinhos": ["passaro.png"],
    "bolinhas_sabao": ["bolha.png"],
    "folhinhas_vento": ["folha.png"],
    "fumacinha": ["fumaca.png"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--lang", default="pt")
    a = ap.parse_args()
    P = ROOT / "projects" / a.slug
    scr = json.load(open(P / "artifacts/script.json", encoding="utf-8"))
    sc = json.load(open(P / "artifacts/scenes.json", encoding="utf-8"))
    out = {}
    for s in scr["sections"]:
        sid = s["id"]
        cfg = sc.get(sid, {})
        # texto falado: beats (ja sincronizados) ou texto cheio
        if isinstance(cfg, dict) and cfg.get("beats"):
            texto = " ".join(b.get("text", "") for b in cfg["beats"])
        else:
            texto = s.get("text", "")
        tl = texto.lower()
        escolhido, razao = FALLBACK
        for padrao, efeito, mot in REGRAS:
            if re.search(padrao, tl, re.I):
                escolhido, razao = efeito, mot
                break
        out[sid] = {"efeito": escolhido, "razao": razao,
                    "pngs": PNGS.get(escolhido, [])}
        print(f"{sid:9s} -> {escolhido:24s} ({razao})")
    dest = P / "artifacts" / "efeitos_por_cena.json"
    json.dump(out, open(dest, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("salvo:", dest)


if __name__ == "__main__":
    main()
