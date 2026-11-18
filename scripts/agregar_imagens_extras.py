# -*- coding: utf-8 -*-
r"""agregar_imagens_extras.py - agrega as 15 imagens antigas (da casa/veterinario)
as cenas do roteiro novo (pracinha), casando por SEMANTICA.

Para cada imagem extra, escolhe a cena cujo texto fala do assunto da imagem
(comida/racao, veterinario, sofá, declaracoes de amor, silencio, inicio da fala,
apresentacao do canal, misterio dos passos), e a INSERE no inicio da lista de
imagens dessa cena (aumentando a densidade visual). Nao remove nenhuma imagem.

Atualiza tambem os 'at' das cenas afetadas para distribuir incluindo a nova.
"""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = Path(r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia")
SCENES = P / "assets/images/gemini/scenes"

# imagem extra -> cena do roteiro onde o texto casa + posicao (0 = inicio)
MAPA = {
    "apresentacao_do_canal_scene.jpg":      ("s0", 0),
    "o_inicio_da_fala_scene.jpg":           ("s1", 0),
    "o_inicio_da_fala_scene_b.jpg":         ("s1", 1),
    "reclamacoes_sobre_a_racao_scene.jpg":  ("s10", 0),
    "reclamacoes_sobre_a_racao_scene_b.jpg":("s10", 2),
    "o_misterio_dos_pssios_scene.jpg":      ("s3", 0),
    "o_misterio_dos_pssios_scene_b.jpg":    ("s3", 2),
    "o_terror_do_veterinario_scene.jpg":    ("s7", 0),
    "o_terror_do_veterinario_scene_b.jpg":  ("s7", 2),
    "a_verdade_sobre_o_sofa_scene.jpg":     ("s5", 0),
    "a_verdade_sobre_o_sofa_scene_b.jpg":   ("s5", 2),
    "declaracoes_de_amor_scene.jpg":        ("s13", 0),
    "declaracoes_de_amor_scene_b.jpg":      ("s13", 2),
    "a_volta_ao_silencio_scene.jpg":        ("s15", 0),
    "a_volta_ao_silencio_scene_b.jpg":      ("s15", 1),
}


def main():
    sc_path = P / "artifacts/scenes.json"
    sc = json.load(open(sc_path, encoding="utf-8"))
    # backup
    (P / "artifacts/scenes.json.bak-extras").write_text(
        json.dumps(sc, ensure_ascii=False, indent=2), encoding="utf-8")

    # agrupa extras por cena
    por_cena = {}
    for img, (sid, pos) in MAPA.items():
        if not (SCENES / img).exists():
            print("FALTA:", img); continue
        por_cena.setdefault(sid, []).append((pos, img))

    alteradas = 0
    for sid, extras in por_cena.items():
        cfg = sc.get(sid, {})
        if not isinstance(cfg, dict):
            continue
        imgs = list(cfg.get("images", []))
        beats = list(cfg.get("beats", []))
        at = list(cfg.get("at", []))
        cams = list(cfg.get("camera", []))
        for pos, img in sorted(extras, key=lambda x: x[0], reverse=True):
            if img in imgs:
                continue
            idx = min(pos, len(imgs))
            imgs.insert(idx, img)
            # beat correspondente: usa o texto do beat mais proximo
            bpos = min(pos, max(0, len(beats) - 1))
            if beats:
                beats.insert(idx, dict(beats[bpos]))
            # tempo: interpolado
            if at and len(at) == len(imgs) - 1:
                t = at[min(pos, len(at)-1)]
                at.insert(idx, t)
            elif at:
                at.insert(min(idx, len(at)), at[min(pos, len(at)-1)])
            if cams:
                cams.insert(idx, cams[min(pos, len(cams)-1)])
        cfg["images"] = imgs
        cfg["beats"] = beats
        if at:
            # remove duplicatas/ordena e garante ultimo <= 0.95
            novos_at = []
            for t in at:
                t = float(t)
                if not novos_at or t > novos_at[-1] + 0.001:
                    novos_at.append(t)
            if novos_at and novos_at[-1] > 0.95:
                novos_at[-1] = 0.95
            cfg["at"] = [round(float(x), 4) for x in novos_at]
        if cams:
            cfg["camera"] = cams
        alteradas += 1
        print(f"{sid}: {len(imgs)} imagens (+{len(extras)})")

    json.dump(sc, open(sc_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("cenas alteradas:", alteradas)


if __name__ == "__main__":
    main()
