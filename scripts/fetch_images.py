# -*- coding: utf-8 -*-
"""
Gera as imagens das cenas no Gemini web (Chrome ja logado) usando a skill
gemini-media-scraping, e depois corta para 1920x1080.

PRE-REQUISITO OBRIGATORIO: este script RODA SEMPRE em modo gerador de IMAGEM
do Gemini (--kind image). Nunca gera audio ou video aqui. Se o Chrome nao
estiver aberto com --remote-debugging-port=18800 e logado no Google, rode:
  python scripts/gemini_fetch.py --login

Uso:
  python scripts/fetch_images.py                     # todas as 16 imagens
  python scripts/fetch_images.py --only s4_barking,s8_jealous
  python scripts/fetch_images.py --single s4_barking  # processa UNA imagem, retorna rc
  python scripts/fetch_images.py --no-preprocess
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# OBRIGATORIO: sempre modo imagem. Nao permitir audio/video neste script.
FORCED_KIND = "image"

# Backstop: prompts antigos com marcas/lixo que o filtro de IP rejeita.
_BANNED_WORDS = ("pixar", "disney", "ghibli", "dreamworks", "illumination")


def get_ref_image():
    """Imagem de referencia dos personagens (config.json -> reference_image).
    Retorna caminho se o arquivo existir; "" caso contrario."""
    try:
        cfg = load_json(HERE / "config.json")
        p = Path(cfg.get("reference_image", ""))
        if p and p.exists() and p.stat().st_size > 0:
            return str(p)
    except Exception:
        pass
    return ""


def copy_to_bank(jpg: Path, proj_name: str):
    """Copia a imagem gerada para o banco de imagens global (config.json ->
    image_bank). Preserva origem com sufixo __slug em caso de colisao."""
    try:
        bank = Path(load_json(HERE / "config.json").get("image_bank", ""))
    except Exception:
        return
    if not bank:
        return
    if not jpg or not jpg.exists() or jpg.stat().st_size == 0:
        return
    try:
        if jpg.resolve().parent == bank.resolve():
            return
    except Exception:
        pass
    bank.mkdir(parents=True, exist_ok=True)
    dst = bank / jpg.name
    if dst.exists():
        dst = bank / ("%s__%s" % (proj_name, jpg.name))
        if dst.exists():
            print("banco de imagens: ja existe %s" % dst.name)
            return
    shutil.copyfile(jpg, dst)
    print("banco de imagens: copiado %s" % dst.name)


def clean_prompt_text(t):
    """Remove marcas de estudio, HTML, risadas, meta-instrucoes de 'todas as cenas'
    e conectivos órfãos de um prompt. Cada imagem é independente."""
    t = re.sub(r"<[^>]+>", " ", str(t))
    t = re.sub(r"\b(?:hahaha+|ha\s+ha\s+ha+|kkkk+|rsrs+)\b[!.]*", " ", t, flags=re.I)
    for w in _BANNED_WORDS:
        t = re.sub(re.escape(w), " ", t, flags=re.I)
    t = re.sub(r"in the style of|estilo (de|do|da|dos|das)\s*", " ", t, flags=re.I)
    t = re.sub(r"\b(?:da|do|das|dos|de)\s+(?:e\s*(?=[,;.]|$)|,|;)\s*", " ", t, flags=re.I)
    t = re.sub(r"ciumenta e possessiva com o tutor", "mandona", t, flags=re.I)
    t = re.sub(r"ciumenta e possessiva", "mandona", t, flags=re.I)
    t = re.sub(r"possessiva com o tutor", "mandona", t, flags=re.I)
    t = re.sub(r"n[aã]o peluda, sem pelos longos, sem barba", "pelo curto e liso", t, flags=re.I)
    # meta-instrucao inutil para geracao de UMA imagem
    t = re.sub(r"Personagens fixos em todas as cenas:\s*", "", t, flags=re.I)
    t = re.sub(r"[Mm]esmas ra[cç]as, cores, portes e tra[cç]os em todas as imagens\.?\s*", "", t)
    t = re.sub(r"[Mm]esmas ra[cç]as, cores e portes em todas as imagens\.?\s*", "", t)
    t = re.sub(r"em todas as (imagens|cenas)", "", t, flags=re.I)
    # sem texto na imagem (o video ja tem overlays)
    if "no text" not in t.lower() and "sem texto" not in t.lower() and "nenhuma letra" not in t.lower():
        t = t.rstrip(" ,;.") + (
            ". no text, no subtitles, no captions, no speech bubbles, "
            "no watermarks, no letters, no words, no typography"
        )
    t = re.sub(r"\s+([,.;;])", r"\1", t)
    t = re.sub(r"\s{2,}", " ", t)
    return t.strip(" ,;.")


def sanitize_prompts_file(prompts_path: Path):
    """Reescreve image_prompts.json se tiver marcas/lixo que causam rejeição."""
    if not prompts_path.exists():
        return
    try:
        data = json.loads(prompts_path.read_text(encoding="utf-8"))
    except Exception:
        return
    changed = False
    for k, v in list(data.items()):
        if k.startswith("_") or not isinstance(v, str):
            continue
        low = v.lower()
        dirty = (
            any(w in low for w in _BANNED_WORDS)
            or "<br" in low
            or "hahaha" in low
            or "possessiva" in low
            or "personagens fixos" in low
            or "em todas as" in low
        )
        # conectivo órfão "da  e ,"
        if re.search(r"\bda\s+e\s*,|da\s+,", v, re.I):
            dirty = True
        if dirty:
            data[k] = clean_prompt_text(v)
            changed = True
    if changed:
        prompts_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("image_prompts.json: prompts limpos (marcas/rejeitáveis removidos)")


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _garantir_modo_imagem(cmd):
    """Garante que --kind image esteja presente e nao seja sobrescrito por outro valor."""
    # Remove qualquer --kind existente e reinsere com o valor correto no inicio
    filtrado = []
    i = 0
    while i < len(cmd):
        if cmd[i] == "--kind" and i + 1 < len(cmd):
            i += 2  # pula o valor antigo
            continue
        filtrado.append(cmd[i])
        i += 1
    # Insere --kind image logo apos o executavel e o script da skill
    # cmd[0] = python, cmd[1] = skill_path
    filtrado.insert(2, "--kind")
    filtrado.insert(3, FORCED_KIND)
    return filtrado


def run_single(proj, prompts, out_dir, name, wait, pause, no_preprocess=False):
    """Processa UNA imagem pelo nome (sem .jpg). Retorna (rc, name, bytes)."""
    cfg = load_json(Path(__file__).resolve().parent / "config.json")
    skill = Path(cfg["gemini_skill"])
    cmd = [sys.executable, str(skill),
           "--project-dir", str(proj),
           "--kind", FORCED_KIND,
           "--prompts-file", str(prompts),
           "--out-dir", str(out_dir),
           "--wait", str(wait),
           "--pause", str(pause),
           "--only", name]
    ref = get_ref_image()
    if ref:
        cmd += ["--ref-image", ref]
    cmd = _garantir_modo_imagem(cmd)
    print(" ".join(cmd))
    rc = subprocess.run(cmd).returncode
    # verifica se o arquivo existe e tem tamanho > 0
    jpg = Path(out_dir) / (name + ".jpg")
    size = jpg.stat().st_size if jpg.exists() else 0
    if size > 0:
        copy_to_bank(jpg, Path(proj).name)
    if not no_preprocess:
        pre = [sys.executable, str(HERE / "preprocess_images.py"),
               "--only", name + ".jpg"]
        subprocess.run(pre, check=False)
    return rc, name, size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="nomes sem .jpg separados por virgula")
    ap.add_argument("--single", default="", help="processa UNA imagem pelo nome")
    ap.add_argument("--wait", type=int, default=420)
    ap.add_argument("--pause", type=int, default=6)
    ap.add_argument("--proj", default=None, help="diretorio do projeto (senao vem de config.json)")
    ap.add_argument("--no-preprocess", action="store_true")
    args = ap.parse_args()

    cfg = load_json(HERE / "config.json")
    # garante tempo minimo de geracao por tentativa (config image_wait_s)
    try:
        cfg_wait = int(cfg.get("image_wait_s", 0) or 0)
        if cfg_wait > args.wait:
            print(f"wait aumentado pela config: {args.wait} -> {cfg_wait}", flush=True)
            args.wait = cfg_wait
    except Exception:
        pass
    proj = (Path(args.proj) if args.proj else (HERE / cfg.get("project_dir", ".."))).resolve()
    skill = Path(cfg["gemini_skill"])

    prompts = proj / "artifacts" / "image_prompts.json"
    out_dir = proj / "assets" / "images" / "gemini" / "scenes"
    out_dir.mkdir(parents=True, exist_ok=True)
    sanitize_prompts_file(prompts)

    # modo single: processa uma imagem e sai
    if args.single:
        rc, name, size = run_single(proj, prompts, out_dir, args.single, args.wait, args.pause,
                                    args.no_preprocess)
        print(f"single {name}: rc={rc} bytes={size}")
        return rc

    cmd = [sys.executable, str(skill),
           "--project-dir", str(proj),
           "--kind", FORCED_KIND,
           "--prompts-file", str(prompts),
           "--out-dir", str(out_dir),
           "--wait", str(args.wait),
           "--pause", str(args.pause)]
    if args.only:
        cmd += ["--only", args.only]
    ref = get_ref_image()
    if ref:
        cmd += ["--ref-image", ref]
    cmd = _garantir_modo_imagem(cmd)

    print(" ".join(cmd))
    rc = subprocess.run(cmd).returncode
    if rc != 0:
        print("gemini_fetch falhou (codigo %s)" % rc)
        return rc

    for k, v in load_json(prompts).items():
        if k.startswith("_"):
            continue
        copy_to_bank(out_dir / (k + ".jpg"), proj.name)

    if not args.no_preprocess:
        pre = [sys.executable, str(HERE / "preprocess_images.py")]
        if args.only:
            pre += ["--only", ",".join(n + ".jpg" if not n.endswith(".jpg") else n
                                       for n in args.only.split(","))]
        subprocess.run(pre, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
