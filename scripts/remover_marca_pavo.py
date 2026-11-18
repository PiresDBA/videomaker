# -*- coding: utf-8 -*-
"""remover_marca_pavo.py - remove a marca 'Pavo' dos clipes copiando textura
do proprio frame (grama/fundo) com mesclagem suave. Sem quadrados visiveis.
"""
from __future__ import annotations
import subprocess, tempfile, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

FF = r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
FP = r"C:\Users\Pires\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffprobe.exe"

# Regiao a corrigir (fracoes da imagem) - cobre o patch verde E a borda branca
X0, Y0, X1, Y1 = 0.84, 0.84, 1.0, 1.0
# De onde copiar a textura: faixa limpa de grama acima (mesma largura)
DY = -0.20


def probe(path):
    import json
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
                        "-of", "json", str(path)], capture_output=True, text=True)
    s = json.loads(r.stdout)["streams"][0]
    return int(s["width"]), int(s["height"]), s.get("r_frame_rate", "30/1"), s.get("nb_frames")


def fix_clip(src: Path, dst: Path):
    w, h, fps, nframes = probe(src)
    x0, y0 = int(X0*w), int(Y0*h)
    x1, y1 = int(X1*w), int(Y1*h)
    dy = int(DY*h)
    print(f"  {src.name}: {w}x{h} fps={fps} frames={nframes} regiao=({x0},{y0})-({x1},{y1})")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        # extrai TODOS os frames como png
        subprocess.run([FF, "-y", "-v", "error", "-i", str(src),
                        str(td / "f_%06d.png")], check=True)
        frames = sorted(td.glob("f_*.png"))
        print(f"  {len(frames)} frames extraidos")

        # mascara numpy: feather suave so nos lados interno/superior;
        # nas bordas direita/inferior do frame ma=1 (cobre a marca ate o canto)
        rw, rh = x1-x0, y1-y0
        feather = 28.0
        ys, xs = np.mgrid[0:rh, 0:rw].astype(np.float32)
        ma = np.clip(np.minimum(xs, ys)/feather, 0.0, 1.0)[:, :, None]

        for i, f in enumerate(frames):
            # carrega e FECHA o arquivo antes de sobrescrever (Windows nao permite
            # gravar sobre um arquivo ainda aberto pelo PIL)
            with Image.open(f) as img:
                arr = np.asarray(img.convert("RGB")).astype(np.float32)

            # regiao fonte: deslocada para cima, com cuidado nos limites
            sy0, sy1 = y0+dy, y1+dy
            if sy0 < 0:  # se saiu do topo, pega de baixo
                sy0, sy1 = min(y1+10, h-1), min(y1+10+rh, h)
            patch = arr[sy0:sy1, x0:x1]
            if patch.shape[0] != rh or patch.shape[1] != rw:
                # redimensiona se necessario
                patch = np.asarray(Image.fromarray(patch.astype(np.uint8)).resize((rw, rh))).astype(np.float32)

            reg = arr[y0:y1, x0:x1]
            misturado = reg*(1-ma) + patch*ma
            arr[y0:y1, x0:x1] = misturado
            # salva em temporario e substitui (evita problema de handle no Windows)
            tmp = f.with_suffix(".tmp.png")
            Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(tmp)
            tmp.replace(f)
            if i == 0:
                Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).save(
                    r"C:\videomaker\projects\e-se-os-cachorros-pudessem-falar-por-um-dia\conferencia\_debug_frame0.png")

        # reencoda mantendo audio se houver
        cmd = [FF, "-y", "-v", "error", "-framerate", fps,
               "-i", str(td / "f_%06d.png")]
        # tenta pegar audio do original
        r = subprocess.run([FF, "-y", "-v", "error", "-i", str(src), "-vn",
                            "-acodec", "copy", str(td / "a.m4a")], capture_output=True)
        if (td / "a.m4a").exists() and (td / "a.m4a").stat().st_size > 1000:
            cmd += ["-i", str(td / "a.m4a")]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "fast",
                "-c:a", "aac", "-b:a", "192k", "-shortest", str(dst)]
        subprocess.run(cmd, check=True)
    print(f"  -> {dst.name} ({dst.stat().st_size} bytes)")


if __name__ == "__main__":
    img = Path(r"C:\videomaker\hyperframes-workspace\assets\images")
    for nome in ["bolinha_limpa.mp4", "osso_voador_limpo.mp4"]:
        src = img / nome
        if src.exists():
            fix_clip(src, img / (nome.replace(".mp4", "_semmarca.mp4")))
    print("OK")
