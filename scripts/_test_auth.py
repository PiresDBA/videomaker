import sys
from pathlib import Path
sys.path.insert(0, r"C:\videomaker\scripts")
sys.stdout.reconfigure(encoding="utf-8")
from youtube_upload import get_service
for lang in ("pt", "en", "es"):
    try:
        s = get_service(Path(rf"C:\videomaker\scripts\client_secret_{lang}.json"),
                        Path(rf"C:\videomaker\scripts\youtube_token_{lang}.json"))
        r = s.channels().list(part="snippet", mine=True).execute()
        print(lang, "AUTENTICADO:", [i["snippet"]["title"] for i in r["items"]])
    except Exception as e:
        print(lang, "ERRO:", type(e).__name__, str(e)[:250])
