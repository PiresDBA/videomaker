# -*- coding: utf-8 -*-
"""refazer_plano_semantico.py - casa as 17 cenas erradas com imagens novas
por SEMANTICA (acao descrita no texto vs nome descritivo da imagem).
Ignora similaridade visual (todas sao da mesma sala - natural).
"""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(r"C:\videomaker")

# Mapa manual: cena -> imagem nova (escolhida pelo que o TEXTO pede)
MAPA = {
    # s2[1] "deu três voltas, cheirando cada pedacinho" -> farejar/perto da caminha
    "desenvolvimento_1_scene_b.jpg": "Two_dogs_inspect_red_bed_d614a16c - Copia (2).jpg",
    # s5[1] "bolinha de tênis verde" -> olhando a bola
    "desenvolvimento_4_scene_b.jpg": "Two_dogs_looking_at_ball_05d78522 - Copia.jpg",
    # s5[2] "jogou no centro da caminha" -> pulando para dentro
    "desenvolvimento_4_scene_c.jpg": "Two_dogs_jumping_into_bed_e55868d2 - Copia.jpg",
    # s6[0] "Luninha curiosa, desafio" -> explorando a caminha nova
    "desenvolvimento_5_scene.jpg": "Two_dogs_exploring_new_bed_0cc4d57b - Copia - Copia.jpg",
    # s6[1] "resgatar a bolinha verde com cuidado" -> olhando a bola
    "desenvolvimento_5_scene_b.jpg": "Two_dogs_looking_at_ball_dde09f24 - Copia (2).jpg",
    # s6[2] "aproximou rastejando colada no chao" -> perto/cheirando a caminha
    "desenvolvimento_5_scene_c.jpg": "Two_dogs_near_dog_bed_40dde3d8.jpg",
    # s7[0] "Luninha imóvel dentro da caminha" -> dentro da caminha
    "desenvolvimento_6_scene.jpg": "Two_dogs_in_dog_bed_62422bb1 - Copia - Copia.jpg",
    # s7[1] "olhinhos arregalados, patinhas para o alto" -> abrindo olhos
    "desenvolvimento_6_scene_b.jpg": "Two_dogs_opening_eyes_2c4a0362.jpg",
    # s7[2] "monstro fofo da caminha ia engolir" -> reacao em paineis
    "desenvolvimento_6_scene_c.jpg": "Two_dogs_reacting_in_panels_b7b125ed.jpg",
    # s17[0] "grande lição" -> compartilhando ideias
    "li_o_da_hist_ria_scene.jpg": "Two_dogs_sharing_ideas_8d5ade72.jpg",
    # s17[1] "nunca julgar antes de experimentar" -> deitadas na caminha
    "li_o_da_hist_ria_scene_b.jpg": "Two_dogs_in_dog_bed_c7433f48 - Copia - Copia.jpg",
    # s17[2] "lugar favorito do mundo" -> na caminha, relaxadas
    "li_o_da_hist_ria_scene_c.jpg": "Two_dogs_on_bed_4eef5115.jpg",
    # s_final[0] "termina nossa aventura" -> relaxando
    "o_v_deo_acabou_scene.jpg": "Two_dogs_relaxing_and_hearing_9ff2888f.jpg",
    # s_final[1] "final da nossa história" -> descansando ao sol
    "o_v_deo_acabou_scene_b.jpg": "Two_dogs_resting_afternoon_sun_55c2eb34.jpg",
    # s_outro[0] "obrigado por assistir" -> acenando para camera
    "agradecimento_scene.jpg": "Two_dogs_waving_at_camera_2bcd88be.jpg",
    # s_outro[1] "like, inscreva, indique aos amiguinhos" -> sentadas juntas
    "agradecimento_scene_b.jpg": "Two_female_dogs_sitting_together_58c72075.jpg",
    # s_outro[2] "beijo no coração, próximos vídeos" -> com travesseiro/coração
    "agradecimento_scene_c.jpg": "Two_dogs_with_pillow_6bb589c1.jpg",
}

plano = json.load(open(ROOT / "plano_trocas.json", encoding="utf-8"))
# verifica que todas as imagens existem
novas = ROOT / "projects/a-caminha-nova-que-ninguem-quer-usar/assets/images/gemini/_novas_baixadas"
for c, n in MAPA.items():
    if not (novas / n).exists():
        print("FALTA:", n)
    # atualiza o plano
    for x in plano:
        if x["errada"] == c:
            x["nova"] = n
            x["score"] = 99
json.dump(plano, open(ROOT / "plano_trocas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
# checa duplicatas de imagem no mapa
vals = list(MAPA.values())
print("duplicatas no mapa:", [v for v in set(vals) if vals.count(v) > 1])
print("plano semantico salvo:", len(MAPA), "trocas")
