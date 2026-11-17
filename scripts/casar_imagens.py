# -*- coding: utf-8 -*-
"""casar_imagens.py - casa as 17 cenas erradas com as 40 imagens novas.

Para cada cena errada, pega o TEXTO do beat e escolhe a imagem nova cujo nome
descritivo (ex: Two_dogs_looking_at_ball) tem maior sobreposicao de palavras.
Nao repete imagens. Salva o plano em plano_trocas.json (NAO copia ainda).
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
P = Path(r"C:\videomaker\projects\a-caminha-nova-que-ninguem-quer-usar")
SCENES = P / "assets/images/gemini/scenes"

# Sinonimos: palavras do texto PT -> termos nos nomes EN das imagens
SIN = {
    "investigar": ["inspect", "looking", "exploring", "near"],
    "cheirando": ["inspect", "near", "smelling"],
    "caminha": ["bed", "dog_bed"], "cama": ["bed"], "almofada": ["pillow"],
    "travesseiro": ["pillow", "bed"], "cobertor": ["bed", "with_pillow"],
    "bolinha": ["ball", "looking_at_ball"], "bola": ["ball"],
    "tênis": ["ball", "looking_at_ball"], "brinquedo": ["ball", "playing"],
    "resgatar": ["reaching", "looking_at_ball", "jumping"],
    "rastejando": ["near", "in_bed"], "espiando": ["looking", "peeking"],
    "pulou": ["jumping", "leaving"], "pulo": ["jumping"], "saltou": ["jumping"],
    "imóvel": ["in_bed", "resting", "relaxing"], "parado": ["in_bed", "resting"],
    "dormindo": ["resting", "sleeping", "in_bed", "waking"],
    "acordou": ["waking", "opening_eyes"], "olhos": ["opening_eyes", "looking"],
    "reunião": ["sharing_ideas", "sitting_together", "reacting"],
    "conversa": ["sharing_ideas", "reacting"], "debater": ["sharing_ideas"],
    "briga": ["fighting"], "brigando": ["fighting"], "disputa": ["fighting"],
    "abrindo": ["opening", "leaving"], "saindo": ["leaving", "running"],
    "chegando": ["running", "jumping"], "correndo": ["running"],
    "cozinha": ["in_kitchen", "hearing_treat"], "pintando": ["painting"],
    "lição": ["waving", "sharing", "sitting"], "aprender": ["waving", "sharing"],
    "obrigado": ["waving", "sitting"], "agrade": ["waving", "sitting"],
    "like": ["waving"], "inscreva": ["waving", "sitting"],
    "beijo": ["waving", "with_pillow", "sharing"],
    "final": ["waving", "resting", "sitting"], "acabou": ["waving", "leaving", "resting"],
    "orelhinhas": ["sharing_ideas", "reacting"], "cara": ["reacting", "looking"],
    "surpresa": ["reacting", "opening_eyes"], "assustad": ["reacting", "jumping"],
    "sol": ["resting_afternoon_sun", "resting"], "tarde": ["resting_afternoon_sun"],
    "macio": ["with_pillow", "in_bed"], "fofinho": ["with_pillow", "in_bed"],
}

# As 17 cenas erradas (nome do arquivo -> secao/beat -> texto)
ERRADAS = {
    "desenvolvimento_1_scene_b.jpg": ("s2", 1),
    "desenvolvimento_4_scene_b.jpg": ("s5", 1),
    "desenvolvimento_4_scene_c.jpg": ("s5", 2),
    "desenvolvimento_5_scene.jpg": ("s6", 0),
    "desenvolvimento_5_scene_b.jpg": ("s6", 1),
    "desenvolvimento_5_scene_c.jpg": ("s6", 2),
    "desenvolvimento_6_scene.jpg": ("s7", 0),
    "desenvolvimento_6_scene_b.jpg": ("s7", 1),
    "desenvolvimento_6_scene_c.jpg": ("s7", 2),
    "li_o_da_hist_ria_scene.jpg": ("s17", 0),
    "li_o_da_hist_ria_scene_b.jpg": ("s17", 1),
    "li_o_da_hist_ria_scene_c.jpg": ("s17", 2),
    "o_v_deo_acabou_scene.jpg": ("s_final", 0),
    "o_v_deo_acabou_scene_b.jpg": ("s_final", 1),
    "agradecimento_scene.jpg": ("s_outro", 0),
    "agradecimento_scene_b.jpg": ("s_outro", 1),
    "agradecimento_scene_c.jpg": ("s_outro", 2),
}

def main():
    sc = json.load(open(P/"artifacts/scenes.json", encoding="utf-8"))
    novas = json.load(open(r"C:\videomaker\novas_unicas.json", encoding="utf-8"))
    usadas = set()
    plano = []
    for errada, (sid, beat_i) in ERRADAS.items():
        beats = sc.get(sid, {}).get("beats", [])
        texto = beats[beat_i].get("text", "") if beat_i < len(beats) else ""
        tl = texto.lower()
        # termos-alvo a partir do texto + sinonimos
        alvos = set()
        for pt, ens in SIN.items():
            if pt in tl:
                alvos.update(ens)
        # sempre aceita genericas fracas como fallback
        alvos.update(["dog", "bed"])
        best, best_score = None, -1
        for n in novas:
            if n in usadas:
                continue
            nl = n.lower().replace("- copia", "").replace("- copia (2)", "")
            score = sum(1 for a in alvos if a in nl)
            # penaliza imagens com 3o cachorro (sharing_dog_bed_87c etc tem terceiro)
            if "two_female" in nl:
                score += 1
            if score > best_score:
                best, best_score = n, score
        if best is None:
            continue
        usadas.add(best)
        plano.append({"errada": errada, "secao": sid, "beat": beat_i,
                      "texto": texto, "nova": best, "score": best_score})
    Path(r"C:\videomaker\plano_trocas.json").write_text(
        json.dumps(plano, ensure_ascii=False, indent=2), encoding="utf-8")
    for p in plano:
        print(f'{p["errada"][:34]:36s} <- {p["nova"][:44]:46s} [{p["score"]}] {p["secao"]}[{p["beat"]}]')
    print("total:", len(plano))

if __name__ == "__main__":
    main()
