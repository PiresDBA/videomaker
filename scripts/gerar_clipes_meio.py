# -*- coding: utf-8 -*-
"""gerar_clipes_meio.py - Gera os 3 clipes de 8 segundos do MEIO do video.

REGRA DO USUARIO (MANUAL §72):
  - clipes de EXATAMENTE 8 SEGUNDOS (escrito no prompt)
  - @[Frida] e @[Luna] sempre que citar os personagens
  - tema derivado do ROTEIRO DESTE video (nunca copiado de outro)
  - via Google Flow, modo Video (3 videos/dia)

Uso:
  python scripts/gerar_clipes_meio.py --slug <slug>
  python scripts/gerar_clipes_meio.py --slug <slug> --minutos "2,5,7"
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
PY = sys.executable


def norm(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def ref(t):
    """Aplica @[Frida]/@[Luna] (arro + colchete)."""
    t = re.sub(r"@?\[?(?:Frid[oó]ca|Frida)\]?", "@[Frida]", t, flags=re.I)
    t = re.sub(r"@?\[?(?:Luninha|Luna)\]?", "@[Luna]", t, flags=re.I)
    return t


def escolher_cenas(script, minutos):
    """Escolhe 1 cena do roteiro proxima a cada minuto pedido."""
    secs = script.get("sections", [])
    # distribui as secoes de desenvolvimento entre os minutos
    dev = [s for s in secs if s.get("id", "").startswith("s") and
           s.get("id") not in ("s_intro", "s0", "s_final", "s_outro")]
    if not dev:
        return []
    escolhidas = []
    for m in minutos:
        # posicao proporcional pelo minuto (assume ~10min de video, ajustavel)
        idx = min(len(dev) - 1, max(0, int((m / 10.0) * len(dev))))
        escolhidas.append((m, dev[idx]))
    return escolhidas


def make_prompt(s, minuto):
    """Monta prompt de VIDEO de 8s com referencias de personagem."""
    texto = ref(s.get("text", "")[:400])
    return (
        "Gere um VIDEO ANIMADO de EXATAMENTE 8 SEGUNDOS (8s), 16:9, estilo "
        "desenho 3D cinematografico para criancas, mesmo traco/textura/paleta "
        "da imagem de referencia. "
        "PERSONAGENS (use as referencias salvas): @[Frida] = buldogue inglesa "
        "fawn grande e compacta com colar de perolas; @[Luna] = dachshund/"
        "salsicha marrom-chocolate comprida e baixa com coleira dourada. "
        "Mantenha @[Frida] e @[Luna] EXATAMENTE iguais em todos os quadros "
        "(mesmas racas, cores, rostos e tamanhos). "
        "CENA (do roteiro deste video, minuto ~%d): %s "
        "Sem humanos, sem outros cachorros, sem texto, sem marcas, sem mudanca "
        "de personagens. DURACAO: 8 SEGUNDOS." % (minuto, texto)
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--minutos", default="2,5,7")
    ap.add_argument("--ref", default=r"C:\videomaker\scripts\reference\frida_luna_reference.jpg")
    a = ap.parse_args()

    P = Path(r"C:\videomaker\projects") / a.slug
    script = json.loads((P / "artifacts/script.json").read_text(encoding="utf-8"))
    outdir = P / "assets/images/gemini/scenes"
    outdir.mkdir(parents=True, exist_ok=True)
    minutos = [int(x) for x in a.minutos.split(",")]
    cenas = escolher_cenas(script, minutos)

    print("=== CLIPES DO MEIO (8s cada) ===")
    for i, (minuto, cena) in enumerate(cenas, 1):
        prompt = make_prompt(cena, minuto)
        nome = f"clipe_meio_{i}_{minuto}min"
        salvo = outdir / f"{nome}.mp4"
        print(f"\n[{i}/{len(cenas)}] {nome} (minuto {minuto}) cena={cena['id']}")
        print(f"  prompt: {len(prompt)} chars | '8 SEGUNDOS' no prompt: {'8 SEGUNDOS' in prompt}")
        cmd = [PY, str(HERE / "gerar_video_flow.py"),
               "--prompt", prompt, "--ref", a.ref, "--save", str(salvo)]
        r = subprocess.run(cmd)
        print(f"  rc={r.returncode} salvo={salvo.exists()}")


if __name__ == "__main__":
    main()
