# -*- coding: utf-8 -*-
"""gerar_prompts_videos.py - Gera o PROMPTS_VIDEOS.md automaticamente a partir
do roteiro (script.json). RODA LOGO APOS O ROTEIRO, antes das imagens,
para o usuario poder gerar os 5 videos no Flow em paralelo.

REGRA DO USUARIO (CONTRATO):
  - todo prompt de video: estilo CINEMATOGRAFICO 3D DISNEY/PIXAR + referencia
  - usar @Frida e @Luna (arro, sem colchetes)
  - 8 SEGUNDOS explicito, 16:9, Veo 3.1 Lite, qualidade baixa, export 720p
  - 5 videos: intro + 3 meio (2/5/7 min) + final subscribe
  - sonoplastia obrigatoria (gerada pela narracao no pipeline)
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent


def ref(t):
    """Aplica @Frida/@Luna e repara mojibake do roteiro."""
    import unicodedata
    t = t or ""
    # repara mojibake tipico: tenta codificar cp1252 e decodificar utf-8
    for _ in range(2):
        try:
            cand = t.encode("cp1252").decode("utf-8")
            if cand != t:
                t = cand
        except Exception:
            break
    # limpa sujeira restante
    t = t.replace("'", "").replace("\u2019", "")
    t = t.replace("\ufffd", "").replace("\u06fd", "").replace("\u065f", "")
    t = re.sub(r"\?(?=[a-zA-Z])", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = unicodedata.normalize("NFKD", t)
    t = re.sub(r"@?\[?(?:Frid[oó]ca|Frida)\]?", "@Frida", t, flags=re.I)
    t = re.sub(r"@?\[?(?:Luninha|Luna)\]?", "@Luna", t, flags=re.I)
    return t


ESTILO = ("Video animado de EXATAMENTE 8 SEGUNDOS, 16:9, ESTILO CINEMATOGRAFICO "
          "3D estilo Disney/Pixar, animacao fofa de alta qualidade para criancas, "
          "traco suave, luz cinematografica, personagens expressivos. "
          "Use @Frida (buldogue inglesa fawn, grande e compacta, colar de "
          "perolas) e @Luna (dachshund marrom-chocolate comprida e baixa, "
          "coleira dourada), EXATAMENTE como na imagem de referencia anexada, "
          "mesmos rostos, racas, cores e tamanhos em todos os quadros. ")
REGRAS = (" Sem humanos, sem outros cachorros, sem texto, sem letras, sem "
          "marcas. DURACAO: 8 SEGUNDOS.")


def escolher(script, minutos, proj=None):
    """Escolhe a cena FALADA em cada minuto usando o timeline real.

    REGRA (2026-11-19): o metodo antigo usava indice proporcional
    `round((m/10)*(len(dev)-1))` e dava OFF-BY-ONE (2min->s4 em vez de s3,
    etc). Os clipes gerados mostravam a cena seguinte e a narração falava a
    anterior. Agora lemos artifacts/timeline.json e pegamos a cena cujo
    intervalo contem o minuto.
    """
    secs = script.get("sections", [])
    dev = [s for s in secs if re.match(r"^s\d+$", s.get("id", ""))]
    tl = None
    if proj:
        tp = Path(proj) / "artifacts" / "timeline.json"
        if tp.exists():
            tl = json.loads(tp.read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in secs}
    out = []
    for m in minutos:
        cena = None
        if tl:
            t = m * 60.0
            for c in tl.get("timeline", []):
                if c.get("start", 0) <= t <= c.get("end", 0):
                    cena = by_id.get(c["id"])
                    break
        if cena is None:
            idx = min(len(dev) - 1, max(0, round((m / 10.0) * (len(dev) - 1)))) if dev else 0
            cena = dev[idx] if dev else secs[0]
        out.append((m, cena))
    return out


def main(slug):
    P = Path(r"C:\videomaker\projects") / slug
    script = json.loads((P / "artifacts/script.json").read_text(encoding="utf-8"))
    titulo = script.get("title", slug)
    secs = {s["id"]: s for s in script["sections"]}
    meio = escolher(script, [2, 5, 7], P)

    blocos = []

    def add(nome, minuto, cena_id, texto):
        prompt = ESTILO + "CENA (" + ref(texto) + ")." + REGRAS
        blocos.append((nome, minuto, cena_id, prompt))

    add("intro_8s.mp4", 0, "s0", secs.get("s0", {}).get("text", "Boas-vindas"))
    for i, (m, cena) in enumerate(meio, 1):
        add(f"meio_{m}min.mp4", m, cena["id"], cena.get("text", ""))
    add("final_subscribe.mp4", 9, "s_outro",
        secs.get("s_outro", {}).get("text", "Inscreva-se"))

    L = [
        f"# PROMPTS DOS 5 VIDEOS - {titulo}",
        "",
        "Gerado automaticamente pelo pipeline (logo apos o roteiro).",
        "Gere os 5 manualmente no Google Flow ENQUANTO o pipeline gera as fotos.",
        "",
        "## ONDE SALVAR",
        "",
        f"C:\\videomaker\\projects\\{slug}\\assets\\images\\gemini\\scenes\\",
        "",
        "## CONFIG (TODOS)",
        "Veo 3.1 Lite - qualidade BAIXA (10 creditos) - 8 segundos - 16:9 - export 720p",
        "Anexar referencia: C:\\videomaker\\scripts\\reference\\frida_luna_reference.jpg",
        "ESTILO: cinematografico 3D Disney/Pixar. Usar @Frida e @Luna (arro, sem colchetes).",
        "",
    ]
    for i, (nome, minuto, cena_id, prompt) in enumerate(blocos, 1):
        L += [f"## {i}. {nome} (minuto {minuto}, cena {cena_id})", "",
              "```", prompt, "```", ""]
    L += ["## DEPOIS DE SALVAR",
          "Me avise no chat. O pipeline faz a compilacao final com sonoplastia "
          "(gerada pela narracao) + efeitos de fundo + blur/foco."]

    dest = P / "PROMPTS_VIDEOS.md"
    dest.write_text("\n".join(L), encoding="utf-8")
    print(f"OK: {dest} ({len(blocos)} prompts)")
    return dest


if __name__ == "__main__":
    slug = sys.argv[1] if len(sys.argv) > 1 else \
        "bulldogue-ingles-frida-e-dachshund-marrom-luna-fic"
    main(slug)
