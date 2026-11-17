# -*- coding: utf-8 -*-
r"""monitor_duplicatas.py - limpa quase-duplicatas enquanto o batch roda.

O flow_agent_batch.py detecta duplicatas por hash EXATO. A trava
check_imagens_repetidas.py usa distanca perceptual e pode acusar figuras
quase iguais. Este monitor roda em paralelo e, ao detectar um par, move a
imagem MAIS RECENTE para banco de imagens/_duplicatas_<data>/ (preservada,
nunca apagada) para que a trava final passa.

Encerra sozinho quando o batch termina (ou quando as 95 imagens existirem).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"C:\videomaker")
SLUG = "a-caminha-nova-que-ninguem-quer-usar"
SCENES = ROOT / "projects" / SLUG / "assets" / "images" / "gemini" / "scenes"
BACKUP = ROOT / "banco de imagens" / "_duplicatas_2026-11-17"
CHECK = ROOT / "scripts" / "check_imagens_repetidas.py"
LOG = ROOT / "log_limpeza_duplicatas.txt"
PY = r"C:\OpenMontage\.venv\Scripts\python.exe"
TOTAL = 95
INTERVALO = 30


def log(msg: str) -> None:
    linha = f"{datetime.now():%H:%M:%S} {msg}\n"
    with LOG.open("a", encoding="utf-8", errors="replace") as f:
        f.write(linha)
    try:
        print(linha, end="", flush=True)
    except Exception:
        pass


def batch_rodando() -> bool:
    ps = (
        "(Get-CimInstance Win32_Process | Where-Object { "
        "$_.Name -eq 'python.exe' -and $_.CommandLine -like '*flow_agent_batch*' "
        "} | Measure-Object).Count"
    )
    r = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", ps],
        capture_output=True, text=True,
    )
    txt = (r.stdout or "").strip()
    return txt.isdigit() and int(txt) > 0


def pares_duplicados():
    r = subprocess.run(
        [PY, str(CHECK), "--slug", SLUG],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    pares = []
    for linha in (r.stdout or "").splitlines():
        m = re.match(r"\s*-\s+(\S+\.jpg)\s+==\s+(\S+\.jpg)", linha)
        if m:
            pares.append((m.group(1), m.group(2)))
    return pares


def main() -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    log("=== monitor de duplicatas iniciado ===")
    while batch_rodando():
        n = len(list(SCENES.glob("*.jpg")))
        if n >= TOTAL:
            log(f"todas as {TOTAL} imagens presentes; encerrando monitor")
            break
        pares = pares_duplicados()
        if pares:
            log(f"{len(pares)} par(es) duplicado(s) detectado(s) ({n} imagens)")
        for a, b in pares:
            fa, fb = SCENES / a, SCENES / b
            if not fa.exists() or not fb.exists():
                continue
            # O mais recente e o recem-gerado: move ele, mantem o mais antigo.
            vitima = max((fa, fb), key=lambda p: p.stat().st_mtime)
            selo = datetime.now().strftime("%H%M%S")
            dest = BACKUP / f"{vitima.stem}_dup_{selo}.jpg"
            shutil.move(str(vitima), str(dest))
            log(f"  movida: {vitima.name} -> {dest.name}  (par {a} == {b})")
        time.sleep(INTERVALO)
    log("=== batch encerrado; monitor finalizado ===")
    r = subprocess.run(
        [PY, str(CHECK), "--slug", SLUG],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    log("checagem final: " + ("OK" if r.returncode == 0 else "AINDA HA DUPLICATAS"))
    log(f"total de imagens: {len(list(SCENES.glob('*.jpg')))}")


if __name__ == "__main__":
    main()
