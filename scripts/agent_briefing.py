# -*- coding: utf-8 -*-
"""agent_briefing.py - COMANDO OBRIGATORIO no inicio de toda sessao.

REGRA DE OURO (2026-11-20): antes de ESCREVER codigo, rodar isto:

    python scripts/agent_briefing.py --slug <slug>

Motivo: ja existem formula pronta para tudo (publicacao por canal, overlays por
idioma, travas de idioma/imagem, VoiceCraft). O agente que "inventa" em vez de
usar o que existe quebra o que ja estava resolvido. Este briefing obriga a ver
as receitas e roda as travas antes de qualquer trabalho.

Nao altera arquivos. So le, imprime e valida. Saida 1 = nao pode seguir.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROJ = ROOT / "projects"

# Lang -> credenciais do CANAL correto (publish_multilang.py LANG_CREDENTIALS).
CANAL = {
    "pt": ("client_secret_pt.json", "youtube_token_pt.json"),
    "en": ("client_secret_en.json", "youtube_token_en.json"),
    "es": ("client_secret_es.json", "youtube_token_es.json"),
}
BADGE = {"pt": "Frida e Luna", "en": "Frida and Luna", "es": "Frida y Luna"}

FORMULAS = [
    ("3 videos PT/EN/ES (overlays + narração + render)", "scripts/gerar_capitulo_trilinguo.py"),
    ("publicar no canal CERTO por idioma", "scripts/publish_multilang.py"),
    ("trava: nenhum texto PT em video EN/ES", "scripts/check_texto_idioma.py --strict"),
    ("trava: mesmas imagens nos 3 idiomas", "scripts/check_imagens_compartilhadas.py --slug <slug>"),
    ("trava geral do CONTRATO", "scripts/hook_validator.py --slug <slug>"),
    ("voz com emoção (12 provedores locais)", "scripts/gen_narration_voicecraft.py (API 8090)"),
    ("thumbnail viral no idioma do video", "scripts/generate_thumbnail.py + pipeline.py THUMB_TEXTS"),
    ("slave de imagens: não pegar folha de referência", "scripts/fix_scenes_ref_personagem.py + commit d90e8dc"),
]

MANUAL_SECOES = [
    "CONTRATO.md §0/§1 (regra de ouro)",
    "MANUAL_GRAFOS.md §0, §37 (CLI), §56/§57 (3 canais), §58.10 (grafo)",
    "scripts/pipeline.py (docstring do topo)",
]


def run(cmd, label):
    print(f"\n--- {label} ---", flush=True)
    r = subprocess.run([sys.executable, *cmd], capture_output=True, text=True,
                       cwd=ROOT, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    print(out[-3500:] if len(out) > 3500 else out, flush=True)
    return r.returncode


def checar_credenciais():
    erros = []
    for lang, (cs, tk) in CANAL.items():
        for f in (cs, tk):
            if not (HERE / f).exists():
                erros.append(f"credencial ausente: {f} (canal {lang.upper()})")
    if erros:
        print("  ! " + "\n  ! ".join(erros), flush=True)
    else:
        print("  OK  credenciais PT/EN/ES presentes (3 canais separados)", flush=True)
    return erros


def checar_overlays(slug):
    p = PROJ / slug
    erros = []
    for lang, badge in BADGE.items():
        d = p / "scenes" / lang
        s0 = d / "s0.html"
        if lang != "pt" and not s0.exists():
            erros.append(f"overlay {lang.upper()} ausente: scenes/{lang}/s0.html "
                         "(use gerar_capitulo_trilinguo.py)")
            continue
        if s0.exists():
            txt = s0.read_text(encoding="utf-8", errors="replace")
            if badge not in txt:
                erros.append(f"overlay {lang.upper()} com badge errado "
                             f"(esperado '{badge}')")
    if erros:
        print("  ! " + "\n  ! ".join(erros), flush=True)
    else:
        print("  OK  overlays por idioma presentes e com badge correto", flush=True)
    return erros


def main():
    ap = argparse.ArgumentParser(description="Briefing obrigatorio do agente")
    ap.add_argument("--slug", default="", help="projeto para validar")
    ap.add_argument("--lang", default="pt", choices=["pt", "en", "es"])
    args = ap.parse_args()

    print("=" * 72)
    print("START HERE — NAO INVENTE. USE O QUE JÁ EXISTE.")
    print("=" * 72)
    print("\n1) LEIA ANTES DE MEXER:")
    for s in MANUAL_SECOES:
        print("   - " + s)
    print("\n2) CONSULTE O GRAFO (barato em token):")
    print('   graphify query "como fazer X" --budget 1500')
    print("\n3) ANTES DE CRIAR, BUSQUE NO HISTORICO:")
    print('   git log --all --oneline --grep="palavra-chave" -i')
    print("   Get-ChildItem scripts -Filter '*palavra*'")
    print("\n4) FORMULAS PRONTAS (usar, NAO reimplementar):")
    for tarefa, script in FORMULAS:
        print(f"   - {tarefa}: {script}")
    print("\n5) REGRAS QUE QUEBRAM SE ESQUECIDAS:")
    print("   - todo texto de tela no idioma do video (PT/EN/ES)")
    print("   - cada idioma vai no SEU canal (token por idioma)")
    print("   - publicar SEMPRE como NAO infantil")
    print("   - thumbnail viral gerada antes de publicar, no idioma do video")
    print("   - narração EN/ES pelo VoiceCraft (API 8090), nao Edge")

    problemas = []
    problemas += checar_credenciais()
    if args.slug:
        if not (PROJ / args.slug).is_dir():
            print(f"\n! projeto nao encontrado: {args.slug}", flush=True)
            return 1
        problemas += checar_overlays(args.slug)
        problemas += ["trava check_texto_idioma"] if run(
            ["scripts/check_texto_idioma.py", "--slug", args.slug, "--strict"],
            "TRAVA idioma (texto PT em EN/ES)") != 0 else []
        problemas += ["trava imagens compartilhadas"] if run(
            ["scripts/check_imagens_compartilhadas.py", "--slug", args.slug],
            "TRAVA imagens (mesmas nos 3 idiomas)") != 0 else []
        problemas += ["trava Hook CONTRATO"] if run(
            ["scripts/hook_validator.py", "--slug", args.slug, "--lang", args.lang],
            f"TRAVA Hook CONTRATO (idioma {args.lang.upper()})") != 0 else []

    print("\n" + "=" * 72)
    if problemas:
        print(f"BLOQUEADO: {len(problemas)} problema(s). Corrija antes de seguir.")
        return 1
    print("BRIEFING OK. Pode seguir usando as formulas prontas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
