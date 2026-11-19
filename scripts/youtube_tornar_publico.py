# -*- coding: utf-8 -*-
"""youtube_tornar_publico.py - Muda um video de private para public via API."""
import argparse, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from youtube_update import get_service


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--client-secret", required=True)
    ap.add_argument("--token", required=True)
    a = ap.parse_args()
    svc = get_service(Path(a.client_secret), Path(a.token))
    body = {"status": {"privacyStatus": "public"}}
    r = svc.videos().update(part="status", body={**body, "id": a.video_id}).execute()
    print(f"OK: {a.video_id} -> public (privacyStatus={r['status']['privacyStatus']})")
    print(f"https://youtu.be/{a.video_id}")


if __name__ == "__main__":
    main()
