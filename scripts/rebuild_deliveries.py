# -*- coding: utf-8 -*-
"""
Reconstroi o JSON global de entregas (projects-deliveries.json) varrendo
todos os projetos em C:\videomaker\projects\*.

Uso:
    python scripts/rebuild_deliveries.py

Gera/atualiza: raiz/projects-deliveries.json
"""
import json
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

PHASES = ["script", "scenes", "music", "images", "narration",
          "timeline", "mix", "compose", "preprocess", "render"]


def slugify(text, max_len=40):
    import unicodedata
    text = unicodedata.normalize("NFKD", text.lower().strip())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    import re
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")[:max_len].strip("-")
    return text or "projeto"


def load_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def video_duration_and_size(video_path):
    try:
        out = subprocess.run(
            [str(Path(r"C:\videomaker\ffmpeg\bin\ffprobe.exe")), "-v", "error",
             "-show_entries", "format=duration,size", "-of", "json", str(video_path)],
            capture_output=True, text=True)
        d = json.loads(out.stdout)
        fmt = d.get("format", {})
        return float(fmt.get("duration", 0) or 0), int(fmt.get("size", 0) or 0)
    except Exception:
        return None, 0


def main():
    projects_dir = ROOT / "projects"
    delivered = []

    if projects_dir.exists():
        for proj_dir in sorted(projects_dir.iterdir()):
            if not proj_dir.is_dir():
                continue
            state_file = proj_dir / "project.json"
            data = load_json(state_file)
            if not data:
                continue

            slug = data.get("slug") or proj_dir.name
            prompt = data.get("prompt", "")
            phases = data.get("phases", {})

            render_rec = phases.get("render", {})
            render_ts = render_rec.get("ts", "")
            video_path = proj_dir / "output" / (slug + ".mp4")

            dur, size = video_duration_and_size(video_path) if video_path.exists() else (None, 0)

            entry = {
                "slug": slug,
                "prompt": prompt,
                "status": "completed",
                "finished_at": render_ts or time.strftime("%Y-%m-%d %H:%M:%S"),
                "elapsed_seconds": None,
                "project_dir": str(proj_dir),
                "video_path": str(video_path),
                "video_exists": video_path.exists(),
                "video_size_bytes": size if video_path.exists() else 0,
                "video_duration_s": dur,
                "publish": {
                    "done": False,
                    "privacy": None,
                    "title": "",
                    "description": "",
                },
                "phases": {},
            }
            for ph in PHASES:
                rec = phases.get(ph)
                if rec:
                    entry["phases"][ph] = {
                        "done": rec.get("done"),
                        "ts": rec.get("ts"),
                    }

            delivered.append(entry)

    out = {"delivered": delivered}
    out_path = ROOT / "projects-deliveries.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Reconstruido {out_path} com {len(delivered)} entrega(s).")


if __name__ == "__main__":
    main()
