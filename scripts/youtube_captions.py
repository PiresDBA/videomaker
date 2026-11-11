# -*- coding: utf-8 -*-
"""
Envio de legendas (captions) para o YouTube via YouTube Data API v3.

Usa captions.insert para adicionar faixas de legenda .srt a um video ja
publicado. Suporta múltiplos idiomas no mesmo video.

Requisitos:
  - scripts/client_secret.json  (OAuth2 do Google Cloud)
  - scripts/youtube_token.json  (token gerado uma vez via youtube_setup.py)
  - google-api-python-client, google-auth-oauthlib, google-auth-httplib2

Uso:
  python scripts/youtube_captions.py --video-id d8n44roJNu4 --lang en --srt assets/subtitles/en/slug.srt
  python scripts/youtube_captions.py --video-id d8n44roJNu4 --lang en --srt ... --lang es --srt ...
  python scripts/youtube_captions.py --proj projects/<slug>  (auto-descobre video_id e srt)

Arquivos alterados pelo script:
  - projects/<slug>/project-control.json  (bloco 'captions' com os captionId)
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

LANG_CODES = {
    "pt": "pt-BR",
    "en": "en-US",
    "es": "es-ES",
}


def get_service(client_secret, token_path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        if not creds or not creds.valid:
            if not client_secret.is_file():
                raise SystemExit(
                    "ERRO: client_secret.json nao encontrado em %s "
                    "(veja o setup no topo de scripts/youtube_upload.py)" % client_secret
                )
            print("Abrindo o navegador para autorizar o canal do YouTube...", flush=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def list_captions(service, video_id):
    """Lista faixas de legenda ja existentes no video."""
    try:
        resp = service.captions().list(part="id,snippet", videoId=video_id).execute()
        return resp.get("items", [])
    except Exception as e:
        print("AVISO: nao foi possível listar captions: %s" % e, flush=True)
        return []


def insert_caption(service, video_id, srt_path, lang, name=None):
    """Envia um arquivo .srt como faixa de legenda para o video."""
    from googleapiclient.http import MediaFileUpload

    srt_path = Path(srt_path)
    if not srt_path.exists():
        print("  ERRO: arquivo de legenda nao encontrado: %s" % srt_path, flush=True)
        return None

    # Verifica se ja existe uma legenda para esse idioma
    existing = list_captions(service, video_id)
    for cap in existing:
        snip = cap.get("snippet", {})
        if snip.get("language") == LANG_CODES.get(lang, lang):
            print("  ja existe legenda %s (id=%s), pulando." % (lang, cap["id"]), flush=True)
            return cap["id"]

    body = {
        "snippet": {
            "videoId": video_id,
            "language": LANG_CODES.get(lang, lang),
            "name": name or "%s legendas" % lang.upper(),
            "isDraft": False,
        }
    }

    media = MediaFileUpload(str(srt_path), mimetype="text/caption", resumable=True)
    try:
        resp = service.captions().insert(
            part="snippet", body=body, media_body=media
        ).execute()
        print("  legenda %s enviada (id=%s)." % (lang, resp["id"]), flush=True)
        return resp["id"]
    except Exception as e:
        print("  ERRO ao enviar legenda %s: %s" % (lang, e), flush=True)
        return None


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def save_json(p, d):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser(description="Envia legendas .srt para o YouTube")
    ap.add_argument("--video-id", help="ID do video no YouTube")
    ap.add_argument("--proj", default=None, help="pasta do projeto (auto-descobre video_id e srt)")
    ap.add_argument("--lang", action="append", help="idioma da legenda (pt,en,es). Pode repetir.")
    ap.add_argument("--srt", action="append", help="caminho do arquivo .str. Deve casar com --lang na ordem.")
    ap.add_argument("--client-secret", default=str(HERE / "client_secret.json"))
    ap.add_argument("--token", default=str(HERE / "youtube_token.json"))
    args = ap.parse_args()

    video_id = args.video_id
    proj_dir = None

    if args.proj:
        proj_dir = Path(args.proj)
        ctrl = proj_dir / "project-control.json"
        if ctrl.exists():
            try:
                c = load_json(ctrl)
                video_id = video_id or c.get("publish", {}).get("video_id")
            except Exception:
                pass

    if not video_id:
        print("ERRO: informe --video-id ou --proj com project-control.json contendo video_id.", flush=True)
        return 1

    langs = args.lang or ["en", "es"]
    srts = args.srt or []

    if proj_dir and not srts:
        # Auto-descobre arquivos .srt por idioma
        srts = []
        for lang in langs:
            srt = proj_dir / "assets" / "subtitles" / lang / f"{proj_dir.name}.srt"
            srts.append(str(srt) if srt.exists() else "")

    if len(srts) < len(langs):
        srts = srts + [""] * (len(langs) - len(srts))

    service = get_service(Path(args.client_secret), Path(args.token))

    caption_ids = {}
    for lang, srt in zip(langs, srts):
        if not srt:
            print("  pulado %s (sem arquivo .srt)." % lang, flush=True)
            continue
        cid = insert_caption(service, video_id, srt, lang)
        if cid:
            caption_ids[lang] = cid

    # Grava no project-control.json
    if proj_dir:
        ctrl = proj_dir / "project-control.json"
        if ctrl.exists():
            c = load_json(ctrl)
            c.setdefault("publish", {})["captions"] = caption_ids
            save_json(ctrl, c)
            print("  caption IDs gravados em project-control.json", flush=True)

    print("  Concluido: %d legenda(s) enviada(s)." % len(caption_ids), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
