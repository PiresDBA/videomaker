# -*- coding: utf-8 -*-
"""Gera RELATORIO_YOUTUBE_IDIOMAS.md a partir do disco + historico de envio.

Uso:
  python scripts/relatorio_youtube.py
  python scripts/relatorio_youtube.py --projects-dir E:\\videomaker\\projects
"""
import argparse
import json
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAIZ = HERE.parent
HIST = HERE / ".publish_history_idioma.json"
SAIDA = RAIZ / "RELATORIO_YOUTUBE_IDIOMAS.md"


def carregar(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def norm(s):
    import re
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def titulo_do_script(proj, lang):
    nome = "script.json" if lang == "pt" else f"script_{lang}.json"
    d = carregar(proj / "artifacts" / nome)
    return (d or {}).get("title", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects-dir", default=r"E:\videomaker\projects")
    ap.add_argument("--canal-json", default="",
                    help="JSON gerado por listar_canal.py (auditoria real dos canais)")
    a = ap.parse_args()
    base = Path(a.projects_dir)

    hist = carregar(HIST) or {"done": []}
    vistos = {(e["slug"], e["lang"]): e for e in hist.get("done", [])}

    canais = carregar(a.canal_json) if a.canal_json else {}
    # Casa cada video do canal com o projeto, por sobreposicao de titulo
    # (o titulo do YouTube nao e igual ao do roteiro).
    mapa_canal = {}
    if canais:
        from description_template import find_project_for_title
        for lang, vids in canais.items():
            for v in vids:
                dl = (v.get("default_language") or "")
                if lang == "pt" and dl not in ("pt-BR", "pt-PT", "pt"):
                    continue
                if lang == "en" and not dl.startswith("en"):
                    continue
                if lang == "es" and not dl.startswith("es"):
                    continue
                proj = find_project_for_title(v.get("title", ""), projects_dir=base)
                if proj:
                    mapa_canal.setdefault((proj.name, lang), v["video_id"])

    linhas = ["# Relatório de idiomas e YouTube", ""]
    linhas.append(f"Gerado em {time.strftime('%Y-%m-%d %H:%M')} a partir de `{base}`.")
    if canais:
        linhas.append("Status conferido também na API do YouTube (título/data de publicação).")
    linhas.append("")
    linhas.append("Legenda: **pronto** = MP4 do idioma existe no disco; "
                  "**publicado** = envio confirmado (histórico local ou canal).")
    linhas.append("")

    totais = {}
    for lang in ("pt", "en", "es"):
        prontos, publicados = [], []
        for proj in sorted(base.iterdir()):
            if not proj.is_dir():
                continue
            out = proj / "output"
            if not out.is_dir():
                continue
            nome = proj.name
            mp4 = out / f"{nome}_{lang}.mp4"
            if lang == "pt" and not mp4.is_file():
                alt = out / f"{nome}_pt.mp4"
                if alt.is_file():
                    mp4 = alt
                elif (out / f"{nome}.mp4").is_file():
                    mp4 = out / f"{nome}.mp4"
            if not mp4.is_file():
                continue
            prontos.append(nome)
            e = vistos.get((nome, lang))
            vid = e["video_id"] if (e and e.get("video_id")) else None
            if not vid:
                vid = mapa_canal.get((nome, lang))
            publicados.append((nome, vid))
        totais[lang] = (len(prontos), len([1 for _, v in publicados if v]))

        linhas.append(f"## {lang.upper()} — {totais[lang][1]} publicados de {len(prontos)} prontos")
        linhas.append("")
        linhas.append("| Projeto | Status | Vídeo |")
        linhas.append("|---------|--------|-------|")
        for nome, vid in publicados:
            if vid:
                linhas.append(f"| {nome} | publicado | https://youtu.be/{vid} |")
            else:
                linhas.append(f"| {nome} | **pendente** | — |")
        linhas.append("")

    linhas.insert(6, "| Idioma | Prontos | Publicados | Pendentes |")
    linhas.insert(7, "|--------|---------|------------|-----------|")
    for i, lang in enumerate(("pt", "en", "es")):
        p, pub = totais[lang]
        linhas.insert(8 + i, f"| {lang.upper()} | {p} | {pub} | {p - pub} |")
    linhas.insert(11, "")

    linhas.append("## Observações")
    linhas.append("")
    linhas.append("- A cota da YouTube Data API permite ~6 uploads por canal por dia "
                  "(`videos.insert` ≈ 1600 de 10.000 unidades).")
    linhas.append("- Para publicar, rode `python scripts/loop_upload_idiomas.py` "
                  "uma vez por dia até a coluna **pendentes** zerar.")
    linhas.append("- O título desenhado na capa dos MP4s antigos ainda está em "
                  "português (pendência de re-render — manual §56.6).")

    SAIDA.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("escrito:", SAIDA)
    for lang in ("pt", "en", "es"):
        print(f"  {lang.upper()}: {totais[lang][1]} publicados / {totais[lang][0]} prontos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
