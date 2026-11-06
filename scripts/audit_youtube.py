# -*- coding: utf-8 -*-
"""
Auditoria direta do canal no YouTube: lista os videos publicados, mostra o
status de cada um e valida a descricao contra o PADRAO DO CANAL
(scripts/description_template.py).

Com --fix, corrige no YouTube os videos cuja descricao esta fora do padrao,
usando a descricao rica gerada a partir do script.json do projeto.

Uso:
  python scripts/audit_youtube.py                 # auditoria (nao altera nada)
  python scripts/audit_youtube.py --limit 8       # ultimos N videos
  python scripts/audit_youtube.py --fix           # corrige descricoes fora do padrao
  python scripts/audit_youtube.py --fix --dry-run # mostra o que seria corrigido
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from description_template import (  # noqa: E402
    build_description, extract_storyline, find_project_for_title,
    read_script, validate, word_count,
)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]


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
                raise SystemExit("ERRO: client_secret.json nao encontrado em %s" % client_secret)
            print("Abrindo o navegador para autorizar o canal do YouTube...", flush=True)
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def list_uploads(service, limit=100):
    """Lista os videos do proprio canal, mais recentes primeiro."""
    # Descobre o playlist de uploads do canal (UU<channelId>)
    ch = service.channels().list(part="contentDetails,id", mine=True).execute()
    channel = ch["items"][0]
    uploads = channel["contentDetails"]["relatedPlaylists"]["uploads"]

    video_ids = []
    token = None
    while len(video_ids) < limit:
        resp = service.playlistItems().list(
            part="contentDetails",
            playlistId=uploads,
            maxResults=min(50, limit),
            pageToken=token,
        ).execute()
        for pl in resp.get("items", []):
            vid = pl.get("contentDetails", {}).get("videoId")
            if vid:
                video_ids.append(vid)
        token = resp.get("nextPageToken")
        if not token:
            break

    # Detalhes dos videos (em lote de 50)
    out = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        detail = service.videos().list(
            part="snippet,status,contentDetails", id=",".join(batch)).execute()
        out.extend(detail.get("items", []))
    return out


TAGS_PADRAO = [
    "cachorro", "animacao", "infantil", "frida", "luna", "cachorrinho",
    "desenhoanimado", "videoengraçado", "conteúdocriativo", "petspride",
    "familia", "criancas", "cachorroengraçado", "diversão", "aprendizado",
    "pet", "cão", "bully", "dachshund", "história",
]


def enrich_tags(current):
    """Une as tags existentes com o conjunto padrao, sem duplicar."""
    out = []
    seen = set()

    def add(t):
        t = (t or "").strip()
        if not t:
            return
        key = t.lower().replace(" ", "")
        if key in seen:
            return
        seen.add(key)
        out.append(t)

    for t in current or []:
        add(t)
    for t in TAGS_PADRAO:
        add(t)
    return out[:30]


def build_rich_description(item):
    """Descricao rica para um video do YouTube, usando o projeto correspondente."""
    title = item.get("snippet", {}).get("title", "")
    project = find_project_for_title(title)
    if project:
        script = read_script(project)
        if script:
            return build_description(script.get("title", title), extract_storyline(script)), project
    # sem projeto: gera a partir do titulo + resumo do que ja existe
    old = item.get("snippet", {}).get("description", "")
    storyline = []
    for para in old.split("\n\n"):
        para = para.strip()
        if len(para.split()) >= 12 and not para.startswith("#"):
            storyline.append(para)
    return build_description(title, storyline), None


def main():
    # Console Windows: evita erro de encoding em acentos/emoji
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description="Audita (e opcionalmente corrige) as descricoes do canal")
    ap.add_argument("--limit", type=int, default=8, help="quantos videos analisar (padrao: 8)")
    ap.add_argument("--fix", action="store_true", help="corrige no YouTube as descricoes fora do padrao")
    ap.add_argument("--dry-run", action="store_true", help="com --fix, nao grava nada")
    ap.add_argument("--client-secret", default=str(HERE / "client_secret.json"))
    ap.add_argument("--token", default=str(HERE / "youtube_token.json"))
    args = ap.parse_args()

    service = get_service(Path(args.client_secret), Path(args.token))
    videos = list_uploads(service, max(args.limit, 50))

    # ordena por data de publicacao (mais recentes primeiro)
    def published(v):
        return v.get("snippet", {}).get("publishedAt", "")

    videos.sort(key=published, reverse=True)
    videos = videos[:args.limit]

    print("=" * 78)
    print("AUDITORIA DO CANAL - ultimos %d videos" % len(videos))
    print("=" * 78)

    problemas_total = 0
    for i, item in enumerate(videos, 1):
        sn = item.get("snippet", {})
        st = item.get("status", {})
        vid = item.get("id", "")
        title = sn.get("title", "")
        desc = sn.get("description", "")
        wc = word_count(desc)
        issues = validate(desc)

        print("[%d] %s" % (i, title))
        print("    id: %s" % vid)
        print("    publicado: %s | privacy: %s | kids: %s" % (
            sn.get("publishedAt", "?"), st.get("privacyStatus", "?"),
            st.get("selfDeclaredMadeForKids", "?")))
        print("    descricao: %d palavras | tags: %d" % (wc, len(sn.get("tags", []))))
        if issues:
            problemas_total += 1
            print("    PROBLEMAS: %s" % "; ".join(issues))
        else:
            print("    STATUS: conforme o padrao")
        print("-" * 78)

    print("Videos analisados: %d | fora do padrao: %d" % (len(videos), problemas_total))

    if not args.fix:
        if problemas_total:
            print("\nRode com --fix para corrigir no YouTube.")
        return 0

    print("\nCORRIGINDO descricoes fora do padrao...")
    fixed = 0
    for item in videos:
        sn = item.get("snippet", {})
        vid = item.get("id", "")
        desc = sn.get("description", "")
        if not validate(desc):
            continue

        new_desc, project = build_rich_description(item)
        if project:
            print("  %s -> projeto: %s" % (vid, project.name))
        else:
            print("  %s -> sem projeto (descricao gerada do titulo)" % vid)
        new_tags = enrich_tags(sn.get("tags", []))
        print("     %d -> %d palavras | tags %d -> %d"
              % (word_count(desc), word_count(new_desc), len(sn.get("tags", [])), len(new_tags)))

        if args.dry_run:
            continue

        body = {
            "id": vid,
            "snippet": {
                "title": sn.get("title", ""),
                "description": new_desc[:5000],
                "tags": new_tags,
                "categoryId": sn.get("categoryId", "24"),
            },
            "status": {
                "selfDeclaredMadeForKids": st_flag(item),
            },
        }
        service.videos().update(part="snippet,status", body=body).execute()
        fixed += 1
        print("     ATUALIZADO no YouTube")

        # grava o video_id no projeto, para rastreabilidade
        if project:
            pc = project / "project-control.json"
            if pc.is_file():
                try:
                    with open(pc, encoding="utf-8") as f:
                        data = json.load(f)
                    data.setdefault("publish", {})["video_id"] = vid
                    with open(pc, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    print("     (aviso: nao gravei video_id: %s)" % e)

    print("\nCorrigidos: %d%s" % (fixed, " (dry-run: nada foi gravado)" if args.dry_run else ""))
    return 0


def st_flag(item):
    return bool(item.get("status", {}).get("selfDeclaredMadeForKids", True))


if __name__ == "__main__":
    raise SystemExit(main())
