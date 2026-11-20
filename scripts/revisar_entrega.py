# -*- coding: utf-8 -*-
"""revisar_entrega.py - pacote de AVALIACAO (nunca publica).

Uso:
  python scripts/revisar_entrega.py --slug <slug> --lang pt|en|es

Gera em <proj>/conferencia/revisao_<lang>.jpg um mosaico de quadros do video
(incluindo os instantes problematicos) e imprime:
  - textos de tela do idioma (overlay s0)
  - relatorio da sonoplastia (sons usados, contagem, zero laser)
  - imagens suspeitas (folha de referencia)
  - LEMBRETE: NAO publicar sem aprovacao do usuario.
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJ = ROOT / "projects"

FF = Path(shutil.which("ffmpeg") or (
    "C:\\Users\\Pires\\AppData\\Local\\Microsoft\\WinGet\\Packages\\"
    "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\"
    "ffmpeg-9.0.2-full_build\\bin\\ffmpeg.exe"))


def duracao(video):
    r = subprocess.run([str(FF), "-i", str(video)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    import re
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr or "")
    if not m:
        return 0.0
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def quadro(video, t, out):
    subprocess.run([str(FF), "-y", "-v", "error", "-ss", str(int(t)), "-i",
                    str(video), "-frames:v", "1", "-q:v", "3", str(out)],
                   capture_output=True)
    return out.exists()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--lang", default="pt", choices=["pt", "en", "es"])
    ap.add_argument("--video", default="")
    a = ap.parse_args()

    P = PROJ / a.slug
    video = Path(a.video) if a.video else P / "output" / f"{a.slug}.mp4"
    if a.lang != "pt":
        alt = P / "output" / f"{a.slug}_{a.lang}.mp4"
        if alt.exists():
            video = alt
    if not video.exists():
        print(f"VIDEO AUSENTE: {video}")
        return 1

    dur = duracao(video)
    print(f"=== ENTREGA PARA AVALIACAO — {a.lang.upper()} ===")
    print(f"video: {video}")
    print(f"duracao: {dur:.1f}s")

    # quadros: inicio + a cada ~40s + zona problematica (610-625s) + fim
    tempos = [1.0] + [i * 40.0 for i in range(1, int(dur // 40))]
    tempos += [t for t in (608, 612, 616, 620, 624) if t < dur]
    tempos += [max(0, dur - 6)]
    tempos = sorted(set(round(t, 1) for t in tempos))
    tmp = Path(tempfile.mkdtemp(prefix="revisao_"))
    frames = []
    for i, t in enumerate(tempos):
        f = tmp / f"f_{i:03d}_{int(t)}.jpg"
        if quadro(video, t, f):
            frames.append((t, f))

    try:
        from PIL import Image, ImageDraw
        W, H = 320, 180
        cols = 5
        sheet = Image.new("RGB", (W * cols, H * ((len(frames) + cols - 1) // cols)), (18, 18, 18))
        dr = ImageDraw.Draw(sheet)
        for i, (t, f) in enumerate(frames):
            im = Image.open(f).convert("RGB").resize((W, H))
            x, y = (i % cols) * W, (i // cols) * H
            sheet.paste(im, (x, y))
            dr.rectangle((x, y, x + W, y + 16), fill=(0, 0, 0))
            dr.text((x + 3, y + 2), f"{int(t)//60}:{int(t)%60:02d}", fill=(255, 230, 0))
        out = P / "conferencia" / f"revisao_{a.lang}.jpg"
        out.parent.mkdir(exist_ok=True)
        sheet.save(out, quality=86)
        print(f"mosaico: {out}")
    except Exception as e:
        print("ERRO mosaico:", e)

    # overlay do idioma
    s0 = P / "scenes" / a.lang / "s0.html"
    if s0.exists():
        import re
        txt = s0.read_text(encoding="utf-8", errors="replace")
        badge = re.search(r'class="badge"[^>]*>([^<]+)</div>', txt)
        h2 = re.search(r"<h2[^>]*>([^<]+)</h2>", txt)
        body = re.search(r'class="body"[^>]*>([^<]+)</div>', txt)
        print("overlay badge :", badge.group(1) if badge else "?")
        print("overlay titulo:", h2.group(1) if h2 else "?")
        print("overlay corpo :", body.group(1) if body else "?")
    else:
        print("overlay: AUSENTE (bloqueia publicacao)")

    # sonoplastia
    cues = P / "artifacts" / f"cues_sonoplastia_{a.lang}.json"
    if cues.exists():
        d = json.loads(cues.read_text(encoding="utf-8"))
        c = Counter(x["id"] for x in d)
        lasers = [x for x in d if any(w in x["id"].lower() for w in
                  ("zap", "glitch", "zing", "whistle", "logo_sting", "osso_assobio",
                   "downlifter", "riser", "sub_drop"))]
        print(f"sonoplastia: {len(d)} cues, {len(c)} sons distintos, LASER={len(lasers)}")
        print("sons mais usados:", c.most_common(10))
    else:
        print("sonoplastia: AUSENTE")

    # imagens suspeitas
    sus = []
    imgs = P / "assets/images/gemini/scenes"
    try:
        import numpy as np
        from PIL import Image
        for f in imgs.glob("*.jpg"):
            im = Image.open(f).convert("RGB").resize((120, 68))
            ar = np.asarray(im, dtype=np.float32)
            br = float((ar.min(axis=2) > 200).mean())
            g = np.asarray(im.convert("L"), dtype=np.float32)
            ed = float((np.abs(np.diff(g, axis=1)) > 40).mean())
            if br > 0.60 and ed > 0.055:
                sus.append(f.name)
    except Exception:
        pass
    print("imagens suspeitas (folha de referencia):", sus or "nenhuma")

    print("\n*** NAO PUBLICAR sem aprovacao explicita do usuario. ***")
    return 0


if __name__ == "__main__":
    sys.exit(main())
