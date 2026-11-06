#!/usr/bin/env python3
r"""gemini_fetch.py - baixa imagens / texto / áudio do Gemini web via Chrome (CDP).

REGRA: nunca pede video ao Gemini; o material visual e sempre imagem estatica
(--kind image). --kind video e recusado.

Script único e genérico para o Videomaker. NÃO tem caminho fixo: o destino é
resolvido a partir do projeto (veja resolve_project_dir).

Exemplos:
  python gemini_fetch.py --check
  python gemini_fetch.py --project bulldog-skincare --kind image --name hook --prompt "..."
  python gemini_fetch.py --project-dir C:\videomaker\projects\x --kind image --prompts-file prompts.json
  python gemini_fetch.py --kind text --prompt "Escreva um roteiro..."      # rodando de dentro de projects/<id>/

Requisitos: pip install playwright   (usa o Chrome já aberto com --remote-debugging-port e já logado)
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_VERSION = "r6-2026-11-05 (REGRA: nunca cria video; --kind image reforca imagem estatica unica)"

# REGRA DO PROJETO: o gemini_fetch nunca pede video ao Gemini. Para material
# visual, usa --kind image (imagem estatica). Pedidos de video sao recusados
# e prompts de imagem recebem o reforco abaixo.
IMAGE_ONLY_PREFIX = (
    "INSTRUCAO OBRIGATORIA: gere SOMENTE UMA IMAGEM ESTATICA (ilustracao/foto), "
    "em um unico quadro. NAO crie video, clipe, animacao em movimento, sequencia "
    "de quadros ou storyboard animado. Retorne apenas uma imagem.\n\n"
)

VIDEO_REQUEST_PATTERNS = (
    (r"\b(?:crie|criar|gere|gerar|fa[çc]a|fazer|produza|produzir)\s+(?:um|uma)\s+v[íi]deo(?:\s+(?:animado|curto|em movimento))?\b",
     "crie uma imagem estatica"),
    (r"\bv[íi]deo\s+(?:curto|animado|em movimento|de\s+\d+\s*(?:s|seg|segundos|min|minutos))\b",
     "imagem estatica"),
    (r"\b(?:clipe|videoclipe|clipe de v[íi]deo)\b", "imagem estatica"),
    (r"\bveo\b", "imagem estatica"),
    (r"\b(?:create|make|generate|produce)\s+(?:a|an)\s+video\b", "create a static image"),
    (r"\bvideo\s+clip\b", "static image"),
)


def _enforce_image_only(prompt: str) -> str:
    """Nunca pede video: remove pedidos explicitos e reforca imagem estatica."""
    out = prompt or ""
    for pat, repl in VIDEO_REQUEST_PATTERNS:
        out = re.sub(pat, repl, out, flags=re.I)
    if IMAGE_ONLY_PREFIX.strip() not in out:
        out = IMAGE_ONLY_PREFIX + out
    return out
DEFAULT_CDP = os.environ.get("GEMINI_CDP_URL", "http://127.0.0.1:18800")
EDITORS = ['div.ql-editor[contenteditable="true"]', '[role="textbox"]']
IMG_DL_LABELS = ["Baixar imagem no tamanho original", "Download original image"]
SEND_HINTS = ["Enviar", "Send"]
STOP_HINTS = ["Parar", "Stop"]
RESPONSE_SEL = "message-content, .model-response-text"
URLS = {"image": "https://gemini.google.com/images", "default": "https://gemini.google.com/app"}
MIME_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
            "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/wav": ".wav", "audio/webm": ".webm",
            "audio/ogg": ".ogg", "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov",
            "audio/mp3": ".mp3", "audio/x-m4a": ".m4a", "audio/x-wav": ".wav", "audio/aac": ".aac"}


class LoginRequired(Exception):
    pass


# ----------------------------------------------------------------- Chrome (abre sozinho)
CHROME_CANDIDATES = [
    os.environ.get("CHROME_PATH", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    shutil.which("chrome") or "",
    shutil.which("google-chrome") or "",
]


def cdp_alive(url: str) -> bool:
    try:
        urllib.request.urlopen(url.rstrip("/") + "/json/version", timeout=2)
        return True
    except Exception:
        return False


def default_profile(args) -> Path:
    if args.profile:
        return Path(args.profile)
    if os.environ.get("GEMINI_CHROME_PROFILE"):
        return Path(os.environ["GEMINI_CHROME_PROFILE"])
    return Path(args.root or os.environ.get("OPENMONTAGE_ROOT") or DEFAULT_ROOT) / ".chrome-gemini-profile"


def launch_chrome(cdp_url: str, profile: Path):
    exe = next((c for c in CHROME_CANDIDATES if c and os.path.exists(c)), None)
    if not exe:
        raise SystemExit("Chrome não encontrado. Defina a variável CHROME_PATH com o caminho do chrome.exe.")
    port = urlparse(cdp_url).port or 18800
    profile.mkdir(parents=True, exist_ok=True)
    print(f"Abrindo Chrome (porta {port}, perfil {profile})...", flush=True)
    subprocess.Popen(
        [exe, f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
         "--no-first-run", "--no-default-browser-check", "--window-size=1920,1080",
         "https://gemini.google.com/app"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(45):
        if cdp_alive(cdp_url):
            return
        time.sleep(1)
    raise SystemExit("Chrome abriu, mas a porta de depuração não respondeu. Feche as janelas do Chrome que "
                     "usam este perfil e tente de novo.")


async def needs_login(page) -> bool:
    if "accounts.google.com" in page.url:
        return True
    try:
        link = page.get_by_role("link", name=re.compile(r"Fazer login|Sign in", re.I)).first
        return await link.count() > 0 and await link.is_visible()
    except Exception:
        return False


# ----------------------------------------------------------------- projeto
DEFAULT_ROOT = r"C:\videomaker"


def latest_project(root: Path) -> Path | None:
    pdir = root / "projects"
    if not pdir.is_dir():
        return None
    dirs = [d for d in pdir.iterdir() if d.is_dir()]
    return max(dirs, key=lambda d: d.stat().st_mtime) if dirs else None


def resolve_project_dir(args) -> Path:
    proj = _resolve_project_dir(args)
    if not proj.is_dir():
        root = Path(args.root or os.environ.get("OPENMONTAGE_ROOT") or DEFAULT_ROOT)
        pdir = root / "projects"
        ids = sorted(d.name for d in pdir.iterdir() if d.is_dir()) if pdir.is_dir() else []
        raise SystemExit(f"Projeto não existe: {proj}\nProjetos disponíveis: {', '.join(ids) or '(nenhum)'}")
    return proj


def _resolve_project_dir(args) -> Path:
    r"""Ordem: --project-dir > $OPENMONTAGE_PROJECT_DIR > --project <id|latest> > cwd dentro de projects/<id>
    > projeto mais recente em <root>/projects (com aviso). Raiz padrão: C:\videomaker."""
    root = Path(args.root or os.environ.get("OPENMONTAGE_ROOT") or DEFAULT_ROOT)
    if args.project_dir:
        return Path(args.project_dir).resolve()
    env_dir = os.environ.get("OPENMONTAGE_PROJECT_DIR")
    if env_dir:
        return Path(env_dir).resolve()
    if args.project and args.project != "latest":
        return (root / "projects" / args.project).resolve()
    if not args.project:
        cwd = Path.cwd().resolve()
        for parent in [cwd, *cwd.parents]:
            if parent.parent.name == "projects":
                return parent
    last = latest_project(root)
    if last:
        print(f"AVISO: projeto não informado; usando o mais recente: {last.name}", flush=True)
        return last.resolve()
    raise SystemExit(f"Nenhum projeto encontrado em {root / 'projects'}. Passe --project-dir.")


def load_prompts(args) -> dict[str, str]:
    """Aceita --prompt/--name, ou --prompts-file em 3 formatos:
    {"nome": "prompt"} | [{"name":..,"prompt":..}] | scene_plan.json (scenes[].id + required_assets[].description)."""
    out: dict[str, str] = {}
    if args.prompt:
        out[args.name or "gemini_output"] = args.prompt
    if args.prompts_file:
        data = json.loads(Path(args.prompts_file).read_text(encoding="utf-8"))
        if isinstance(data, dict) and "scenes" in data:
            for sc in data["scenes"]:
                for a in sc.get("required_assets", []):
                    d = a["description"]
                    out[sc["id"]] = (d[4:] if d.startswith("EN: ") else d).strip()
        elif isinstance(data, dict):
            out.update({k: str(v) for k, v in data.items()})
        elif isinstance(data, list):
            for it in data:
                out[it["name"]] = it["prompt"]
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        miss = wanted - set(out)
        if miss:
            raise SystemExit(f"Nomes sem prompt: {sorted(miss)}")
        out = {k: v for k, v in out.items() if k in wanted}
    if not out:
        raise SystemExit("Nenhum prompt. Use --prompt (+ --name) ou --prompts-file.")
    return out


# ----------------------------------------------------------------- página
async def get_page(ctx):
    page = next((p for p in ctx.pages if "gemini.google.com" in p.url), None) or await ctx.new_page()
    await page.bring_to_front()
    await page.set_viewport_size({"width": 1920, "height": 1080})
    return page


async def open_fresh(page, kind: str):
    await page.goto(URLS.get(kind, URLS["default"]), wait_until="domcontentloaded", timeout=45000)
    try:
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    await page.wait_for_timeout(1200)
    if await needs_login(page):
        raise LoginRequired("Sessão do Gemini não está logada. Rode uma vez: python gemini_fetch.py --login")


async def editor(page):
    for sel in EDITORS:
        try:
            await page.wait_for_selector(sel, state="visible", timeout=30000)
            return page.locator(sel).first
        except Exception:
            continue
    raise LoginRequired("Campo de prompt não apareceu (sessão deslogada ou UI mudou).")


async def submit_prompt(page, prompt: str, clear: bool = True) -> bool:
    ed = await editor(page)
    await ed.click()
    await page.wait_for_timeout(400)
    if clear:
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Delete")
        await page.keyboard.insert_text(prompt)
    typed = (await ed.inner_text()).strip()
    if len(typed) < min(20, len(prompt)):
        await ed.click()
        await page.keyboard.insert_text(prompt)
    for attempt in range(3):
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1500)
        if len((await ed.inner_text()).strip()) < 5:
            print(f"  envio confirmado (tentativa {attempt + 1})", flush=True)
            return True
        for hint in SEND_HINTS:  # Enter não enviou: tenta o botão
            btn = page.locator(f'button[aria-label*="{hint}"]')
            if await btn.count():
                try:
                    await btn.last.click()
                    break
                except Exception:
                    pass
        await page.wait_for_timeout(1500)
        if len((await ed.inner_text()).strip()) < 5:
            return True
    return False


async def count_dl(page) -> int:
    return sum([await page.locator(f'[aria-label="{l}"]').count() for l in IMG_DL_LABELS])


def save_bytes(out_dir: Path, name: str, ext: str, data: bytes) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{name}{ext}"
    p.write_bytes(data)
    return p


# ----------------------------------------------------------------- imagem
REFUSAL_PATTERNS = [
    "não consigo gerar",
    "políticas de conteúdo",
    "content policy",
    "vendor policies",
    "políticas de fornecedores",
    "refusal",
    "bloqueado",
    "blocked",
    "safety",
    "violação",
    "violation",
    "não pode ser gerada",
    "não poderá ser gerada",
    "não é possível gerar",
    "não foi possível gerar",
    "não consigo",
    "desculpe",
    "youtube",
    "impróprio",
    "inadequado",
]

async def _check_refusal(page) -> bool:
    """Verifica se a resposta do Gemini indica recusa por política de conteúdo."""
    try:
        # Pega o texto da última resposta visível
        txt = (await page.locator(RESPONSE_SEL).last.inner_text()).strip().lower()
        return any(p in txt for p in REFUSAL_PATTERNS)
    except Exception:
        return False


SOFTEN_MAP = (
    ("caos absoluto", "caos divertido"),
    ("gritando", "latindo bem alto"),
    ("grimar", "reclamar"),
    ("olhou feio", "deu uma olhada indiferente"),
    ("olha feia", "olhada indiferente"),
    ("exige respeito imediato", "pede cuidado"),
    ("temido", "famoso"),
    ("desespero", "ansiedade cômica"),
    ("sargento estrito", "capitã animada"),
    ("assassino", "brinquedo"),
    ("morte", "fim"),
    ("sangue", "brilho"),
    ("louco", "animado"),
)


def _soften_prompt(original_prompt: str) -> str:
    """Variante suavizada do prompt (anti-recusa): mesmo conteudo estrutural
    (CENA + PERSONAGENS + bloco anti-texto/anti-video), termos agressivos
    trocados. Preserva a estrutura nova do prompt (nao corta pelo fim)."""
    out = original_prompt
    for a, b in SOFTEN_MAP:
        out = out.replace(a, b).replace(a.capitalize(), b.capitalize()).replace(a.upper(), b.upper())
    return out


def _minimal_prompt(original_prompt: str) -> str:
    """Gera prompt mínimo (apenas ficha + cena) removendo bloco de estilo SAFE_STYLE."""
    # Assume que o prompt original tem a estrutura: FICHA + "Topic: ..." + SAFE_STYLE
    # Remove tudo após "high-quality cinematic 3D animation" ou "animação 3D cinematográfica"
    import re
    # Procura o início do bloco de estilo seguro
    style_markers = [
        "high-quality cinematic 3d animation",
        "animação 3d cinematográfica",
        "safe_style",
    ]
    for marker in style_markers:
        idx = original_prompt.lower().find(marker)
        if idx != -1:
            return original_prompt[:idx].strip()
    # Fallback: retorna apenas as primeiras ~500 chars (ficha + cena)
    return original_prompt[:500].strip()


UPLOAD_HINTS = ("anexar", "faça upload", "fazer upload", "upload", "adicionar arquivo", "adicionar anexo", "attachment", "attach file", "enviar arquivo", "anexo", "paperclip")


async def attach_reference(page, ref_path) -> bool:
    """Anexa a imagem de referencia (personagens) na conversa do Gemini.
    Tenta input[type=file] do composer; se nao achar, clica no botao de
    anexo e usa o file chooser. Falha = warning e segue sem anexo."""
    if not ref_path:
        return False
    p = Path(ref_path)
    if not p.exists() or p.stat().st_size == 0:
        print("  ref-image: arquivo ausente (%s); seguindo sem anexo" % ref_path, flush=True)
        return False
    try:
        used = False
        inputs = page.locator('input[type="file"]')
        if await inputs.count():
            try:
                await inputs.first.set_input_files(str(p))
                used = True
            except Exception as e:
                print("  ref-image: input[type=file] falhou (%s)" % str(e)[:60], flush=True)
        if not used:
            btn = None
            deadline = time.monotonic() + 25.0
            while time.monotonic() < deadline and btn is None:
                for h in UPLOAD_HINTS:
                    cand = page.locator('button[aria-label*="%s" i]' % h)
                    try:
                        n = await cand.count()
                    except Exception:
                        n = 0
                    if n:
                        btn = cand.last
                        break
                if btn is None:
                    await page.wait_for_timeout(1500)
            if btn is None:
                # Fallback: colar a imagem via clipboard no composer (Ctrl+V)
                print("  ref-image: seletor de anexo indisponivel; tentando colar via clipboard...", flush=True)
                try:
                    ed = await editor(page)
                    await ed.click()
                    await page.wait_for_timeout(500)
                    await page.keyboard.press("Control+a")
                    await page.keyboard.press("Delete")
                    await page.wait_for_timeout(300)
                    img_b64 = base64.b64encode(p.read_bytes()).decode("ascii")
                    await page.evaluate(
                        """async (b64) => {
                            const bin = atob(b64);
                            const bytes = new Uint8Array(bin.length);
                            for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
                            const blob = new Blob([bytes], { type: 'image/png' });
                            const item = new ClipboardItem({ 'image/png': blob });
                            await navigator.clipboard.write([item]);
                        }""",
                        img_b64,
                    )
                    await page.keyboard.press("Control+v")
                    await page.wait_for_timeout(3500)
                    print("  ref-image: colagem via clipboard ok", flush=True)
                    return True
                except Exception as pe:
                    print("  ref-image: colagem via clipboard falhou (%s); seguindo sem anexo" % str(pe)[:80], flush=True)
                    return False
            async with page.expect_file_chooser(timeout=15000) as fc:
                await btn.click()
            chooser = await fc.value
            await chooser.set_files(str(p))
        await page.wait_for_timeout(3500)
        for _ in range(20):
            busy = await page.locator('[role="progressbar"]:visible,.upload-indicator:visible').count()
            if not busy:
                break
            await page.wait_for_timeout(1500)
        print("  ref-image: imagem de referencia anexada (%s)" % p.name, flush=True)
        return True
    except Exception as e:
        print("  ref-image: falhou (%s); seguindo sem anexo" % str(e)[:80], flush=True)
        return False


WORKING_HINTS = ("criando", "gerando", "geração de imagem", "imagens são aproximadas", "imaginary", "experimente conceder")


async def _last_screen_text(page) -> str:
    """Texto da ultima resposta visível no navegador (para leitura de recusas)."""
    try:
        if not await page.locator(RESPONSE_SEL).count():
            return ""
        return (await page.locator(RESPONSE_SEL).last.inner_text()).strip().lower()
    except Exception:
        return ""


def _norm_ascii(t: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()


_REFUSAL_ASCII = None


def _classify_screen(txt: str) -> str:
    global _REFUSAL_ASCII
    if not txt:
        return "empty"
    if _REFUSAL_ASCII is None:
        _REFUSAL_ASCII = [_norm_ascii(p) for p in REFUSAL_PATTERNS]
    t = _norm_ascii(txt)
    if any(p in t for p in _REFUSAL_ASCII):
        return "refusal"
    return "working"


def _split_cena(prompt: str):
    """Retorna (linha_cena, resto_linhas_uteis) do prompt estruturado novo."""
    lines = prompt.split("\n")
    cena = ""
    resto = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("CENA"):
            cena = s
        elif s.startswith(("PERSONAGENS", "Uma única", "IMAGEM")):
            resto.append(s)
    return cena, resto


def _simplified_prompt(prompt: str) -> str:
    """Cena reduzida as duas primeiras frases; resto da estrutura mantida."""
    cena, resto = _split_cena(prompt)
    body = cena.split(":", 1)[1].strip() if ":" in cena else cena
    sents = re.split(r"(?<=[.!?…])\s+", body)
    short = " ".join(s for s in sents[:2] if s.strip())
    if not short:
        return prompt
    return "\n".join(["CENA (gere exatamente esta cena): %s" % short] + resto)


def _generic_prompt(prompt: str) -> str:
    """Estrategia final generica: 1a frase + descricao simples da referencia."""
    cena, resto = _split_cena(prompt)
    body = cena.split(":", 1)[1].strip() if ":" in cena else cena
    sents = re.split(r"(?<=[.!?…])\s+", body)
    short = next((s for s in sents if s.strip()), "cena ilustrativa")
    return "\n".join([
        "CENA (gere exatamente esta cena): %s" % short,
        "Ilustração fofa e divertida de desenho animado das duas personagens "
        "(cachorrinhas) da imagem de referência anexada, na situação descrita.",
    ] + [r for r in resto if r.startswith("Uma única")])


def _strategy_prompts(prompt: str):
    return [prompt, _soften_prompt(prompt), _simplified_prompt(prompt), _generic_prompt(prompt)]


STRATEGY_NAMES = ("original", "suave", "simplificada", "generica")


VIDEO_EXTS = (".mp4", ".webm", ".mov", ".m4v")


async def grab_image(page, name, prompt, out_dir, wait_s, ref_image=None) -> dict:
    prompt = _enforce_image_only(prompt)
    await open_fresh(page, "image")
    before = await count_dl(page)  # conta DEPOIS de abrir conversa nova
    captured = {"body": None, "ct": ""}

    async def on_resp(resp):  # plano B: intercepta a imagem na rede
        if captured["body"] or "googleusercontent.com" not in resp.url:
            return
        try:
            ct = (resp.headers or {}).get("content-type", "")
            if ct.startswith("image/") and resp.status == 200:
                body = await resp.body()
                if body and len(body) > 10000:
                    captured.update(body=body, ct=ct)
        except Exception:
            pass

    page.on("response", on_resp)
    try:
        strategies = _strategy_prompts(prompt)
        attempt_log = []
        for attempt, sp in enumerate(strategies):
            strategy = STRATEGY_NAMES[min(attempt, len(STRATEGY_NAMES) - 1)]
            if attempt:
                print(f"  nova estrategia ({strategy})...", flush=True)
                await open_fresh(page, "image")
                before = await count_dl(page)
                captured["body"] = None
                captured["ct"] = ""
            ok_ref = True
            if ref_image:
                ok_ref = await attach_reference(page, ref_image)
                if not ok_ref:
                    ref_image = None
            if not await submit_prompt(page, sp, clear=bool(ref_image)):
                attempt_log.append(f"{strategy}:prompt nao enviado")
                continue
            # espera adaptativa: le a tela a cada 4s e sai cedo em recusa/parada
            waited = 0
            state = "working"
            while waited < wait_s and await count_dl(page) <= before:
                await page.wait_for_timeout(4000)
                waited += 4
                state = _classify_screen(await _last_screen_text(page))
                if state == "refusal":
                    break  # recusa antecipada: nao espera o timeout todo
                if state == "empty" and waited >= 45:
                    state = "stalled"
                    break  # nada na tela: timeout curto
            if state == "refusal":
                txt = (await _last_screen_text(page))[:120].replace("\n", " ")
                print(f"  ⚠ recusa lida da tela ({waited}s): {txt}", flush=True)
                attempt_log.append(f"{strategy}:recusa ({waited}s)")
                continue
            if await count_dl(page) > before:
                btn = page.locator(f'[aria-label="{IMG_DL_LABELS[0]}"], [aria-label="{IMG_DL_LABELS[1]}"]').last
                try:
                    await btn.wait_for(state="visible", timeout=60000)
                    for _ in range(120):
                        if await btn.is_enabled():
                            break
                        await page.wait_for_timeout(1000)
                    async with page.expect_download(timeout=90000) as dl:
                        await btn.click()
                    d = await dl.value
                    ext = Path(d.suggested_filename).suffix or ".png"
                    if ext.lower() in VIDEO_EXTS:
                        # Gemini gerou VIDEO (Veo) em vez de imagem: tenta proxima estrategia
                        attempt_log.append(f"{strategy}:veo_video_instead_of_image")
                        if attempt < len(strategies) - 1:
                            continue
                        return {"ok": False, "error": "veo_video_instead_of_image", "retried": attempt > 0}
                    out_dir.mkdir(parents=True, exist_ok=True)
                    p = out_dir / f"{name}{ext}"
                    await d.save_as(str(p))
                    return {"ok": True, "path": str(p), "bytes": p.stat().st_size, "method": "download_button", "strategy": strategy, "retried": attempt > 0}
                except Exception as e:
                    print(f"  botão falhou ({e}); tentando captura de rede", flush=True)
            if captured["body"]:
                p = save_bytes(out_dir, name, MIME_EXT.get(captured["ct"], ".jpg"), captured["body"])
                return {"ok": True, "path": str(p), "bytes": p.stat().st_size, "method": "network_fallback", "strategy": strategy, "retried": attempt > 0}
            # sem nada nesta conversa: tenta a proxima estrategia
            attempt_log.append(f"{strategy}:sem download ({waited}s)")
            if attempt < len(strategies) - 1:
                continue
            return {"ok": False, "error": "todas as estrategias falharam: " + "; ".join(attempt_log), "retried": attempt > 0}
    finally:
        page.remove_listener("response", on_resp)


# ----------------------------------------------------------------- texto
async def grab_text(page, name, prompt, out_dir, wait_s) -> dict:
    await open_fresh(page, "text")
    before = await page.locator(RESPONSE_SEL).count()
    if not await submit_prompt(page, prompt):
        return {"ok": False, "error": "prompt não enviado"}
    last, stable, waited = "", 0, 0
    while waited < wait_s:
        await page.wait_for_timeout(2000)
        waited += 2
        if await page.locator(RESPONSE_SEL).count() <= before:
            continue
        txt = (await page.locator(RESPONSE_SEL).last.inner_text()).strip()
        busy = sum([await page.locator(f'button[aria-label*="{h}"]').count() for h in STOP_HINTS])
        stable = stable + 1 if (txt and txt == last and not busy) else 0
        last = txt
        if stable >= 3:  # texto parou de mudar e não há botão "Parar"
            p = save_bytes(out_dir, name, ".md", txt.encode("utf-8"))
            return {"ok": True, "path": str(p), "chars": len(txt), "method": "dom_text"}
    return {"ok": False, "error": f"timeout {wait_s}s sem resposta estável"}


# ----------------------------------------------------------------- áudio / vídeo
ICON_NAMES = ("download", "file_download", "download_2", "save_alt")
DL_SELECTOR = ", ".join(
    [f'[{attr}*="{word}" i]' for attr in ("aria-label", "mattooltip", "title") for word in ("Baixar", "Download")]
    + [f':is(button,[role="button"]):has(mat-icon[fonticon="{n}"])' for n in ICON_NAMES]
    + [f':is(button,[role="button"]):has([data-mat-icon-name="{n}"])' for n in ICON_NAMES]
)
JS_MEDIA = """(tag) => [...document.querySelectorAll(tag)].map(e => ({
    src: e.currentSrc || e.src || (e.querySelector('source') || {}).src || '',
    duration: isFinite(e.duration) ? e.duration : 0, ready: e.readyState})).filter(m => m.src)"""
JS_FETCH = """async (u) => { const r = await fetch(u); const b = await r.blob();
    return await new Promise(res => { const f = new FileReader();
      f.onload = () => res({type: b.type, data: f.result.split(',')[1]}); f.readAsDataURL(b); }); }"""
JS_DEBUG = """() => ({url: location.href,
  buttons: [...document.querySelectorAll('button,a,[role=button],[role=menuitem]')]
    .filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; })
    .map(e => ((e.getAttribute('aria-label') || '') + ' | ' + (e.innerText || '').trim().slice(0, 40) + ' | icons:'
        + [...e.querySelectorAll('mat-icon')].map(i => i.getAttribute('fonticon') || i.dataset.matIconName || i.textContent.trim()).join(',')).slice(0, 140))
    .slice(-80),
  media: [...document.querySelectorAll('audio,video')].map(e => ({tag: e.tagName,
    src: (e.currentSrc || e.src || '').slice(0, 140), dur: e.duration, ready: e.readyState}))})"""


async def is_generating(page) -> bool:
    return sum([await page.locator(f'button[aria-label*="{h}"]').count() for h in STOP_HINTS]) > 0


async def fetch_url(page, url: str):
    """Baixa o arquivo completo. blob:/data: via página; http(s) via requisição com os cookies do Chrome."""
    if url.startswith(("blob:", "data:")):
        res = await page.evaluate(JS_FETCH, url)
        return base64.b64decode(res["data"]), res["type"]
    r = await page.context.request.get(url, timeout=180000)
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status}")
    return await r.body(), r.headers.get("content-type", "")


async def dump_debug(page, out_dir: Path, name: str) -> str:
    """Salva screenshot + lista de botões/mídias da página para diagnosticar mudanças na UI do Gemini."""
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        await page.screenshot(path=str(out_dir / f"_{name}_debug.png"))
        info = await page.evaluate(JS_DEBUG)
        (out_dir / f"_{name}_debug.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return f"(debug falhou: {e})"
    return str(out_dir / f"_{name}_debug.json")


async def try_download(page, btn, out_dir: Path, name: str, default_ext: str):
    """Clica no botão esperando um download. Se não vier, tenta menu 'Baixar' e clique via JS."""
    for mode in ("click", "menu", "js"):
        try:
            async with page.expect_download(timeout=30000) as dl:
                if mode == "click":
                    await btn.click(timeout=10000)
                elif mode == "menu":
                    item = page.get_by_role("menuitem", name=re.compile(r"Baixar|Download", re.I)).first
                    if not await item.count():
                        raise RuntimeError("sem menu de download")
                    await item.click(timeout=5000)
                else:
                    await btn.evaluate("e => e.click()")
            d = await dl.value
            p = out_dir / f"{name}{Path(d.suggested_filename).suffix or default_ext}"
            await d.save_as(str(p))
            return p
        except Exception as e:
            print(f"  download via {mode} não funcionou ({str(e)[:70]})", flush=True)
    return None


async def grab_media(page, name, prompt, out_dir, wait_s, kind) -> dict:
    """Envia o prompt UMA vez e espera a mídia ficar pronta. Captura, em ordem de preferência:
    1) botão Baixar/Download novo na página (arquivo original);
    2) <audio>/<video> com duração > 0 ou URL de mídia vista na rede, baixados com os cookies do Chrome."""
    await open_fresh(page, kind)
    out_dir.mkdir(parents=True, exist_ok=True)
    default_ext = ".mp4" if kind == "video" else ".mp3"
    tags = "audio,video" if kind == "audio" else kind  # Gemini mostra música como cartão que pode ser <video>
    ok_types = ("audio/", "video/") if kind == "audio" else ("video/",)
    seen = {m["src"] for m in await page.evaluate(JS_MEDIA, tags)}
    dl_loc = page.locator(DL_SELECTOR)
    before_dl = await dl_loc.count()
    net = {"url": None}

    async def on_resp(resp):
        try:
            ct = (resp.headers or {}).get("content-type", "").split(";")[0].lower()
            if ct.startswith(ok_types) and resp.status in (200, 206) and net["url"] is None:
                net["url"] = resp.url
        except Exception:
            pass

    page.on("response", on_resp)
    try:
        if not await submit_prompt(page, prompt):
            return {"ok": False, "error": "prompt não enviado"}
        print(f"  prompt enviado; aguardando geração (até {wait_s}s)...", flush=True)
        t0 = time.time()
        first_signal = None
        click_tries = 0
        debug_done = False
        while time.time() - t0 < wait_s:
            await page.wait_for_timeout(3000)

            # 1) botão de download novo (por nome OU por ícone de download)
            try:
                if click_tries < 4 and await dl_loc.count() > before_dl:
                    btn = dl_loc.last
                    if await btn.is_visible() and await btn.is_enabled():
                        click_tries += 1
                        p = await try_download(page, btn, out_dir, name, default_ext)
                        if p:
                            return {"ok": True, "path": str(p), "bytes": p.stat().st_size,
                                    "method": "download_button", "submitted": True}
            except Exception:
                pass

            # diagnóstico antecipado: com 90s sem sucesso, já grava o debug (dá para dar Ctrl+C e me mandar)
            if not debug_done and time.time() - t0 > 90:
                debug_done = True
                print(f"  diagnóstico salvo em {await dump_debug(page, out_dir, name)}", flush=True)

            # 2) elemento de mídia pronto ou URL vista na rede
            try:
                ready = [m for m in await page.evaluate(JS_MEDIA, tags) if m["src"] not in seen and m["duration"] > 0]
                url = ready[-1]["src"] if ready else net["url"]
                if url and first_signal is None:
                    first_signal = time.time()
                if url and time.time() - first_signal > 25 and not await is_generating(page):
                    try:
                        data, ct = await fetch_url(page, url)
                        if data and len(data) > 5000:
                            ext = MIME_EXT.get(ct.split(";")[0].strip().lower(), default_ext)
                            p = save_bytes(out_dir, name, ext, data)
                            return {"ok": True, "path": str(p), "bytes": len(data),
                                    "method": "media_url", "submitted": True}
                    except Exception as e:
                        print(f"  download da URL falhou ({str(e)[:90]}); tentando de novo depois", flush=True)
                        first_signal = time.time()
            except Exception:
                pass

        dbg = await dump_debug(page, out_dir, name)
        return {"ok": False, "submitted": True, "debug": dbg,
                "error": f"timeout {wait_s}s sem conseguir baixar o {kind}. Diagnóstico em {dbg}"}
    finally:
        page.remove_listener("response", on_resp)


# ----------------------------------------------------------------- check / main
async def run_login(ctx) -> int:
    page = await get_page(ctx)
    await page.goto(URLS["default"], wait_until="domcontentloaded", timeout=45000)
    print("Faça login no Google na janela do Chrome que abriu. Aguardando até 10 minutos...", flush=True)
    for _ in range(300):
        await page.wait_for_timeout(2000)
        try:
            if not await needs_login(page) and await page.locator(EDITORS[0]).count():
                print("Login detectado. Sessão salva no perfil; não precisa repetir.")
                return 0
        except Exception:
            pass
    print("Tempo esgotado sem detectar login.")
    return 4


async def run_check(ctx):
    print(f"Abas abertas: {len(ctx.pages)}")
    page = next((p for p in ctx.pages if "gemini.google.com" in p.url), None)
    if not page:
        print("Nenhuma aba do Gemini aberta (o script abrirá uma).")
        return 0
    print("Aba:", page.url)
    print("Título:", await page.title())
    print("Logado:", not await needs_login(page))
    for sel in EDITORS:
        print(f"Campo de prompt {sel}:", await page.locator(sel).count() > 0)
    return 0


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--kind", choices=["image", "text", "audio", "video"], default="image")
    ap.add_argument("--prompt")
    ap.add_argument("--name", help="nome do arquivo (sem extensão) para --prompt")
    ap.add_argument("--prompts-file")
    ap.add_argument("--only", help="nomes separados por vírgula (filtra o prompts-file)")
    ap.add_argument("--project", help="id do projeto em <root>/projects/<id>")
    ap.add_argument("--project-dir", help="caminho absoluto do projeto")
    ap.add_argument("--root", help="raiz do Videomaker (ou $OPENMONTAGE_ROOT)")
    ap.add_argument("--out-dir", help="sobrescreve a pasta de saída (relativa ao projeto ou absoluta)")
    ap.add_argument("--cdp-url", default=DEFAULT_CDP)
    ap.add_argument("--wait", type=int, default=0, help="segundos de espera por item")
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--ref-image", default="", help="imagem anexada como referencia dos personagens (modo image)")
    ap.add_argument("--pause", type=float, default=3.0)
    ap.add_argument("--check", action="store_true", help="só testa a conexão com o Chrome/Gemini")
    ap.add_argument("--login", action="store_true", help="abre o Chrome para você logar no Google (uma única vez)")
    ap.add_argument("--profile", help="pasta do perfil do Chrome (padrão: <root>/.chrome-gemini-profile)")
    ap.add_argument("--no-launch", action="store_true", help="não abrir o Chrome automaticamente")
    args = ap.parse_args()

    # REGRA: o Gemini neste projeto so gera IMAGENS (estaticas), nunca video.
    if args.kind == "video":
        print("REGRA: gemini_fetch nunca cria video. Use --kind image para imagens.")
        return 2

    if not cdp_alive(args.cdp_url):
        if args.no_launch:
            print(f"Chrome não está ouvindo em {args.cdp_url} e --no-launch foi usado.")
            return 3
        launch_chrome(args.cdp_url, default_profile(args))

    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp(args.cdp_url, timeout=15000)
        except Exception as e:
            print(f"Não conectou em {args.cdp_url}: {e}")
            return 3
        ctx = browser.contexts[0]
        if args.login:
            rc = await run_login(ctx)
            await browser.close()
            return rc
        if args.check:
            rc = await run_check(ctx)
            await browser.close()
            return rc

        project = resolve_project_dir(args)
        # Estrutura padrão do Videomaker: public/assets/{images,music,audio,subtitles}, artifacts/, narration/
        default_sub = {"image": "public/assets/images", "text": "artifacts/gemini",
                       "audio": "public/assets/music", "video": "public/assets/video"}[args.kind]
        out_dir = project / (args.out_dir or default_sub)
        if args.out_dir and Path(args.out_dir).is_absolute():
            out_dir = Path(args.out_dir)
        prompts = load_prompts(args)
        wait_s = args.wait or {"image": 480, "text": 180, "audio": 600, "video": 900}[args.kind]
        print(f"gemini_fetch versão {SCRIPT_VERSION}\nProjeto: {project}\nSaída:   {out_dir}\nItens:   {len(prompts)}", flush=True)

        log_path = out_dir / "_gemini_log.json"
        out_dir.mkdir(parents=True, exist_ok=True)
        log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
        page = await get_page(ctx)
        results = {}

        for i, (name, prompt) in enumerate(prompts.items()):
            print(f"\n=== {name} ({args.kind}) ===", flush=True)
            res = {"ok": False, "error": "sem tentativa"}
            for attempt in range(args.retries + 1):
                if attempt:
                    print(f"  retry {attempt}/{args.retries}", flush=True)
                    await page.wait_for_timeout(3000)
                try:
                    if args.kind == "image":
                        res = await grab_image(page, name, prompt, out_dir, wait_s,
                                               ref_image=(args.ref_image or None))
                    elif args.kind == "text":
                        res = await grab_text(page, name, prompt, out_dir, wait_s)
                    else:
                        res = await grab_media(page, name, prompt, out_dir, wait_s, args.kind)
                except LoginRequired as e:
                    print(f"  {e}")
                    await browser.close()
                    return 4
                except Exception as e:
                    res = {"ok": False, "error": str(e)}
                if res.get("ok"):
                    break
                print(f"  falhou: {res.get('error')}", flush=True)
                if res.get("submitted"):
                    print("  prompt já foi enviado; não reenvia para evitar gerar duplicado.", flush=True)
                    break
            results[name] = res
            log[name] = {**res, "kind": args.kind}
            log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
            print("  " + json.dumps(res, ensure_ascii=False)[:300], flush=True)
            if i < len(prompts) - 1:
                await page.wait_for_timeout(int(args.pause * 1000))

        await browser.close()

    ok = sum(1 for r in results.values() if r.get("ok"))
    print(f"\nRESUMO {ok}/{len(results)}")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
