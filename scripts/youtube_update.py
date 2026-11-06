# -*- coding: utf-8 -*-
"""
Atualiza metadados de um video ja enviado ao YouTube (titulo, descricao, tags, thumbnail).
Uso:
  python scripts/youtube_update.py --video-id <ID> --title "..." --description "..." --tags "a,b,c" --thumbnail <caminho.jpg>
"""
import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def get_service(client_secret, token_path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
              "https://www.googleapis.com/auth/youtube.force-ssl"]

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
                raise SystemExit("ERRO: client_secret.json nao encontrado em %s" % client_secret)
            print("Abrindo o navegador para autorizar o canal do YouTube...", flush=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def update_video(service, video_id, title, description, tags, category, thumbnail=None, made_for_kids=False):
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    # Atualizar snippet (titulo, descricao, tags, categoria)
    body = {
        "id": video_id,
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": str(category),
        },
        "status": {
            "selfDeclaredMadeForKids": bool(made_for_kids),
        },
    }
    try:
        service.videos().update(part="snippet,status", body=body).execute()
        print("Metadados atualizados com sucesso.", flush=True)
    except HttpError as e:
        print("ERRO ao atualizar metadados: %s" % e, flush=True)
        raise

    # Atualizar thumbnail
    if thumbnail:
        try:
            service.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail))).execute()
            print("Thumbnail atualizada.", flush=True)
        except HttpError as e:
            print("AVISO: thumbnail falhou (%s). O canal precisa estar verificado por telefone." % e.resp.status, flush=True)


def main():
    ap = argparse.ArgumentParser(description="Atualiza metadados de video no YouTube")
    ap.add_argument("--video-id", required=True, help="ID do video no YouTube")
    ap.add_argument("--title", required=True, help="Novo titulo")
    ap.add_argument("--description", required=True, help="Nova descricao")
    ap.add_argument("--tags", required=True, help="Tags separadas por virgula")
    ap.add_argument("--category", default="24", help="24=Entretenimento, 1=Filmes e Animacao, 22=Pessoas e Blogs")
    ap.add_argument("--thumbnail", default="", help="Caminho da imagem da miniatura")
    ap.add_argument("--made-for-kids", action="store_true", help="marca o video como feito para criancas (COPPA)")
    ap.add_argument("--client-secret", default=str(HERE / "client_secret.json"))
    ap.add_argument("--token", default=str(HERE / "youtube_token.json"))
    a = ap.parse_args()

    tags_list = [t.strip() for t in a.tags.split(",") if t.strip()]
    thumb = Path(a.thumbnail) if a.thumbnail.strip() else None
    if thumb and not thumb.is_file():
        print("AVISO: thumbnail nao encontrada: %s" % thumb, flush=True)
        thumb = None

    service = get_service(Path(a.client_secret), Path(a.token))
    update_video(service, a.video_id, a.title, a.description, tags_list, a.category, thumb, a.made_for_kids)
    print("Concluido para video %s" % a.video_id, flush=True)


if __name__ == "__main__":
    main()
