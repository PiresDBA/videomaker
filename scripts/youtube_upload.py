# -*- coding: utf-8 -*-
"""
Envio de video para o YouTube (YouTube Data API v3, OAuth2, upload resumable).

Instalacao (uma vez):
  pip install google-api-python-client google-auth-oauthlib google-auth-httplib2

Setup (uma vez):
  1. https://console.cloud.google.com -> criar projeto -> ativar "YouTube Data API v3"
  2. Tela de consentimento OAuth -> tipo "Externo" -> adicionar seu e-mail como "Usuario de teste"
  3. Credenciais -> Criar -> "ID do cliente OAuth" -> tipo "App para computador"
  4. Baixar o JSON e salvar como scripts/client_secret.json
  Na 1a execucao abre o navegador para voce autorizar o canal; o token fica em
  scripts/youtube_token.json (nao compartilhe esses dois arquivos).

Uso:
  python scripts/youtube_upload.py --video projects/meu-slug/output/meu-slug.mp4 \
      --title "Meu video" --description "..." --tags "pixel art,disney" --privacy private
"""
import argparse
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
RETRY_STATUS = (500, 502, 503, 504)


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
                raise SystemExit("ERRO: client_secret.json nao encontrado em %s "
                                 "(veja o setup no topo deste arquivo)" % client_secret)
            print("Abrindo o navegador para autorizar o canal do YouTube...", flush=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def to_utc_iso(local_str):
    """'AAAA-MM-DD HH:MM' (hora local) -> RFC3339 UTC."""
    dt = datetime.strptime(local_str.strip(), "%Y-%m-%d %H:%M")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def upload(service, video, title, description, tags, category, privacy,
           made_for_kids, publish_at=None, thumbnail=None,
           default_language="pt-BR", default_audio_language="pt-BR"):
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": bool(made_for_kids)}
    if publish_at:
        status["privacyStatus"] = "private"   # exigido pela API para agendar
        status["publishAt"] = publish_at
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags,
            "categoryId": str(category),
            "defaultLanguage": default_language,
            "defaultAudioLanguage": default_audio_language,
        },
        "status": status,
    }
    media = MediaFileUpload(str(video), chunksize=8 * 1024 * 1024, resumable=True,
                            mimetype="video/mp4")
    req = service.videos().insert(part="snippet,status", body=body, media_body=media)

    response, retries, last = None, 0, -1
    while response is None:
        try:
            st, response = req.next_chunk()
            if st:
                pct = int(st.progress() * 100)
                if pct != last:
                    print("UPLOAD %d%%" % pct, flush=True)
                    last = pct
        except HttpError as e:
            if e.resp.status in RETRY_STATUS and retries < 8:
                retries += 1
                wait = random.random() * (2 ** retries)
                print("Erro %s, tentando de novo em %.1fs (%d/8)" % (e.resp.status, wait, retries), flush=True)
                time.sleep(wait)
            else:
                raise
    vid = response["id"]
    print("UPLOAD 100%", flush=True)

    if thumbnail:
        try:
            service.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumbnail))).execute()
            print("Thumbnail enviada.", flush=True)
        except HttpError as e:
            print("AVISO: thumbnail falhou (%s). O canal precisa estar verificado por telefone." % e.resp.status, flush=True)
    return vid


