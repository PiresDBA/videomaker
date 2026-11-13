# -*- coding: utf-8 -*-
"""
Trava anti-repeticao de prompt (MANUAL_GRAFOS.md 58.6 / CONTRATO.md 5.8).

Falha (exit 1) quando um prompt manda o gerador COPIAR a imagem de referencia.
Foi essa a causa do video do Chihuahua repetir a mesma foto de ~1:22 ao fim e do
Restaurante repetir a mesma figura o video inteiro: "siga a imagem de referencia
anexada para TUDO", "mantenha exatamente a mesma aparencia ... em todas as
imagens", "mantenha este mesmo ambiente em todas as imagens".

A referencia (`--ref-image`) serve SOMENTE para o design das personagens e para
o estilo do traco. A cena vem da narracao e manda em tudo.

Uso:
  python scripts/check_prompt_repeticao.py                  # todos os projetos
  python scripts/check_prompt_repeticao.py --slug <slug>    # um projeto
  python scripts/check_prompt_repeticao.py --slug <slug> --strict
      (--strict exige tambem a estrutura nova: CENA prioridade maxima +
       REGRA ANTI-REPETICAO; usado pelo gerar_capitulo_trilinguo.py)
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

PROMPT_BUILDERS = (
    HERE / "generate_scenes_and_prompts.py",
    HERE / "flow_fetch.py",
)

# Frases que pedem copia literal da referencia (comparadas sem acento/minusculas).
FRASES_PROIBIDAS = (
    "siga a imagem de referencia anexada para tudo",
    "para tudo - aparencia",
    "mantenha exatamente a mesma aparencia",
    "mantenha este mesmo ambiente em todas as imagens",
    "referencia.png",
    "mesma aparencia dos dois personagens em todas as imagens",
    "use-o como referencia de cores",
)

# A referencia pode aparecer, mas so com este sentido.
FRASES_OBRIGATORIAS = (
    "regra anti-repeticao",
    "cena (prioridade maxima",
)


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto or "")
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).lower()


def _varrer_fonte(caminho: Path, erros: list):
    """Confere os textos fixos dos construtores de prompt."""
    try:
        bruto = caminho.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        erros.append(f"{caminho.name}: nao foi possivel ler ({e})")
        return
    norm = normalizar(bruto)
    for frase in FRASES_PROIBIDAS:
        if frase in norm:
            erros.append(
                f"{caminho.name}: frase proibida no construtor de prompt -> "
                f"'{frase}' (a referencia nunca define a cena; ver CONTRATO.md 5.8)"
            )


def _varrer_prompts(arquivo: Path, strict: bool, erros: list, avisos: list):
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8-sig"))
    except Exception as e:
        erros.append(f"{arquivo}: JSON invalido ({e})")
        return
    projeto = arquivo.parent.parent.name
    for nome, prompt in dados.items():
        if str(nome).startswith("_") or not isinstance(prompt, str):
            continue
        norm = normalizar(prompt)
        for frase in FRASES_PROIBIDAS:
            if frase in norm:
                # Projeto ja publicado (prompt antigo, imagem ja conferida):
                # nao bloqueia o repo. Prompt NOVO passa por --strict.
                destino = erros if strict else avisos
                destino.append(
                    f"[{projeto}] {nome}: frase proibida -> '{frase}'"
                )
        if strict:
            for frase in FRASES_OBRIGATORIAS:
                if frase not in norm:
                    erros.append(
                        f"[{projeto}] {nome}: falta o bloco obrigatorio "
                        f"'{frase}' (regenere com "
                        f"generate_scenes_and_prompts.py)"
                    )


def _checar_scene_mode(erros: list):
    cfg = HERE / "config.json"
    try:
        dados = json.loads(cfg.read_text(encoding="utf-8-sig"))
    except Exception:
        return
    modo = ((dados or {}).get("scene_density") or {}).get("scene_mode")
    if modo and str(modo).lower() != "two":
        erros.append(
            f"scripts/config.json: scene_density.scene_mode = '{modo}'. "
            "O modo 'beats' gera varios prompts quase identicos por secao e "
            "multiplica imagem repetida. Use 'two' (CONTRATO.md 5.8)."
        )


def _checar_build_prompt(erros: list):
    """Garante que o corte de MAX_PROMPT_CHARS nao come as regras obrigatorias.

    Regressao real (§58.6): em cenas longas o corte derrubava a linha
    "REGRA ANTI-REPETICAO" e a imagem saia repetindo a referencia.
    """
    try:
        if str(HERE) not in sys.path:
            sys.path.insert(0, str(HERE))
        import generate_scenes_and_prompts as gsp
    except Exception as e:
        erros.append(f"nao foi possivel importar generate_scenes_and_prompts ({e})")
        return
    cena = ("A Frida e a Luna correram pela praca cheia de gente, comeram "
            "muitas coisas gostosas e latiram de alegria. ") * 15
    try:
        prompt = gsp.build_prompt("Teste de trava", cena, "desenho animado",
                                  True, has_reference=True,
                                  cenario="restaurante dos caes")
    except Exception as e:
        erros.append(f"build_prompt falhou no teste da trava ({e})")
        return
    norm = normalizar(prompt)
    for frase in FRASES_OBRIGATORIAS:
        if frase not in norm:
            erros.append(
                f"build_prompt: cena longa cortou o bloco obrigatorio '{frase}' "
                "(corte deve reduzir a CENA, nunca as regras; CONTRATO.md 5.8)"
            )
    if len(prompt) > gsp.MAX_PROMPT_CHARS:
        erros.append("build_prompt: passou de MAX_PROMPT_CHARS")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Trava anti-repeticao: prompt nao pode mandar copiar a referencia")
    ap.add_argument("--slug", default="", help="confere so este projeto")
    ap.add_argument("--strict", action="store_true",
                    help="exige tambem a estrutura nova do prompt")
    ap.add_argument("--projects-dir", default=str(ROOT / "projects"))
    args = ap.parse_args()

    erros = []
    avisos = []
    for fonte in PROMPT_BUILDERS:
        if fonte.exists():
            _varrer_fonte(fonte, erros)
    _checar_build_prompt(erros)
    _checar_scene_mode(erros)

    base = Path(args.projects_dir)
    if args.slug:
        arquivos = [base / args.slug / "artifacts" / "image_prompts.json"]
    else:
        arquivos = sorted(base.glob("*/artifacts/image_prompts.json"))
    for arq in arquivos:
        if arq.exists():
            _varrer_prompts(arq, args.strict, erros, avisos)

    if avisos:
        print("AVISO: prompt antigo (projeto ja gerado) com frase proibida.")
        print("       Nao bloqueia commit; sera bloqueado se for regenerado.")
        for a in avisos[:5]:
            print("  ~ " + a)
        if len(avisos) > 5:
            print(f"  ... e mais {len(avisos) - 5}")

    if erros:
        print("=" * 70)
        print("TRACADO: prompt pedindo repeticao da referencia (ou modo errado)")
        print("=" * 70)
        for e in erros[:40]:
            print(" - " + e)
        if len(erros) > 40:
            print(f" ... e mais {len(erros) - 40}")
        print()
        print("Regra (CONTRATO.md 5.8 / MANUAL_GRAFOS.md 58.6):")
        print("  A imagem de referencia serve SO para o design das personagens e")
        print("  para o estilo do traco. A CENA manda em tudo. Nunca pedir para")
        print("  'manter o mesmo ambiente', 'mesma aparencia em todas as imagens'")
        print("  nem 'seguir a referencia para tudo'.")
        return 1

    print(f"[OK] prompts sem pedido de repeticao ({len(arquivos)} projeto(s) conferido(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
