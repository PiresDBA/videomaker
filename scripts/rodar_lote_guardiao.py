# -*- coding: utf-8 -*-
"""rodar_lote_guardiao.py - Roda o lote do Flow com VIGIA DO CHROME.

Problema: o Chrome do CDP (porta 18800) morre durante geracoes longas e o
lote fica preso esperando imagens que nunca chegam.

Solucao: este guardiao
  1. mantem o Chrome aberto no projeto
  2. roda o flow_agent_batch_on como subprocesso
  3. monitora o CDP a cada 15s
  4. se o Chrome morrer: mata o lote, REABRE o Chrome e RELANCA o lote
     (o lote pula imagens ja existentes -> retoma de onde parou, seguro)
  5. se o lote terminar (rc=0): pronto

Uso: python scripts/rodar_lote_guardiao.py
"""
from __future__ import annotations
import subprocess, sys, time, urllib.request, os, json
from pathlib import Path

PY = sys.executable
SCRIPTS = Path(r"C:\videomaker\scripts")
PROJ = r"C:\videomaker\projects\bulldogue-ingles-frida-e-dachshund-marrom-luna-fic"
PROMPTS = Path(PROJ) / "artifacts/image_prompts.json"
OUTDIR = Path(PROJ) / "assets/images/gemini/scenes"
CDP = "http://127.0.0.1:18800"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PROFILE = r"C:\videomaker\.chrome-gemini-profile"
PROJECT_URL = "https://flow.google.com/project/d43a0933-5310-4951-b511-911f96a6bc22"
LOG = Path(r"C:\videomaker\log_lote_guardiao.txt")


def cdp_ok() -> bool:
    try:
        urllib.request.urlopen(CDP.rstrip("/") + "/json/version", timeout=3)
        return True
    except Exception:
        return False


def abrir_chrome():
    print("  [guardiao] abrindo Chrome no projeto...", flush=True)
    subprocess.Popen([CHROME, "--remote-debugging-port=18800",
                      f"--user-data-dir={PROFILE}", "--no-first-run",
                      "--no-default-browser-check", PROJECT_URL],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if cdp_ok():
            print("  [guardiao] Chrome pronto", flush=True)
            return True
        time.sleep(1)
    return False


def cmd_lote():
    return [PY, str(SCRIPTS / "flow_agent_batch_on.py"),
            "--prompts-file", str(PROMPTS), "--project-dir", PROJ,
            "--out-dir", str(OUTDIR), "--batch-size", "10",
            "--wait", "600", "--pause", "15"]


def main():
    if not cdp_ok() and not abrir_chrome():
        print("ERRO: nao consegui abrir o Chrome", flush=True)
        sys.exit(1)

    reinicios = 0
    MAX_REINICIOS = 8
    while reinicios <= MAX_REINICIOS:
        print(f"\n[guardiao] iniciando lote (reinicio {reinicios})", flush=True)
        proc = subprocess.Popen(cmd_lote())
        morto = False
        while proc.poll() is None:
            time.sleep(15)
            if not cdp_ok():
                print("  [guardiao] CDP MORTO detectado!", flush=True)
                morto = True
                break
        if proc.poll() == 0 and not morto:
            # CONFERIR se realmente gerou todas: o script retorna 0 mesmo com
            # imagens faltando. Conta .jpg no out-dir e relanca se faltarem.
            import re as _re
            sc = Path(PROJ) / "artifacts/scenes.json"
            total = 0
            if sc.exists():
                dados = json.loads(sc.read_text(encoding="utf-8"))
                total = sum(1 for k, v in dados.items() if k.startswith("s")
                            for i in v.get("images", []) if not i.endswith(".mp4"))
            prontas = len(list(OUTDIR.glob("*.jpg")))
            faltam = total - prontas
            print(f"[guardiao] ./ conferencia: {prontas}/{total} jpg, faltam {faltam}", flush=True)
            if faltam <= 0:
                print("[guardiao] LOTE CONCLUIDO - todas as imagens prontas", flush=True)
                return 0
            reinicios += 1
            print(f"[guardiao] faltam {faltam} imagens -> relancando ({reinicios}/{MAX_REINICIOS})", flush=True)
            if reinicios > MAX_REINICIOS:
                print("[guardiao] limite de reinicios atingido", flush=True)
                return 3
            if not cdp_ok() and not abrir_chrome():
                return 2
            time.sleep(5)
        if morto:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:
                proc.kill()
            reinicios += 1
            print(f"  [guardiao] reiniciando Chrome + lote ({reinicios}/{MAX_REINICIOS})", flush=True)
            if not abrir_chrome():
                print("  [guardiao] falhou ao abrir Chrome", flush=True)
                return 2
            time.sleep(5)
        else:
            rc = proc.poll()
            print(f"[guardiao] lote terminou rc={rc}", flush=True)
            return rc
    print("[guardiao] limite de reinicios atingido", flush=True)
    return 3


if __name__ == "__main__":
    sys.exit(main())
