# -*- coding: utf-8 -*-
"""Lista os videos ja publicados em cada canal (PT/EN/ES) com titulo e inicio
da descricao. Serve de auditoria antes de corrigir metadados.

Uso:
  python scripts/listar_canal.py            # os 3 canais que tiverem token
  python scripts/listar_canal.py --lang en
  python scripts/listar_canal.py --json out.json
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

CREDS = {
    "pt": (HERE / "client_secret_pt.json", HERE / "youtube_token_pt.json"),
    "en": (HERE / "client_secret_en.json", HERE / "youtube_token_en.json"),
    "es": (HERE / "client_secret_es.json", HERE / "youtube_token_es.json"),
}


def service_for(lang):
    from youtube_upload import get_service
    cs, tk = CREDS[lang]
    if lang == "pt" and not tk.exists():
        # canal principal historico
        tk = HERE / "youtube_token.json"
        cs = HERE / "client_secret.json"
    if not tk.exists():
        raise SystemExit(f"ERRO: token do canal {lang} nao existe: {tk}")
    return get_service(cs, tk)


def list_videos(svc):
    out = []
    ch = svc.channels().list(part="contentDetails,snippet", mine=True).execute()
    items = ch.get("items", [])
    if not items:
        return out
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    token = None
    while True:
        pl = svc.playlistItems().list(
            part="snippet,contentDetails", playlistId=uploads,
            maxResults=50, pageToken=token).execute()
        for it in pl.get("items", []):
            s = it["snippet"]
            out.append({
                "video_id": it["contentDetails"]["videoId"],
                "title": s.get("title", ""),
                "description": s.get("description", ""),
                "published_at": s.get("publishedAt", ""),
            })
        token = pl.get("nextPageToken")
        if not token:
            break
    # detalhes (idioma padrao, visualizacoes e duracao)
    for i in range(0, len(out), 50):
        ids = [v["video_id"] for v in out[i:i + 50]]
        d = svc.videos().list(part="snippet,status,statistics,contentDetails",
                              id=",".join(ids)).execute()
        by_id = {v["id"]: v for v in d.get("items", [])}
        for v in out[i:i + 50]:
            full = by_id.get(v["video_id"], {})
            sn = full.get("snippet", {})
            v["default_language"] = sn.get("defaultLanguage")
            v["default_audio_language"] = sn.get("defaultAudioLanguage")
            v["privacy"] = full.get("status", {}).get("privacyStatus")
            v["views"] = int(full.get("statistics", {}).get("viewCount", 0) or 0)
            v["duration_s"] = iso_para_segundos(
                full.get("contentDetails", {}).get("duration", ""))
    return out


def iso_para_segundos(iso):
    """'PT3M31S' -> 211"""
    import re
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = m.groups()
    return int(d or 0) * 86400 + int(h or 0) * 3600 + int(mi or 0) * 60 + int(float(s or 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="", help="pt, en ou es (padrao: todos com token)")
    ap.add_argument("--json", default="", help="salva o resultado completo nesse arquivo")
    a = ap.parse_args()

    def tem_token(l):
        cs, tk = CREDS[l]
        if l == "pt" and not tk.exists():
            tk = HERE / "youtube_token.json"
        return tk.exists()

    langs = [a.lang] if a.lang else [l for l in ("pt", "en", "es") if tem_token(l)]
    tudo = {}
    for lang in langs:
        print("=" * 70)
        print("CANAL", lang.upper())
        print("=" * 70)
        try:
            svc = service_for(lang)
            vids = list_videos(svc)
        except SystemExit as e:
            print(e)
            continue
        except Exception as e:
            print("ERRO:", e)
            continue
        tudo[lang] = vids
        print("total de videos:", len(vids))
        for v in vids:
            desc1 = " ".join(v["description"].split())[:120]
            print(f"- {v['video_id']} | {v['title']}")
            print(f"    lang={v['default_language']} audio={v['default_audio_language']} "
                  f"{v['privacy']} | {v.get('views', 0)} views")
            print(f"    desc: {desc1}")
        print()

    if a.json:
        Path(a.json).write_text(json.dumps(tudo, ensure_ascii=False, indent=2), encoding="utf-8")
        print("salvo em", a.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
