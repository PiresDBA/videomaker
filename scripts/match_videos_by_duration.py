# -*- coding: utf-8 -*-
"""
Casa os videos do canal com os projetos locais usando a DURACAO do video
(fingerprint forte) + similaridade de titulo.

A duracao do mp4 renderizado (ffprobe) e a duracao publicada no YouTube
(contentDetails.duration) devem ser praticamente iguais. Quando a duracao
bate (tolerancia de 2s), a association e confiavel mesmo que o titulo do
YouTube tenha sido reescrito.

Uso:
  python scripts/match_videos_by_duration.py            # mostra o pareamento
  python scripts/match_videos_by_duration.py --apply    # grava video_id nos projetos
  python scripts/match_videos_by_duration.py --apply --threshold 3
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from description_template import _fold, _tokens  # noqa: E402

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]


def get_service(client_secret, token_path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
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
                raise SystemExit("ERRO: client_secret.json nao encontrado")
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def list_channel_videos(service):
    ch = service.channels().list(part="contentDetails", mine=True).execute()
    uploads = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    ids = []
    token = None
    while True:
        resp = service.playlistItems().list(
            part="contentDetails", playlistId=uploads,
            maxResults=50, pageToken=token).execute()
        for pl in resp.get("items", []):
            vid = pl.get("contentDetails", {}).get("videoId")
            if vid:
                ids.append(vid)
        token = resp.get("nextPageToken")
        if not token:
            break

    out = []
    for i in range(0, len(ids), 50):
        det = service.videos().list(
            part="snippet,contentDetails,status", id=",".join(ids[i:i + 50])).execute()
        out.extend(det.get("items", []))
    return out


def parse_iso_duration(text):
    """'PT2M30S' -> 150.0 segundos."""
    text = (text or "").strip()
    if not text.startswith("PT"):
        return None
    total = 0.0
    num = ""
    for ch in text[2:]:
        if ch.isdigit() or ch == ".":
            num += ch
        else:
            try:
                value = float(num)
            except ValueError:
                value = 0.0
            num = ""
            if ch == "H":
                total += value * 3600
            elif ch == "M":
                total += value * 60
            elif ch == "S":
                total += value
    return total or None


def ffprobe_duration(path):
    try:
        res = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", str(path)],
            capture_output=True, text=True, timeout=120)
        data = json.loads(res.stdout or "{}")
        return float(data.get("format", {}).get("duration") or 0) or None
    except Exception:
        return None


def project_video_path(project_dir):
    pc = project_dir / "project-control.json"
    if not pc.is_file():
        return None
    try:
        with open(pc, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    video = data.get("video") or {}
    path = video.get("path") if isinstance(video, dict) else None
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        # tenta o arquivo padrao na pasta output
        guess = project_dir / "output" / ("%s.mp4" % project_dir.name)
        return guess if guess.is_file() else None
    return p


def title_score(a, b):
    ta, tb = set(_tokens(a)), set(_tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / float(len(ta | tb))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="grava video_id nos projetos")
    ap.add_argument("--threshold", type=float, default=2.0, help="tolerancia em segundos")
    ap.add_argument("--client-secret", default=str(HERE / "client_secret.json"))
    ap.add_argument("--token", default=str(HERE / "youtube_token.json"))
    ap.add_argument("--projects", default=str(HERE.parent / "projects"))
    args = ap.parse_args()

    service = get_service(Path(args.client_secret), Path(args.token))
    videos = list_channel_videos(service)

    root = Path(args.projects)
    projects = []
    for item in sorted(root.iterdir()):
        if not item.is_dir():
            continue
        vp = project_video_path(item)
        if not vp:
            continue
        dur = ffprobe_duration(vp)
        if dur:
            projects.append((item, dur, vp))
    print("Projetos com video renderizado: %d" % len(projects))

    matches = []
    unmatched_videos = []
    used_projects = set()
    for v in videos:
        vd = parse_iso_duration(v.get("contentDetails", {}).get("duration"))
        title = v.get("snippet", {}).get("title", "")
        if not vd:
            continue
        best = None
        for item, dur, vp in projects:
            if item.name in used_projects:
                continue
            delta = abs(dur - vd)
            if delta <= args.threshold:
                score = title_score(title, item.name)
                if best is None or score > best[0]:
                    best = (score, item, dur, delta)
        if best:
            score, item, dur, delta = best
            used_projects.add(item.name)
            matches.append((v["id"], title, item.name, dur, vd, delta, score))
        else:
            unmatched_videos.append((v["id"], title, vd))

    print("\n%d video(s) casados por duracao:\n" % len(matches))
    for vid, title, proj, dur, vd, delta, score in matches:
        print("  %s | %s" % (vid, title))
        print("      projeto: %s" % proj)
        print("      duracao local %.1fs vs youtube %.1fs (delta %.1fs) | titulo %.0f%%"
              % (dur, vd, delta, score * 100))

    if unmatched_videos:
        print("\nVideos sem projeto correspondente:")
        for vid, title, vd in unmatched_videos:
            print("  %s | %s | %.1fs" % (vid, title, vd))

    if not args.apply:
        print("\n(use --apply para gravar video_id nos project-control.json)")
        return 0

    written = 0
    for vid, title, proj, dur, vd, delta, score in matches:
        pc = root / proj / "project-control.json"
        if not pc.is_file():
            continue
        with open(pc, encoding="utf-8") as f:
            data = json.load(f)
        publish = data.setdefault("publish", {})
        if publish.get("video_id") and publish.get("video_id") != vid:
            print("  AVISO %s ja tinha video_id %s (mantido)" % (proj, publish.get("video_id")))
            continue
        publish["video_id"] = vid
        publish["youtube_duration_s"] = round(vd, 1)
        publish["local_duration_s"] = round(dur, 1)
        with open(pc, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        written += 1
        print("  gravado %s -> %s" % (proj, vid))
    print("\nvideo_id gravados: %d" % written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
