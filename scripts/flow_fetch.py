#!/usr/bin/env python3
r"""flow_fetch.py - baixa imagens / vídeo / áudio do Google Flow via Chrome (CDP).

REGRA: nunca pede vídeo ao Google Flow se o modo for imagem; o material visual
é sempre imagem estática (--kind image). --kind vídeo é recusado no modo image.

Script único e genérico para o Videomaker. NÃO tem caminho fixo: o destino é
resolvido a partir do projeto (veja resolve_project_dir).

Exemplos:
  python flow_fetch.py --check
  python flow_fetch.py --project-dir C:\videomaker\projects\x --kind image --prompt "..."
  python flow_fetch.py --kind image --prompts-file prompts.json
  python flow_fetch.py --kind text --prompt "Escreva um roteiro..."
  python flow_fetch.py --busca-audio --prompt "Narre este texto..." --name s1

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

SCRIPT_VERSION = "r2-2026-11-07 (Google Flow via CDP + Playwright + Gemini TTS)"
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"

# REGRA DO PROJETO: o flow_fetch nunca pede vídeo ao Google Flow no modo image.
# Para material visual, usa --kind image (imagem estática).
IMAGE_ONLY_PREFIX = (
    "INSTRUCAO OBRIGATORIA: gere SOMENTE UMA IMAGEM ESTATICA (ilustracao/foto), "
    "em um unico quadro. NAO crie video, clipe, animacao em movimento, sequencia "
    "de quadros ou storyboard animado. Retorne apenas uma imagem.\n\n"
)

# Personagens padrão já criados dentro do Flow. Todo prompt de imagem usa esta
# referência; anexar arquivo só quando o usuário pedir (--ref-image / --force-ref).
DEFAULT_CHARACTERS = "Frida e Luna"
CHARACTER_REF_MARKER = "REFERENCIA DE PERSONAGENS (OBRIGATORIA)"
CHARACTER_REF_TEMPLATE = (
    CHARACTER_REF_MARKER + ": use como base os personagens ja criados neste Google "
    "Flow chamados {names}. Mantenha exatamente a mesma aparencia dos dois "
    "personagens (Frida: buldogue inglesa amarelo-fawn, tranquila; Luna: salsicha "
    "marrom-chocolate, pelo curto e liso, focinho com pelinhos brancos) em todas "
    "as imagens. Nao altere raca, cor, tamanho, idade nem tracos dos personagens.\n\n"
)


def _enforce_characters(prompt: str, characters: str = DEFAULT_CHARACTERS) -> str:
    """Garante no prompt a referência aos personagens Frida e Luna criados no Flow."""
    out = prompt or ""
    if not characters or CHARACTER_REF_MARKER in out:
        return out
    return CHARACTER_REF_TEMPLATE.format(names=characters) + out

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
    """Nunca pede vídeo: remove pedidos explícitos e reforça imagem estática."""
    out = prompt or ""
    for pat, repl in VIDEO_REQUEST_PATTERNS:
        out = re.sub(pat, repl, out, flags=re.I)
    if IMAGE_ONLY_PREFIX.strip() not in out:
        out = IMAGE_ONLY_PREFIX + out
    return out


DEFAULT_CDP = os.environ.get("GEMINI_CDP_URL", "http://127.0.0.1:18800")
EDITORS = ['div[role="textbox"].ProseMirror', '[role="textbox"]', 'div[contenteditable="true"]']
IMG_DL_LABELS = ["Baixar imagem no tamanho original", "Download original image", "Baixar mídia", "Fazer o download", "Download media", "Baixar", "Download", "Download image", "Baixar imagem"]
SEND_HINTS = ["Enviar", "Send"]
STOP_HINTS = ["Parar", "Stop"]
RESPONSE_SEL = "message-content, .model-response-text"
URLS = {"image": "https://flow.google.com", "video": "https://flow.google.com",
        "audio": "https://flow.google.com", "default": "https://flow.google.com"}
MIME_EXT = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webm",
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
         "https://flow.google.com"],
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
        out[args.name or "flow_output"] = args.prompt
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
    page = next((p for p in ctx.pages if "flow.google.com" in p.url), None) or await ctx.new_page()
    await page.bring_to_front()
    await page.set_viewport_size({"width": 1920, "height": 1080})
    return page


async def _flow_target_url() -> str:
    """URL do Flow a usar: a página do projeto salva no setup, se houver."""
    try:
        state = _load_flow_state()
        if state.get("ready") and state.get("url", "").startswith("https://flow.google.com"):
            return state["url"]
    except Exception:
        pass
    return URLS["default"]


async def open_fresh(page, kind: str):
    url = await _flow_target_url() if kind == "image" else URLS.get(kind, URLS["default"])
    await page.goto(url, wait_until="domcontentloaded", timeout=45000)
    try:
        await page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    await page.wait_for_timeout(1200)
    if await needs_login(page):
        raise LoginRequired("Sessão do Google Flow não está logada. Rode uma vez: python flow_fetch.py --login")
    # Fecha pop-ups de propaganda/permissão e força modo Imagem (nunca vídeo)
    await dismiss_ads_and_permissions(page)
    await select_image_mode(page)


async def editor(page):
    for sel in EDITORS:
        try:
            await page.wait_for_selector(sel, state="visible", timeout=30000)
            return page.locator(sel).first
        except Exception:
            continue
    raise LoginRequired("Campo de prompt não apareceu (sessão deslogada ou UI mudou).")


async def _dismiss_overlays(page):
    """Fecha overlays/modais que possam bloquear cliques."""
    try:
        backdrop = page.locator('.cdk-overlay-backdrop').first
        if await backdrop.count() > 0:
            await backdrop.click()
            await page.wait_for_timeout(1000)
    except Exception:
        pass


async def dismiss_ads_and_permissions(page) -> None:
    """Fecha pop-ups de propaganda, aceita permissões e libera a tela do Flow."""
    try:
        # 1) Botão "Try it now!" / "Experimente agora" (primeira tela)
        try_it_btn = page.locator(
            'button:has-text("Try it now!"), button:has-text("Experimente agora"), '
            '[aria-label*="Try it now" i], [aria-label*="Experimente agora" i]'
        ).first
        if await try_it_btn.count() > 0 and await try_it_btn.is_visible():
            await try_it_btn.click()
            await page.wait_for_timeout(2000)
            print("  'Try it now!' clicado - tela liberada", flush=True)
    except Exception:
        pass

    try:
        # 2) Outros botões de aceitar/fechar permissões
        for hint in ["Aceitar", "Concordar", "OK", "Fechar", "Permitir", "Allow", "Accept", "Sim", "Continue"]:
            btn = page.locator(f'button:has-text("{hint}"), [aria-label*="{hint}" i]').first
            if await btn.count() > 0 and await btn.is_visible():
                try:
                    await btn.click()
                    await page.wait_for_timeout(800)
                except Exception:
                    pass
    except Exception:
        pass


async def _toggle_checked(toggle) -> bool:
    try:
        return await toggle.evaluate(
            "e => e.classList.contains('mat-button-toggle-checked') || "
            "((e.querySelector('button')||{}).getAttribute && "
            "e.querySelector('button').getAttribute('aria-checked') === 'true')"
        )
    except Exception:
        return False


async def select_image_mode(page, aspect: str = "16:9") -> bool:
    """Seleciona 'Imagem' no painel de configurações do Google Flow.

    O painel abre pelo ícone (Gatilho de configurações) ao lado de
    "Nano Banana ... x1" na barra de prompt. NUNCA deixar em Vídeo.
    """
    try:
        toggle = page.locator('mat-button-toggle:has-text("Imagem")').first
        if await toggle.count() == 0:
            trig = page.locator(
                'button[aria-label="Gatilho de configurações"], button.settings-trigger-button'
            ).first
            if await trig.count() == 0:
                print("  AVISO: painel de configurações não encontrado; abortando para não gerar vídeo", flush=True)
                return False
            try:
                await trig.click(timeout=5000)
            except Exception:
                await trig.evaluate("(el) => el.click()")
            await page.wait_for_timeout(900)
            toggle = page.locator('mat-button-toggle:has-text("Imagem")').first

        if await toggle.count() == 0:
            print("  AVISO: opção 'Imagem' não apareceu no painel; abortando para não gerar vídeo", flush=True)
            return False

        if not await _toggle_checked(toggle):
            btn = toggle.locator("button").first
            try:
                if await btn.count():
                    await btn.click(timeout=5000)
                else:
                    await toggle.click(timeout=5000)
            except Exception:
                await toggle.evaluate("(el) => el.click()")
            await page.wait_for_timeout(700)

        if not await _toggle_checked(toggle):
            print("  AVISO: não foi possível confirmar o modo Imagem; abortando para não gerar vídeo", flush=True)
            return False

        if aspect:
            asp = page.locator(f'mat-button-toggle:has-text("{aspect}")').first
            if await asp.count() and not await _toggle_checked(asp):
                try:
                    await asp.locator("button").first.click(timeout=4000)
                except Exception:
                    try:
                        await asp.evaluate("(el) => el.click()")
                    except Exception:
                        pass
                await page.wait_for_timeout(300)

        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        await page.wait_for_timeout(300)
        print(f"  modo Imagem selecionado (x1, {aspect or 'aspecto atual'}) (nunca vídeo)", flush=True)
        return True
    except Exception as e:
        print(f"  AVISO: falha ao selecionar modo Imagem ({str(e)[:80]})", flush=True)
        return False


async def submit_flow_prompt(page, prompt: str, clear: bool = True,
                             aspect: str = "16:9") -> dict:
    """Envia o prompt no campo de texto do Google Flow.

    Retorna dict com {ok: bool, error: str|None}.
    Se não conseguir selecionar modo Imagem, retorna ok=False para evitar gerar vídeo.
    """
    result = {"ok": False, "error": None}
    await _dismiss_overlays(page)
    ed = await editor(page)
    await ed.click()
    await page.wait_for_timeout(300)
    # fill() funciona em contenteditable (ProseMirror) e garante o texto visível
    try:
        await ed.fill(prompt)
    except Exception:
        if clear:
            await page.keyboard.press("Control+a")
            await page.keyboard.press("Delete")
        await page.keyboard.insert_text(prompt)
    await page.wait_for_timeout(400)
    typed = (await ed.inner_text()).strip()
    if len(typed) < min(20, len(prompt)):
        await ed.click()
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Delete")
        await page.keyboard.insert_text(prompt)
        await page.wait_for_timeout(300)
        typed = (await ed.inner_text()).strip()
    if len(typed) < 5:
        result["error"] = "campo de prompt vazio após digitação"
        print(f"  ⚠ {result['error']}", flush=True)
        return result
    # Garantir modo Imagem (NUNCA vídeo) antes de selecionar quantidade
    image_ok = await select_image_mode(page, aspect)
    if not image_ok:
        result["error"] = "não foi possível selecionar modo Imagem - abortando para evitar gerar vídeo"
        print(f"  ⚠ {result['error']}", flush=True)
        return result
    # Selecionar x1 (gerar apenas 1 imagem) antes de enviar
    await select_x1(page)
    # Clicar no botão "Iniciar geração" (arrow_forward)
    for attempt in range(3):
        await page.wait_for_timeout(1500)
        # Tentar clicar no botão de gerar
        gen_btn = page.locator('button[aria-label*="Iniciar geração"], button:has(mat-icon:has-text("arrow_forward"))').first
        if await gen_btn.count() > 0:
            try:
                await gen_btn.click()
                await page.wait_for_timeout(1500)
                if len((await ed.inner_text()).strip()) < 5:
                    print(f"  envio confirmado (tentativa {attempt + 1})", flush=True)
                    result["ok"] = True
                    return result
            except Exception:
                pass
        # Fallback: Enter
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1500)
        if len((await ed.inner_text()).strip()) < 5:
            print(f"  envio confirmado (tentativa {attempt + 1})", flush=True)
            result["ok"] = True
            return result
    result["error"] = "não foi possível enviar o prompt"
    return result


async def select_x1(page) -> bool:
    """Seleciona 'x1' (gerar apenas 1 imagem) no painel de configurações."""
    trig = page.locator(
        'button[aria-label="Gatilho de configurações"], button.settings-trigger-button'
    ).first
    try:
        if await trig.count():
            txt = (await trig.inner_text()).lower()
            if "x1" in txt:
                print("  x1 já selecionado (1 imagem)", flush=True)
                return True
    except Exception:
        pass
    try:
        if not await trig.count():
            return False
        try:
            await trig.click(timeout=5000)
        except Exception:
            await trig.evaluate("(el) => el.click()")
        await page.wait_for_timeout(800)
        toggle = page.locator('mat-button-toggle:has-text("x1")').first
        if await toggle.count() == 0:
            await page.keyboard.press("Escape")
            return False
        if not await _toggle_checked(toggle):
            try:
                await toggle.locator("button").first.click(timeout=4000)
            except Exception:
                await toggle.evaluate("(el) => el.click()")
            await page.wait_for_timeout(500)
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(300)
        print("  x1 selecionado (1 imagem)", flush=True)
        return True
    except Exception:
        try:
            await page.keyboard.press("Escape")
        except Exception:
            pass
        return False


async def count_dl(page) -> int:
    """Conta botões de download visíveis (por aria-label ou ícone de download)."""
    try:
        count = 0
        # Por aria-label
        for label in IMG_DL_LABELS:
            count += await page.locator(f'[aria-label="{label}"]').count()
        # Por ícone de download (mat-icon com "download" ou "file_download")
        try:
            count += await page.locator('button:has(mat-icon:has-text("download")), button:has(mat-icon:has-text("file_download"))').count()
        except Exception:
            pass
        return count
    except Exception:
        return 0


def save_bytes(out_dir: Path, name: str, ext: str, data: bytes) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{name}{ext}"
    p.write_bytes(data)
    return p


def _read_env_value(name: str) -> str:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    raw = b""
    try:
        raw = env_path.read_bytes()
    except Exception:
        pass
    if not raw:
        return (os.environ.get(name) or "").strip()
    text = raw.decode("utf-16-le", errors="ignore") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8", errors="ignore")
    for ln in text.splitlines():
        s = ln.strip().replace("\ufeff", "").strip()
        if s.startswith(name + "="):
            v = s.split("=", 1)[1].strip().strip('"').strip("'")
            if v:
                return v
    return (os.environ.get(name) or "").strip()


def _gemini_tts_key() -> str:
    """Chave da API do Gemini TTS (Google AI Studio) usada no geracao de audio."""
    key = (os.environ.get("GOOGLE_TTS_API_KEY") or "").strip()
    if not key:
        key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        try:
            import json as _json
            cfg_path = Path(__file__).resolve().parent / "config.json"
            if cfg_path.exists():
                cfg = _json.loads(cfg_path.read_text(encoding="utf-8"))
                tts_cfg = cfg.get("tts") or {}
                env_name = str(tts_cfg.get("key_env") or "GOOGLE_TTS_API_KEY")
                key = _read_env_value(env_name)
        except Exception:
            pass
    return key


def generate_audio_gemini(text: str, api_key: str = "", model: str = GEMINI_TTS_MODEL) -> dict:
    """Gera um arquivo de audio via Gemini TTS (Text-to-Speech) usando a Google AI API."""
    from google import genai
    key = (api_key or _gemini_tts_key()).strip()
    if not key:
        raise RuntimeError("Chave GOOGLE_TTS_API_KEY ausente (veja .env / scripts/config.json).")
    client = genai.Client(api_key=key)
    resp = client.models.generate_content(model=model, contents=text, config={"response_modalities": ["AUDIO"]})
    cand = resp.candidates[0]
    part = cand.content.parts[0]
    data = part.inline_data.data
    return {"bytes": data, "mime_type": (part.inline_data.mime_type or "audio/wav"), "model": model}


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
    try:
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
    out = original_prompt
    for a, b in SOFTEN_MAP:
        out = out.replace(a, b).replace(a.capitalize(), b.capitalize()).replace(a.upper(), b.upper())
    return out


def _minimal_prompt(original_prompt: str) -> str:
    import re
    style_markers = [
        "high-quality cinematic 3d animation",
        "animação 3d cinematográfica",
        "safe_style",
    ]
    for marker in style_markers:
        idx = original_prompt.lower().find(marker)
        if idx != -1:
            return original_prompt[:idx].strip()
    return original_prompt[:500].strip()


UPLOAD_HINTS = ("anexar", "faça upload", "fazer upload", "upload", "adicionar arquivo", "adicionar anexo", "attachment", "attach file", "enviar arquivo", "anexo", "paperclip")


async def attach_reference(page, ref_path) -> bool:
    """Anexa a imagem de referência na conversa do Google Flow."""
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
                print("  ref-image: seletor de anexo indisponível; tentando colar via clipboard...", flush=True)
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
            # Tentar file chooser com timeout curto; se travar, cai para JS
            try:
                async with page.expect_file_chooser(timeout=8000) as fc:
                    await btn.click()
                chooser = await fc.value
                await chooser.set_files(str(p))
            except Exception as fc_err:
                print("  ref-image: file chooser travou (%s), tentando via JS..." % str(fc_err)[:80], flush=True)
                try:
                    await btn.evaluate("(el) => el.click()")
                    await page.wait_for_timeout(2000)
                    # Tentar definir diretamente via input[type=file] se existir
                    file_inputs = page.locator('input[type="file"]')
                    if await file_inputs.count() > 0:
                        await file_inputs.first.set_input_files(str(p))
                    else:
                        # Fallback: colar via clipboard
                        ed = await editor(page)
                        await ed.click()
                        await page.wait_for_timeout(500)
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
                except Exception as js_err:
                    print("  ref-image: JS fallback falhou (%s); seguindo sem anexo" % str(js_err)[:80], flush=True)
                    return False
        await page.wait_for_timeout(3500)
        for _ in range(20):
            busy = await page.locator('[role="progressbar"]:visible,.upload-indicator:visible').count()
            if not busy:
                break
            await page.wait_for_timeout(1500)
        print("  ref-image: imagem de referência anexada (%s)" % p.name, flush=True)
        return True
    except Exception as e:
        print("  ref-image: falhou (%s); seguindo sem anexo" % str(e)[:80], flush=True)
        return False


WORKING_HINTS = ("criando", "gerando", "geração de imagem", "imagens são aproximadas", "imaginary", "experimente conceder")


async def _last_screen_text(page) -> str:
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


def _simplified_prompt(prompt: str):
    cena, resto = _split_cena(prompt)
    body = cena.split(":", 1)[1].strip() if ":" in cena else cena
    sents = re.split(r"(?<=[.!?…])\s+", body)
    short = " ".join(s for s in sents[:2] if s.strip())
    if not short:
        return prompt
    return "\n".join(["CENA (gere exatamente esta cena): %s" % short] + resto)


def _generic_prompt(prompt: str):
    cena, resto = _split_cena(prompt)
    body = cena.split(":", 1)[1].strip() if ":" in cena else cena
    sents = re.split(r"(?<=[.!?…])\s+", body)
    short = next((s for s in sents if s.strip()), "cena ilustrativa")
    return "\n".join([
        "CENA (gere exatamente esta cena): %s" % short,
        "Ilustração fofa e divertida de desenho animado das duas personagens "
        "(cachorrinhas Frida e Luna) já criadas neste Flow, na situação descrita.",
    ] + [r for r in resto if r.startswith("Uma única")])


def _strategy_prompts(prompt: str):
    return [prompt, _soften_prompt(prompt), _simplified_prompt(prompt), _generic_prompt(prompt)]


STRATEGY_NAMES = ("original", "suave", "simplificada", "generica")

VIDEO_EXTS = (".mp4", ".webm", ".mov", ".m4v")


async def grab_image(page, name, prompt, out_dir, wait_s, ref_image=None,
                     characters: str = DEFAULT_CHARACTERS,
                     aspect: str = "16:9") -> dict:
    prompt = _enforce_image_only(prompt)
    await open_fresh(page, "image")
    before = await count_dl(page)
    captured = {"body": None, "ct": ""}

    async def on_resp(resp):
        if captured["body"]:
            return
        url = resp.url or ""
        if not ("flow-content.google" in url or "googleusercontent.com" in url
                or "gstatic.com" in url and "flow" in url):
            return
        if "perlin" in url:
            return
        try:
            ct = (resp.headers or {}).get("content-type", "")
            if ct.startswith("image/") and resp.status == 200:
                body = await resp.body()
                if body and len(body) > 20000:
                    captured.update(body=body, ct=ct)
        except Exception:
            pass

    page.on("response", on_resp)
    try:
        strategies = [_enforce_image_only(_enforce_characters(sp, characters))
                      for sp in _strategy_prompts(prompt)]
        attempt_log = []
        for attempt, sp in enumerate(strategies):
            strategy = STRATEGY_NAMES[min(attempt, len(STRATEGY_NAMES) - 1)]
            if attempt:
                print(f"  nova estratégia ({strategy})...", flush=True)
                await open_fresh(page, "image")
                before = await count_dl(page)
                captured["body"] = None
                captured["ct"] = ""
            ok_ref = True
            if ref_image:
                ok_ref = await attach_reference(page, ref_image)
                if not ok_ref:
                    ref_image = None
            try:
                submit_result = await submit_flow_prompt(page, sp, clear=bool(ref_image),
                                                         aspect=aspect)
            except Exception as e:
                err_msg = str(e)
                if "Target page, context or browser has been closed" in err_msg:
                    print(f"  ⚠ Navegador fechado inesperadamente durante envio de prompt", flush=True)
                    return {"ok": False, "error": "navegador fechado inesperadamente", "retried": attempt > 0}
                raise
            if not submit_result.get("ok"):
                attempt_log.append(f"{strategy}:{submit_result.get('error', 'prompt não enviado')}")
                # Se o erro é sobre modo Imagem, não tentar próxima estratégia - abortar
                if "modo Imagem" in str(submit_result.get("error", "")):
                    return {"ok": False, "error": submit_result.get("error"), "retried": attempt > 0}
                continue
            # espera adaptativa
            waited = 0
            state = "working"
            while waited < wait_s and await count_dl(page) <= before:
                await page.wait_for_timeout(4000)
                waited += 4
                state = _classify_screen(await _last_screen_text(page))
                if state == "refusal":
                    break
                if state == "empty" and waited >= 45:
                    state = "stalled"
                    break
            if state == "refusal":
                txt = (await _last_screen_text(page))[:120].replace("\n", " ")
                print(f"  ⚠ recusa lida da tela ({waited}s): {txt}", flush=True)
                attempt_log.append(f"{strategy}:recusa ({waited}s)")
                continue
            if await count_dl(page) > before:
                dl_sel = ", ".join(f'[aria-label="{l}"]' for l in IMG_DL_LABELS)
                btn = page.locator(dl_sel).last
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
                        attempt_log.append(f"{strategy}:veo_video_instead_of_image")
                        if attempt < len(strategies) - 1:
                            continue
                        return {"ok": False, "error": "veo_video_instead_of_image", "retried": attempt > 0}
                    out_dir.mkdir(parents=True, exist_ok=True)
                    p = out_dir / f"{name}{ext}"
                    await d.save_as(str(p))
                    # --- CÓPIA PARA O BANCO DE IMAGENS ---
                    _copiar_para_banco(p)
                    return {"ok": True, "path": str(p), "bytes": p.stat().st_size, "method": "download_button", "strategy": strategy, "retried": attempt > 0}
                except Exception as e:
                    print(f"  botão falhou ({e}); tentando captura de rede", flush=True)
            if captured["body"]:
                p = save_bytes(out_dir, name, MIME_EXT.get(captured["ct"], ".jpg"), captured["body"])
                _copiar_para_banco(p)
                return {"ok": True, "path": str(p), "bytes": p.stat().st_size, "method": "network_fallback", "strategy": strategy, "retried": attempt > 0}
            # ESTRATÉGIA FINAL: tentar baixar qualquer elemento <img> visível na tela
            try:
                img_src = await page.evaluate("""() => {
                    const imgs = Array.from(document.querySelectorAll('img'));
                    for (const img of imgs) {
                        if (img.offsetWidth > 0 && img.offsetHeight > 0 && img.src && img.src.startsWith('http')) {
                            return img.src;
                        }
                    }
                    return null;
                }""")
                if img_src:
                    print(f"  baixando imagem direta da tela: {img_src[:80]}...", flush=True)
                    data, ct = await fetch_url(page, img_src)
                    if data and len(data) > 10000:
                        ext = ".jpg"
                        if ct and "png" in ct.lower():
                            ext = ".png"
                        elif ct and "webp" in ct.lower():
                            ext = ".webp"
                        p = save_bytes(out_dir, name, ext, data)
                        _copiar_para_banco(p)
                        return {"ok": True, "path": str(p), "bytes": len(data), "method": "screen_img", "strategy": strategy, "retried": attempt > 0}
            except Exception as e:
                print(f"  download de imagem da tela falhou ({str(e)[:80]})", flush=True)
            attempt_log.append(f"{strategy}:sem download ({waited}s)")
            if attempt < len(strategies) - 1:
                continue
            # Debug: capturar tela quando tudo falhar
            try:
                await page.screenshot(path=str(out_dir / f"_{name}_debug.png"))
                print(f"  debug: screenshot salvo em {out_dir / f'_{name}_debug.png'}", flush=True)
                # Listar botões visíveis
                buttons = await page.evaluate("""() => Array.from(document.querySelectorAll('button,[role="button"]'))
                    .filter(e => e.offsetWidth > 0 && e.offsetHeight > 0)
                    .map(e => ({text: e.innerText.trim().slice(0,60), aria: e.getAttribute('aria-label')||''}))
                    .slice(0, 30)""")
                print(f"  debug: botões visíveis: {buttons}", flush=True)
            except Exception:
                pass
            return {"ok": False, "error": "todas as estratégias falharam: " + "; ".join(attempt_log), "retried": attempt > 0}
    finally:
        page.remove_listener("response", on_resp)
    return {"ok": False, "error": "grab_image terminou inesperadamente sem retorno", "retried": False}


def _copiar_para_banco(caminho_gerado: Path):
    """Copia a imagem gerada também para o banco de imagens global."""
    try:
        banco = Path(r"C:\videomaker\banco de imagens")
        if not banco.exists():
            return
        nome = caminho_gerado.name
        destino = banco / nome
        if not destino.exists():
            import shutil
            shutil.copy2(str(caminho_gerado), str(destino))
            print(f"  copiado para banco de imagens: {destino}", flush=True)
    except Exception as e:
        print(f"  aviso: não foi possível copiar para o banco de imagens ({e})", flush=True)


# ----------------------------------------------------------------- texto
async def grab_text(page, name, prompt, out_dir, wait_s) -> dict:
    await open_fresh(page, "text")
    before = await page.locator(RESPONSE_SEL).count()
    submit_result = await submit_flow_prompt(page, prompt)
    if not submit_result.get("ok"):
        return {"ok": False, "error": submit_result.get("error", "prompt não enviado")}
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
        if stable >= 3:
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


async def is_generating(page) -> bool:
    return sum([await page.locator(f'button[aria-label*="{h}"]').count() for h in STOP_HINTS]) > 0


async def fetch_url(page, url: str):
    if url.startswith(("blob:", "data:")):
        res = await page.evaluate(JS_FETCH, url)
        return base64.b64decode(res["data"]), res["type"]
    r = await page.context.request.get(url, timeout=180000)
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status}")
    return await r.body(), r.headers.get("content-type", "")


async def try_download(page, btn, out_dir: Path, name: str, default_ext: str):
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
    await open_fresh(page, kind)
    out_dir.mkdir(parents=True, exist_ok=True)
    default_ext = ".mp4" if kind == "video" else ".mp3"
    tags = "audio,video" if kind == "audio" else kind
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
        submit_result = await submit_flow_prompt(page, prompt)
        if not submit_result.get("ok"):
            return {"ok": False, "error": submit_result.get("error", "prompt não enviado")}
        print(f"  prompt enviado; aguardando geração (até {wait_s}s)...", flush=True)
        t0 = time.time()
        first_signal = None
        click_tries = 0
        debug_done = False
        while time.time() - t0 < wait_s:
            await page.wait_for_timeout(3000)
            try:
                if click_tries < 4 and await dl_loc.count() > before_dl:
                    btn = dl_loc.last
                    if await btn.is_visible() and await btn.is_enabled():
                        click_tries += 1
                        p = await try_download(page, btn, out_dir, name, default_ext)
                        if p:
                            _copiar_para_banco(p)
                            return {"ok": True, "path": str(p), "bytes": p.stat().st_size,
                                    "method": "download_button", "submitted": True}
            except Exception:
                pass
            if not debug_done and time.time() - t0 > 90:
                debug_done = True
                print(f"  diagnóstico salvo em {await dump_debug(page, out_dir, name)}", flush=True)
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
                            _copiar_para_banco(p)
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
    """Faz login no Google Flow com pausa para o usuário."""
    page = await get_page(ctx)
    await page.goto(URLS["default"], wait_until="domcontentloaded", timeout=45000)
    print("Faça login no Google na janela do Chrome que abriu.", flush=True)
    print("Aguardando até 10 minutos para detectar login...", flush=True)
    for _ in range(300):
        await page.wait_for_timeout(2000)
        try:
            if not await needs_login(page) and await page.locator(EDITORS[0]).count():
                print("Login detectado. Sessão salva no perfil; não precisa repetir.", flush=True)
                return 0
        except Exception:
            pass
    print("Tempo esgotado sem detectar login.", flush=True)
    return 4


async def _login_with_user_confirmation(ctx) -> int:
    """Requisito #1: se não logado, parar, solicitar login, aguardar OK do usuário,
    testar conexão, se falhar pedir para logar novamente."""
    page = await get_page(ctx)
    await page.goto(URLS["default"], wait_until="domcontentloaded", timeout=45000)

    tentativas = 0
    max_tentativas = 3

    while tentativas < max_tentativas:
        tentativas += 1
        if not await needs_login(page):
            # Já logado - testar se o campo de prompt está disponível
            try:
                ed = await editor(page)
                if await ed.count() > 0:
                    print("Login confirmado. Campo de prompt disponível.", flush=True)
                    return 0
            except Exception:
                pass

        print("\n" + "=" * 60)
        print("LOGIN NECESSÁRIO NO GOOGLE FLOW")
        print(f"Tentativa {tentativas}/{max_tentativas}")
        print("Por favor, faça login no Google na janela do Chrome.")
        print("Após fazer login, pressione Enter aqui para continuar...")
        print("=" * 60)
        try:
            input("Pressione Enter após concluir o login: ")
        except EOFError:
            print("Não foi possível ler entrada do usuário.", flush=True)
            return 4

        await page.wait_for_timeout(3000)
        await page.goto("https://flow.google.com", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2000)

        # Testar se conseguiu logar
        try:
            ed = await editor(page)
            if await ed.count() > 0 and not await needs_login(page):
                print("Login confirmado com sucesso.", flush=True)
                return 0
        except Exception:
            pass

        print(f"Login ainda não detectado após a tentativa {tentativas}.", flush=True)

    print("Falha ao fazer login após todas as tentativas.", flush=True)
    return 4


# ----------------------------------------------------------------- setup / aprendizado
FLOW_STATE_FILE = Path(DEFAULT_ROOT) / ".flow_learned_state.json"


def _load_flow_state() -> dict:
    """Carrega as 'lições aprendidas' de configurações do Flow."""
    try:
        if FLOW_STATE_FILE.exists():
            return json.loads(FLOW_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_flow_state(state: dict) -> None:
    """Salva as lições aprendidas para reutilizar nas próximas execuções."""
    try:
        FLOW_STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  estado do Flow salvo em {FLOW_STATE_FILE}", flush=True)
    except Exception as e:
        print(f"  aviso: não foi salvar estado do Flow ({e})", flush=True)


async def _prompt_user_confirm(message: str) -> bool:
    """Pede confirmação do usuário no console."""
    try:
        resp = input(f"\n{message} (s/n): ").strip().lower()
        return resp in ("s", "sim", "y", "yes", "")
    except EOFError:
        return False


async def run_setup_learning(ctx) -> int:
    """Modo de aprendizado: o usuário configura o Flow manualmente e confirma
    quando estiver pronto. Salva as lições para reutilizar."""
    page = await get_page(ctx)
    await page.goto(URLS["default"], wait_until="domcontentloaded", timeout=45000)

    print("\n" + "=" * 70)
    print("MODO DE APRENDIZADO - Google Flow")
    print("=" * 70)
    print("1. O Flow será aberto no navegador.")
    print("2. Navegue até a tela de criação de projeto.")
    print("3. Clique em 'Imagem' (não Vídeo).")
    print("4. Selecione 'x1' (gerar apenas 1 imagem).")
    print("5. Aceite permissões e feche pop-ups de propaganda.")
    print("6. Deixe o campo de prompt visível e pronto.")
    print("7. Quando tudo estiver configurado, volte aqui e pressione Enter.")
    print("=" * 70)

    # Aguardar login se necessário
    if await needs_login(page):
        print("\nLOGIN NECESSÁRIO. Faça login no Google no Chrome.")
        if not await _prompt_user_confirm("Pressione Enter após concluir o login?"):
            return 4
        await page.wait_for_timeout(3000)
        await page.goto("https://flow.google.com", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(2000)

    # Aguardar o usuário configurar tudo
    if not await _prompt_user_confirm("Já configurou o Flow (Imagem, x1, sem pop-ups)? Pressione Enter para continuar"):
        return 4

    # Validar se está pronto
    try:
        ed = await editor(page)
        ready = await ed.count() > 0
    except Exception:
        ready = False

    if ready:
        print("\n✓ Campo de prompt detectado. O Flow está pronto!", flush=True)
        _save_flow_state({
            "ready": True,
            "url": page.url,
            "title": await page.title(),
            "learned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "editors_found": [sel for sel in EDITORS if await page.locator(sel).count() > 0],
        })
        return 0
    else:
        print("\n✗ Campo de prompt NÃO detectado. Tente novamente.", flush=True)
        _save_flow_state({"ready": False})
        return 1


async def validate_flow_ready(page) -> bool:
    """Valida se o Flow está pronto usando as lições aprendidas."""
    state = _load_flow_state()
    if not state.get("ready"):
        return False

    async def _has_editor() -> bool:
        try:
            for sel in state.get("editors_found", EDITORS):
                if await page.locator(sel).count() > 0:
                    return True
        except Exception:
            pass
        return False

    if await _has_editor():
        return True

    # Se veio para a home (sem editor), tenta abrir a página do projeto salva.
    target = state.get("url", "")
    if target.startswith("https://flow.google.com") and target.rstrip("/") != page.url.rstrip("/"):
        try:
            await page.goto(target, wait_until="domcontentloaded", timeout=45000)
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass
            await page.wait_for_timeout(2500)
            return await _has_editor()
        except Exception:
            return False
    return False


async def run_check(ctx):
    print(f"Abas abertas: {len(ctx.pages)}")
    page = next((p for p in ctx.pages if "flow.google.com" in p.url), None)
    if not page:
        print("Nenhuma aba do Google Flow aberta (o script abrirá uma).")
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
    ap.add_argument("--ref-image", "--force-ref", dest="ref_image", default="",
                    help="anexa uma imagem de referência (força a referência). Padrão: não anexa; "
                         "usa os personagens Frida e Luna já criados no Flow")
    ap.add_argument("--characters", default=DEFAULT_CHARACTERS,
                    help="personagens criados no Flow usados como referência no prompt "
                         f"(padrão: {DEFAULT_CHARACTERS!r}; passe vazio para desativar)")
    ap.add_argument("--aspect", default="16:9",
                    help="proporção da imagem no painel do Flow (padrão: 16:9; vazio mantém)")
    ap.add_argument("--busca-audio", dest="busca_audio", action="store_true",
                    help="busca/gera audio de narracao via Gemini TTS (API) e salva o wav (usa --prompt e --name)")
    ap.add_argument("--pause", type=float, default=3.0)
    ap.add_argument("--check", action="store_true", help="só testa a conexão com o Chrome/Flow")
    ap.add_argument("--login", action="store_true", help="abre o Chrome para você logar no Google (uma única vez)")
    ap.add_argument("--setup", action="store_true", help="modo de aprendizado: configura o Flow interativamente e salva as lições")
    ap.add_argument("--skip-confirm", action="store_true", help="pula a confirmação do usuário antes de enviar o prompt")
    ap.add_argument("--profile", help="pasta do perfil do Chrome (padrão: <root>/.chrome-gemini-profile)")
    ap.add_argument("--no-launch", action="store_true", help="não abrir o Chrome automaticamente")
    args = ap.parse_args()

    # REGRA: o Google Flow neste projeto só gera IMAGENS (estáticas), nunca vídeo.
    if args.kind == "video":
        print("REGRA: flow_fetch nunca cria vídeo. Use --kind image para imagens.")
        return 2

    # NOVO: --busca-audio gera audio de narracao via Gemini TTS (API) e salva o wav.
    if getattr(args, "busca_audio", False):
        if not args.prompt:
            print("ERRO: --busca-audio precisa de --prompt (texto de narracao) e --name (arquivo).")
            return 2
        project = _resolve_project_dir(args)
        if args.out_dir and Path(args.out_dir).is_absolute():
            out_dir = Path(args.out_dir)
        else:
            out_dir = project / "public" / "assets" / "audio" / "narration"
        text = args.prompt.strip()
        if not text:
            print("ERRO: --prompt vazio para --busca-audio.")
            return 2
        try:
            res_audio = generate_audio_gemini(text)
        except Exception as e:
            print(f"ERRO no Gemini TTS: {e}")
            return 5
        data = res_audio.get("bytes") or b""
        if not data:
            print("ERRO: Gemini TTS nao retornou audio.")
            return 5
        p = save_bytes(out_dir, args.name, ".wav", data)
        print(f"OK --busca-audio: audio salvo em {p} ({len(data)} bytes) modelo {res_audio.get('model')}")
        return 0

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
            rc = await _login_with_user_confirmation(ctx)
            await browser.close()
            return rc

        if args.check:
            rc = await run_check(ctx)
            await browser.close()
            return rc

        if args.setup:
            rc = await run_setup_learning(ctx)
            await browser.close()
            return rc

        project = resolve_project_dir(args)
        default_sub = {"image": "public/assets/images", "text": "artifacts/gemini",
                       "audio": "public/assets/music", "video": "public/assets/video"}[args.kind]
        out_dir = project / (args.out_dir or default_sub)
        if args.out_dir and Path(args.out_dir).is_absolute():
            out_dir = Path(args.out_dir)
        prompts = load_prompts(args)
        wait_s = args.wait or {"image": 480, "text": 180, "audio": 600, "video": 900}[args.kind]
        print(f"flow_fetch versão {SCRIPT_VERSION}\nProjeto: {project}\nSaída:   {out_dir}\nItens:   {len(prompts)}", flush=True)
        if args.kind == "image":
            ref_txt = args.ref_image or "nenhuma (usa personagens do Flow)"
            print(f"Personagens: {args.characters or 'desativado'}\nReferência forçada: {ref_txt}", flush=True)

        log_path = out_dir / "_flow_log.json"
        out_dir.mkdir(parents=True, exist_ok=True)
        log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
        page = await get_page(ctx)
        # Garantir que estamos no Flow (navegar se necessário)
        if "flow.google.com" not in page.url:
            await page.goto(await _flow_target_url(), wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2000)

        # Validar se o Flow está pronto usando as lições aprendidas
        ready = await validate_flow_ready(page)
        if not ready:
            print("\n" + "=" * 70)
            print("O Google Flow ainda não foi configurado.")
            print("Execute: python scripts/flow_fetch.py --setup")
            print("para configurar interativamente antes de gerar imagens.")
            print("=" * 70 + "\n")
            await browser.close()
            return 1

        # Validar com o usuário antes de enviar o prompt (pode ser desabilitado com --skip-confirm)
        if not getattr(args, "skip_confirm", False):
            print("\n" + "=" * 70)
            print("VALIDAÇÃO - Google Flow pronto para enviar prompt")
            print("=" * 70)
            print("Verifique se:")
            print("  - O Flow está na tela de criação (não Vídeo)")
            print("  - A opção 'x1' (1 imagem) está selecionada")
            print("  - O campo de prompt está visível")
            print("  - Não há pop-ups de propaganda bloqueando")
            print("=" * 70)
            if not await _prompt_user_confirm("Tudo está pronto? Posso enviar o prompt agora?"):
                print("Operação cancelada pelo usuário.", flush=True)
                await browser.close()
                return 1
            print("✓ Usuário confirmou. Enviando prompt...", flush=True)
        else:
            print("\n✓ --skip-confirm ativado. Enviando prompt automaticamente...", flush=True)

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
                                               ref_image=(args.ref_image or None),
                                               characters=args.characters,
                                               aspect=args.aspect)
                    elif args.kind == "text":
                        res = await grab_text(page, name, prompt, out_dir, wait_s)
                    else:
                        res = await grab_media(page, name, prompt, out_dir, wait_s, args.kind)
                except LoginRequired as e:
                    print(f"  {e}")
                    await browser.close()
                    return 4
                except Exception as e:
                    err_msg = str(e)
                    if "Target page, context or browser has been closed" in err_msg:
                        print(f"  ⚠ Navegador fechado inesperadamente", flush=True)
                        res = {"ok": False, "error": "navegador fechado inesperadamente"}
                        break  # Não tenta retry se o navegador fechou
                    res = {"ok": False, "error": err_msg}
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
