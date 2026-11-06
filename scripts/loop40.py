# -*- coding: utf-8 -*-
"""
Loop de 40 pipelines completos (roteiro ate publicar no YouTube publico).

Contrato de unicidade (sem repetir video):
  - Reserva o topico se o slug/prompt/titulo real de QUALQUER video ja existente
    (entrega registrada ou MP4 no disco) casar com o topico.
  - Compara por slug, prompt completo, TITULO/TEMA extraidos do briefing e pelo
    titulo real em artifacts/script.json.
  - Tambem bloqueia near-duplicata por sobreposicao de palavras (>= 85%).
  - Pasta de projeto sem MP4 NAO conta como usada: o pipeline retoma os
    checkpoints existentes em vez de refazer do zero.
  - O pipeline so registra entrega quando o MP4 final existe.

Uso:
  python scripts\\loop40.py              # executa os 40 proximos topicos nao usados
  python scripts\\loop40.py --dry-run    # so mostra o que faria, sem rodar
  python scripts\\loop40.py --audit      # audita contrato e duplicatas
  python scripts\\loop40.py --no-upload  # gera os videos, nao publica
  python scripts\\loop40.py --limit 40 --retries 2
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PIPELINE = HERE / "pipeline.py"
TOPICS = HERE / "topics.txt"
DELIVERIES = ROOT / "projects-deliveries.json"
LOGDIR = ROOT / "logs" / "pipeline40"
PROJECTS = ROOT / "projects"


def slugify(text, max_len=40):
    s = unicodedata.normalize("NFKD", (text or "").lower().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")[:max_len].strip("-") or "projeto"


def repair_mojibake(text):
    """Desfaz UTF-8 lido como cp437/cp850 (ex.: 'est├í' -> 'está')."""
    if not text:
        return ""
    for enc in ("cp437", "cp850"):
        try:
            fixed = text.encode(enc).decode("utf-8")
            if fixed != text:
                return fixed
        except Exception:
            continue
    return text


def norm_ident(text):
    t = repair_mojibake(text or "")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def extract_titles(prompt):
    """Extrai TITULO/TEMA de um briefing longo e o proprio prompt se for curto."""
    p = repair_mojibake(prompt or "")
    out = []
    for label in ("TÍTULO:", "TITULO:", "TEMA:"):
        for m in re.finditer(re.escape(label) + r"\s*([^\n\r]+)", p, re.I):
            out.append(m.group(1).strip())
    if p and "\n" not in p.strip() and len(p) <= 200:
        out.append(p.strip())
    return out


def parse_topic(line):
    """Remove o marcador de data especial (@MM-DD) do inicio do topico."""
    m = re.match(r"^@\d{2}-\d{2}\s+(.*)$", line.strip())
    return m.group(1).strip() if m else line.strip()


def read_topics():
    out = []
    if not TOPICS.exists():
        return out
    for line in TOPICS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(parse_topic(line))
    return out


def load_json_file(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def load_deliveries():
    return load_json_file(DELIVERIES, {"delivered": []})


def projects_with_video():
    """Lista dicts dos projetos que possuem MP4 real em output/."""
    rows = []
    if not PROJECTS.exists():
        return rows
    for d in sorted(PROJECTS.iterdir()):
        if not d.is_dir():
            continue
        out = d / "output"
        mp4s = sorted(out.glob("*.mp4")) if out.exists() else []
        if not mp4s:
            continue
        sc = load_json_file(d / "artifacts" / "script.json")
        pj = load_json_file(d / "project.json")
        rows.append({
            "folder": d.name,
            "slug": slugify(d.name),
            "videos": [m.name for m in mp4s],
            "sizes": [m.stat().st_size for m in mp4s],
            "title": sc.get("title", "") if isinstance(sc, dict) else "",
            "prompt": pj.get("prompt", "") if isinstance(pj, dict) else "",
        })
    return rows


def build_reserved_index():
    """Conjunto de identidades normalizadas que nao podem ser repetidas."""
    idents = set()
    reserved_slugs = set()

    data = load_deliveries()
    for d in data.get("delivered", []):
        slug = d.get("slug") or ""
        if slug:
            reserved_slugs.add(slug)
            idents.add(norm_ident(slug.replace("-", " ")))
        prompt = d.get("prompt") or ""
        if prompt:
            idents.add(norm_ident(prompt))
            idents.update(norm_ident(t) for t in extract_titles(prompt) if t)

    for row in projects_with_video():
        reserved_slugs.add(row["slug"])
        idents.add(norm_ident(row["folder"].replace("-", " ")))
        for v in row["videos"]:
            idents.add(norm_ident(Path(v).stem.replace("-", " ")))
        if row["prompt"]:
            idents.add(norm_ident(row["prompt"]))
            idents.update(norm_ident(t) for t in extract_titles(row["prompt"]) if t)
        if row["title"]:
            idents.add(norm_ident(row["title"]))

    idents.discard("")
    return reserved_slugs, idents


def is_reserved(topic, reserved_slugs, idents):
    slug = slugify(topic)
    if slug in reserved_slugs:
        return True
    n = norm_ident(topic)
    if not n:
        return True
    if n in idents:
        return True
    toks = set(n.split())
    if len(toks) >= 4:
        for ident in idents:
            itoks = set(ident.split())
            if not itoks:
                continue
            if len(toks & itoks) / len(toks) >= 0.85:
                return True
    return False


def selected_topics(limit=40):
    reserved_slugs, idents = build_reserved_index()
    chosen = []
    seen = set()
    for t in read_topics():
        s = slugify(t)
        if not s or s in seen:
            continue
        seen.add(s)
        if is_reserved(t, reserved_slugs, idents):
            continue
        chosen.append(t)
        if len(chosen) >= limit:
            break
    return chosen


def build_cmd(topic, index, total, privacy="public", kids=True):
    title = topic[:100]
    desc = "%s\n\nEpisodio %d de %d - Frida e Luna.\nInscreva-se!" % (topic, index, total)
    tags = "cachorro,animacao,infantil,criancas,familia,desenho animado,pet"
    cmd = [
        sys.executable, str(PIPELINE), "full",
        "--prompt", topic,
        "--publish",
        "--privacy", privacy,
        "--yt-title", title,
        "--yt-desc", desc,
        "--yt-tags", tags,
        "--yt-secret", str(HERE / "client_secret.json"),
        "--no-parallel",
    ]
    if kids:
        cmd.append("--yt-kids")
    return cmd


def audit():
    data = load_deliveries()
    arr = data.get("delivered", [])
    rows = projects_with_video()

    print("== AUDITORIA DO CONTRATO ==")
    print("registros de entrega: %d" % len(arr))
    print("videos MP4 no disco: %d" % len(rows))

    missing = []
    for d in arr:
        vp = d.get("video_path") or ""
        if not (vp and Path(vp).is_file()):
            missing.append(d)
    print("registros sem MP4 no disco: %d" % len(missing))
    for d in missing:
        print("  - %s | status=%s | publish.done=%s"
              % (d.get("slug"), d.get("status"),
                 (d.get("publish") or {}).get("done")))

    slugs = [d.get("slug") for d in arr]
    dup_slugs = sorted({s for s in slugs if slugs.count(s) > 1})
    print("slugs duplicados: %s" % (", ".join(dup_slugs) if dup_slugs else "nenhum"))

    prompts = [norm_ident(d.get("prompt") or "") for d in arr if d.get("prompt")]
    dup_prompts = sorted({p for p in prompts if p and prompts.count(p) > 1})
    print("prompts duplicados: %d" % len(dup_prompts))

    titles = {}
    for r in rows:
        if r["title"]:
            key = norm_ident(r["title"])
            titles.setdefault(key, []).append(r["folder"])
    dups = {k: v for k, v in titles.items() if len(v) > 1}
    print("titulos iguais em videos diferentes: %d" % len(dups))
    for k, v in dups.items():
        print("  - %s" % k)
        for x in v:
            print("      %s" % x)

    size_map = {}
    for r in rows:
        for name, size in zip(r["videos"], r["sizes"]):
            size_map.setdefault(size, []).append("%s/%s" % (r["folder"], name))
    same = {k: v for k, v in size_map.items() if len(v) > 1}
    print("arquivos MP4 com mesmo tamanho (possivel copia): %d" % len(same))
    for k, v in same.items():
        print("  - %d bytes: %s" % (k, ", ".join(v)))

    reserved_slugs, idents = build_reserved_index()
    print("slugs reservados: %d | identidades reservadas: %d"
          % (len(reserved_slugs), len(idents)))
    return 0


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="Loop de 40 pipelines completos")
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--dry-run", action="store_true", help="so mostra o que faria")
    ap.add_argument("--audit", action="store_true", help="audita contrato e duplicatas")
    ap.add_argument("--no-upload", action="store_true", help="gera o video, nao publica")
    ap.add_argument("--wait-between", type=int, default=5, help="segundos entre videos")
    ap.add_argument("--retries", type=int, default=2, help="tentativas por video (retoma)")
    ap.add_argument("--retry-wait", type=int, default=15, help="segundos entre tentativas")
    a = ap.parse_args()

    if a.audit:
        return audit()

    LOGDIR.mkdir(parents=True, exist_ok=True)
    topics = selected_topics(a.limit)
    if not topics:
        print("Nenhum topico novo para rodar (todos reservados por titulo/slug/MP4).")
        return 0

    print("Topicos selecionados: %d (limite %d)" % (len(topics), a.limit))
    for i, t in enumerate(topics, 1):
        retomar = " (retomar)" if (PROJECTS / slugify(t)).exists() else ""
        print("  %02d. %s%s" % (i, t, retomar))
    if a.dry_run:
        print("DRY-RUN: nada executado.")
        return 0

    ok_count = 0
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    for i, topic in enumerate(topics, 1):
        cmd = build_cmd(topic, i, len(topics),
                        privacy="private" if a.no_upload else "public",
                        kids=not a.no_upload)
        log_path = LOGDIR / ("pipeline40_%02d_%s.log" % (i, slugify(topic)))
        print("\n===== [%02d/%d] %s =====" % (i, len(topics), topic), flush=True)
        print("Log: %s" % log_path, flush=True)

        rc = 1
        attempt = 0
        while attempt <= a.retries:
            attempt += 1
            mode = "w" if attempt == 1 else "a"
            with open(log_path, mode, encoding="utf-8") as lf:
                def tee(line):
                    print(line, flush=True)
                    lf.write(line + "\n")

                tee("\n--- tentativa %d/%d ---" % (attempt, a.retries + 1))
                if attempt == 1:
                    tee("CMD: " + " ".join(cmd))
                env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
                r = subprocess.run(
                    cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", env=env,
                    creationflags=flags,
                )
                rc = r.returncode
                for line in (r.stdout or "").splitlines():
                    tee(line)

                if rc == 0:
                    tee("SUCESSO: [%02d/%d] %s" % (i, len(topics), topic))
                else:
                    tee("FALHA (codigo %d): [%02d/%d] %s" % (rc, i, len(topics), topic))

            if rc == 0:
                ok_count += 1
                break
            if attempt <= a.retries:
                print("Tentativa %d falhou; retomando em %ds..." % (attempt, a.retry_wait), flush=True)
                time.sleep(a.retry_wait)

        if rc != 0:
            print("FALHA definitiva em [%02d/%d] %s - parando o loop."
                  % (i, len(topics), topic), flush=True)
            break

        if i < len(topics):
            print("Aguardando %ds antes do proximo..." % a.wait_between, flush=True)
            time.sleep(a.wait_between)

    print("\nConcluido: %d/%d com sucesso." % (ok_count, len(topics)))
    return 0 if ok_count == len(topics) else 1


if __name__ == "__main__":
    sys.exit(main())