def main():
    ap = argparse.ArgumentParser(description="Envia um MP4 para o YouTube")
    ap.add_argument("--video", required=True)
    ap.add_argument("--title", default="", help="titulo (default: nome do arquivo ou do projeto)")
    ap.add_argument("--description", default="", help="descricao (default: gerada automaticamente com IA, sem promocao paga, PT-BR, infantil)")
    ap.add_argument("--tags", default="cachorro,animacao,infantil,frida,luna,cachorrinho,desenhoanimado,videoengraçado,conteúdocriativo,petspride,familia,criancas,cachorroengraçado,diversão,aprendizado", help="tags separadas por virgula")
    ap.add_argument("--category", default="24", help="22=Pessoas e blogs, 24=Entretenimento, 1=Filmes/Animacao")
    ap.add_argument("--privacy", default="public", choices=["private", "unlisted", "public"])
    ap.add_argument("--made-for-kids", action="store_true", default=True, help="marca como feito para criancas (padrao: sim)")
    ap.add_argument("--nao-kids", action="store_true", help="desativa o modo feito para criancas")
    ap.add_argument("--publish-at", default="", help="'AAAA-MM-DD HH:MM' (hora local); agenda a publicacao")
    ap.add_argument("--thumbnail", default="", help="caminho da thumbnail (default: procura thumb.jpg/thumbnail.jpg na pasta do projeto)")
    ap.add_argument("--default-language", default="pt-BR", help="idioma padrao do video (padrao: pt-BR)")
    ap.add_argument("--default-audio-language", default="pt-BR", help="idioma do audio/narracao (padrao: pt-BR)")
    ap.add_argument("--client-secret", default=str(HERE / "client_secret.json"))
    ap.add_argument("--token", default=str(HERE / "youtube_token.json"))
    a = ap.parse_args()

    video = Path(a.video)
    if not video.is_file():
        print("ERRO: video nao encontrado: %s" % video)
        return 1

    # Título: usa --title, senão tenta ler do projeto, senão nome do arquivo
    title = a.title.strip()
    if not title:
        # tenta ler do artifacts/script.json na mesma arvore do projeto
        proj_dir = video.parent.parent  # projects/<slug>/output -> projects/<slug>
        script_json = proj_dir / "artifacts" / "script.json"
        if script_json.is_file():
            try:
                import json
                title = json.load(open(script_json, encoding="utf-8")).get("title", "") or ""
            except Exception:
                title = ""
    if not title:
        title = video.stem.replace("-", " ").title()

    # Descricao: usa --description, senão gera automatica no PADRAO DO CANAL
    # (scripts/description_template.py — fonte unica da verdade).
    desc = a.description.strip()
    if not desc:
        from description_template import build_description, extract_storyline, read_script

        proj_dir = video.parent.parent  # projects/<slug>/output -> projects/<slug>
        script = read_script(proj_dir)
        if script:
            desc = build_description(script.get("title", title), extract_storyline(script))
        if not desc.strip():
            # fallback: sem script.json, gera a partir do titulo
            desc = build_description(title, [])

    # Tags
    tags = [t.strip() for t in a.tags.split(",") if t.strip()]

    # Made for kids: default True, --nao-kids desativa
    made_for_kids = bool(a.made_for_kids) and not a.nao_kids

    # Idiomas
    default_language = a.default_language or "pt-BR"
    default_audio_language = a.default_audio_language or "pt-BR"

    publish_at = None
    if a.publish_at.strip():
        try:
            publish_at = to_utc_iso(a.publish_at)
        except ValueError:
            print("ERRO: --publish-at deve ser 'AAAA-MM-DD HH:MM'")
            return 1

    # Thumbnail: usa --thumbnail, senão procura thumb.jpg / thumbnail.jpg na pasta do projeto
    thumb = None
    thumb_arg = a.thumbnail.strip()
    if thumb_arg:
        t = Path(thumb_arg)
        if t.is_file():
            thumb = t
        else:
            print("AVISO: thumbnail nao encontrada, ignorando: %s" % t)
    else:
        proj_dir = video.parent.parent
        for nome in ("thumb.jpg", "thumbnail.jpg", "thumb.png", "thumbnail.png"):
            cand = proj_dir / nome
            if cand.is_file():
                thumb = cand
                break
        if not thumb:
            # tenta primeira imagem da cena
            img_dir = proj_dir / "assets" / "images" / "gemini" / "scenes"
            if img_dir.exists():
                imgs = sorted(img_dir.glob("*.jpg"))
                if imgs:
                    thumb = imgs[0]
    if thumb:
        print(f"== Thumbnail: {thumb}", flush=True)
    else:
        print("== Thumbnail: nenhuma encontrada (publicara sem miniatura personalizada)", flush=True)

    try:
        from googleapiclient.errors import HttpError
    except ImportError:
        print("ERRO: instale com: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        return 1

    print("Enviando: %s (%.1f MB)" % (video.name, video.stat().st_size / 1e6), flush=True)
    try:
        service = get_service(Path(a.client_secret), Path(a.token))
        vid = upload(service, video, title, desc, tags, a.category,
                     a.privacy, made_for_kids, publish_at, thumb,
                     default_language, default_audio_language)
    except HttpError as e:
        msg = str(e)
        print("ERRO da API do YouTube: %s" % msg)
        if "quotaExceeded" in msg:
            print("Cota diaria da API estourada (cada upload custa ~1600 de 10000). Tente amanha.")
        return 1
    print("OK: https://youtu.be/%s" % vid)
    print("Studio: https://studio.youtube.com/video/%s/edit" % vid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
