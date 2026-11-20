# -*- coding: utf-8 -*-
"""auditoria_idioma.py - confirma que o audio falado esta no idioma do video.

Motivo: o check_texto_idioma so lia script/overlay. O video EN terminava com
frases em PT narradas com voz americana e nenhuma trava pegava.

Faz:
  1. extrai 3 trechos (inicio/meio/fim) do audio narrado
  2. transcreve com Whisper em modo AUTO (sem forcar idioma)
  3. compara o idioma detectado com o esperado
  4. grava artifacts/auditoria_idioma_<lang>.json

Uso: python scripts/auditoria_idioma.py --slug <slug> --lang pt|en|es
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJ = ROOT / "projects"
FF = (ROOT / "ffmpeg" / "bin" / "ffmpeg.exe")
if not FF.exists():
    import shutil
    FF = Path(shutil.which("ffmpeg") or (
        "C:\\Users\\Pires\\AppData\\Local\\Microsoft\\WinGet\\Packages\\"
        "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\"
        "ffmpeg-9.0.2-full_build\\bin\\ffmpeg.exe"))

ESPERADO = {"pt": "pt", "en": "en", "es": "es"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--lang", required=True, choices=["pt", "en", "es"])
    ap.add_argument("--trecho", type=int, default=25, help="segundos por trecho")
    a = ap.parse_args()
    P = PROJ / a.slug
    AUD = P / "assets" / "audio"
    audio = AUD / f"narration_full_{a.lang}.wav"
    if not audio.exists():
        audio = AUD / "final_mix.m4a"
    if not audio.exists():
        print("AUDIO AUSENTE")
        return 1

    import soundfile as sf
    from faster_whisper import WhisperModel
    model = WhisperModel("tiny", device="cpu", compute_type="int8")

    wav16 = P / "artifacts" / "auditoria" / f"_idioma_{a.lang}_16k.wav"
    wav16.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(FF), "-y", "-v", "error", "-i", str(audio),
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav16)],
                   check=True)
    x, sr = sf.read(wav16, dtype="float32")
    total = len(x) / sr
    centros = [min(total / 6, 20), total / 2, max(total - 20, total * 5 / 6)]

    erros, trechos = [], []
    alvo = ESPERADO[a.lang]
    for i, centro in enumerate(centros):
        ini = max(0, int((centro - a.trecho / 2) * sr))
        fim = min(len(x), ini + int(a.trecho * sr))
        seg = x[ini:fim]
        if len(seg) < sr * 3:
            continue
        res, info = model.transcribe(seg, language=None, beam_size=3)
        texto = " ".join(s.text for s in res).strip()
        det = getattr(info, "language", None) or "?"
        trechos.append({"ponto": ["inicio", "meio", "fim"][i], "detectado": det,
                        "texto": texto[:220]})
        if det != alvo:
            erros.append(f"trecho {['inicio','meio','fim'][i]}: audio Falado em "
                         f"'{det}', esperado '{alvo}' -> {texto[:90]!r}")

    out = P / "artifacts" / f"auditoria_idioma_{a.lang}.json"
    dados = {
        "lang": a.lang, "status": "PASS" if not erros else "FALHA",
        "erros": erros, "trechos": trechos,
        "atualizado_em": datetime.now().isoformat(timespec="seconds"),
    }
    out.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"=== AUDITORIA IDIOMA {a.lang.upper()} === status={dados['status']}")
    for t in trechos:
        print(f"  {t['ponto']}: detectado={t['detectado']} | {t['texto'][:90]}")
    for e in erros:
        print("  ERRO:", e)
    print("relatorio:", out)
    return 0 if not erros else 1


if __name__ == "__main__":
    sys.exit(main())
