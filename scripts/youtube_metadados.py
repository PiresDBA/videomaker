# -*- coding: utf-8 -*-
"""Corrige metadados ou apaga videos ja publicados, por canal (PT/EN/ES).

Dois modos:
  --apagar      apaga o(s) video(s) do canal (exige --confirmar)
  --atualizar   reescreve titulo/descricao/idioma do video sem reenviar o MP4
                (custa ~50 unidades de cota; reenviar custa ~1600)

O titulo e a descricao vem de artifacts/script_<lang>.json do projeto.

Exemplos:
  # apagar os 3 videos errados do canal ingles
  python scripts/youtube_metadados.py --lang en --ids id1,id2,id3 --apagar --confirmar

  # corrigir titulo/descricao de um video sem reenviar
  python scripts/youtube_metadados.py --lang en --video-id id1 \
      --proj E:\\videomaker\\projects\\<slug> --atualizar
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

CREDS = {
    "pt": (HERE / "client_secret_pt.json", HERE / "youtube_token_pt.json", "pt-BR"),
    "en": (HERE / "client_secret_en.json", HERE / "youtube_token_en.json", "en-US"),
    "es": (HERE / "client_secret_es.json", HERE / "youtube_token_es.json", "es-ES"),
}


def get_service(lang):
    from youtube_upload import get_service as gs
    cs, tk, _ = CREDS[lang]
    if not tk.is_file():
        raise SystemExit(f"ERRO: token do canal {lang.upper()} nao existe: {tk}")
    return gs(cs, tk)


def carregar_metadados(proj, lang):
    """Titulo + descricao localizados do projeto."""
    sys.path.insert(0, str(HERE))
    from description_template import build_description
    import re

    nome = "script.json" if lang == "pt" else f"script_{lang}.json"
    p = Path(proj) / "artifacts" / nome
    if not p.is_file():
        raise SystemExit(f"ERRO: {p} nao existe — sem titulo no idioma, nada a corrigir")
    script = json.loads(p.read_text(encoding="utf-8"))
    titulo = (script.get("title") or "").strip()
    partes = []
    for sec in script.get("sections", []):
        if sec.get("id") in ("s_intro", "s0", "s_outro"):
            continue
        t = re.sub(r"\s+", " ", sec.get("text", "") or "").strip()
        if t:
            partes.append(t)
    hook_index = {"pt": 0, "en": 1, "es": 2}[lang]
    desc = build_description(titulo, partes[:8], hook_index=hook_index, lang=lang)
    return titulo, desc


def apagar(lang, ids):
    svc = get_service(lang)
    for vid in ids:
        try:
            svc.videos().delete(id=vid).execute()
            print(f"  apagado: {vid}")
        except Exception as e:
            print(f"  ERRO ao apagar {vid}: {e}")
    return 0


def atualizar(lang, vid, proj):
    svc = get_service(lang)
    titulo, desc = carregar_metadados(proj, lang)
    code = CREDS[lang][2]
    body = {
        "id": vid,
        "snippet": {
            "title": titulo[:100],
            "description": desc[:5000],
            "categoryId": "24",
            "defaultLanguage": code,
            "defaultAudioLanguage": code,
        },
    }
    r = svc.videos().update(part="snippet", body=body).execute()
    print(f"  atualizado: {vid}")
    print(f"    titulo: {r['snippet']['title']}")
    print(f"    lang: {r['snippet'].get('defaultLanguage')}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=["pt", "en", "es"])
    ap.add_argument("--ids", default="", help="lista de video ids separada por virgula")
    ap.add_argument("--video-id", default="")
    ap.add_argument("--proj", default="", help="pasta do projeto (para --atualizar)")
    ap.add_argument("--apagar", action="store_true")
    ap.add_argument("--atualizar", action="store_true")
    ap.add_argument("--confirmar", action="store_true", help="obrigatorio para apagar")
    a = ap.parse_args()

    if a.apagar:
        if not a.confirmar:
            print("ERRO: apagar exige --confirmar")
            return 1
        ids = [i.strip() for i in a.ids.split(",") if i.strip()]
        if not ids:
            print("ERRO: informe --ids")
            return 1
        return apagar(a.lang, ids)

    if a.atualizar:
        if not (a.video_id and a.proj):
            print("ERRO: --atualizar exige --video-id e --proj")
            return 1
        return atualizar(a.lang, a.video_id, a.proj)

    print("Nada a fazer: use --apagar ou --atualizar")
    return 1


if __name__ == "__main__":
    sys.exit(main())
