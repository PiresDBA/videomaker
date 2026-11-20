# -*- coding: utf-8 -*-
"""finalizar_idioma.py - aplica sonoplastia ao video ja renderizado e gera
o pacote de AVALIACAO. NAO publica nada.

A formula antiga (gerar_capitulo_trilinguo.py) renderiza com o mix 'pelado'
porque nao tinha a fase de sonoplastia. Este script corrige isso SEM
re-renderizar: gera o mix com efeitos e faz mux da faixa de audio no MP4.

Uso:
  python scripts/finalizar_idioma.py --slug <slug> --lang pt|en|es
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJ = ROOT / "projects"

FF = Path(shutil.which("ffmpeg") or (
    "C:\\Users\\Pires\\AppData\\Local\\Microsoft\\WinGet\\Packages\\"
    "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\"
    "ffmpeg-9.0.2-full_build\\bin\\ffmpeg.exe"))


def run(cmd, label, check=True):
    print(f"\n--- {label} ---", flush=True)
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    print(out[-2500:] if len(out) > 2500 else out, flush=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"{label} falhou (rc={r.returncode})")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--lang", required=True, choices=["pt", "en", "es"])
    a = ap.parse_args()
    P = PROJ / a.slug
    AUD = P / "assets" / "audio"

    # 1) sonoplastia (usa obter_efeito_sonoro, sem laser)
    run([sys.executable, str(HERE / "sonoplastia_por_idioma.py"),
         "--lang", a.lang, "--slug", str(P)], f"SONOPLASTIA {a.lang.upper()}")

    sono = AUD / f"final_mix_sonoplastia_{a.lang}.m4a"
    if not sono.exists():
        raise SystemExit("mix sonoplastia nao gerado")
    shutil.copy2(sono, AUD / "final_mix.m4a")
    shutil.copy2(AUD / "final_mix.m4a", P / "final_mix.m4a")
    (AUD / "final_mix.m4a.lang").write_text(a.lang, encoding="ascii")
    print("final_mix.m4a = sonoplastia (Hook vai passar)", flush=True)

    # 2) localizar video renderizado mais recente
    videos = sorted(P.glob("output/*.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not videos:
        raise SystemExit("nenhum MP4 em output/")
    video = videos[0]
    print(f"video renderizado: {video.name}", flush=True)

    # 3) mux: troca so a faixa de audio (sem re-renderizar)
    tmp = P / "output" / f"_mux_{a.lang}.mp4"
    run([str(FF), "-y", "-v", "error", "-i", str(video), "-i", str(sono),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
         "-b:a", "192k", "-shortest", str(tmp)], f"MUX audio {a.lang.upper()}")
    final = P / "output" / f"{a.slug}_{a.lang}.mp4"
    tmp.replace(final)
    print(f"video final: {final.name} ({final.stat().st_size} bytes)", flush=True)

    # 4) validacoes + pacote de avaliacao
    run([sys.executable, str(HERE / "verify_output.py"), "--proj", str(P),
         "--file", str(final)], f"VERIFY {a.lang.upper()}", check=False)
    run([sys.executable, str(HERE / "hook_validator.py"), "--slug", a.slug,
         "--lang", a.lang], f"HOOK {a.lang.upper()}", check=False)
    run([sys.executable, str(HERE / "revisar_entrega.py"), "--slug", a.slug,
         "--lang", a.lang, "--video", str(final)], f"AVALIACAO {a.lang.upper()}",
        check=False)
    print("\n*** NAO PUBLICAR sem aprovacao explicita do usuario. ***", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
