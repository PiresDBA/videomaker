# -*- coding: utf-8 -*-
"""hook_manager.py - O HOOK do Videomaker.

Um HOOK e um mecanismo que permite 'enganchar' codigo personalizado dentro do
fluxo de execucao existente, SEM alterar o codigo-fonte original. Aqui ele
intercepta eventos criticos do pipeline (antes de renderizar, antes de
publicar, antes de aplicar sincronia) e dispara a validacao do CONTRATO
automaticamente, bloqueando a acao se alguma regra estiver quebrada.

Uso no pipeline:
    from hook_manager import disparar
    if not disparar("antes_render", slug=p.slug):
        raise RuntimeError("HOOK bloqueou a acao")

Para adicionar um novo gatilho: basta @registrar("nome_do_evento") numa funcao.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
_REGISTRY: dict[str, list] = {}


def registrar(evento: str):
    """Decorador: registra uma funcao como hook do evento."""
    def deco(fn):
        _REGISTRY.setdefault(evento, []).append(fn)
        return fn
    return deco


def disparar(evento: str, **contexto) -> bool:
    """Dispara todos os hooks do evento. Retorna False se algum bloquear."""
    permitir = True
    for fn in _REGISTRY.get(evento, []):
        try:
            resultado = fn(**contexto)
        except Exception as e:
            print(f"HOOK {evento}: ERRO ao executar {fn.__name__}: {e}", flush=True)
            resultado = False
        if resultado is False:
            permitir = False
    return permitir


@registrar("antes_render")
@registrar("antes_publicar")
@registrar("antes_auditoria_aplicar")
def validar_contrato(slug: str = "", **_ctx) -> bool:
    """Gatilho principal: roda o validador do CONTRATO e bloqueia se falhar."""
    validador = HERE / "hook_validator.py"
    if not validador.exists():
        print("HOOK: validador ausente - bloqueando por seguranca", flush=True)
        return False
    args = [sys.executable, str(validador)]
    if slug:
        args += ["--slug", slug]
    r = subprocess.run(args, capture_output=True, text=True)
    print(r.stdout, flush=True)
    if r.returncode != 0:
        print("HOOK BLOQUEOU: corrija os erros acima antes de continuar.", flush=True)
        return False
    return True
