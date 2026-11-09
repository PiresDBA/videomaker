# -*- coding: utf-8 -*-
"""Leitura de chaves de API do .env com deteccao de encoding.

O .env do Videomaker pode estar salvo em UTF-8 ou UTF-16 (Windows PowerShell
5.1 grava UTF-16 por padrao com ``Out-File``/``Set-Content``). Ler UTF-16 como
UTF-8 deixa os nomes das chaves com ``\\x00`` entre os caracteres e a chave
nunca e encontrada. Este modulo decodifica pelo BOM.

Uso:
    from env_keys import load_env_key
    key = load_env_key("GOOGLE_TTS_API_KEY")
"""
import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _decode(raw):
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", "ignore")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw[3:].decode("utf-8", "ignore")
    return raw.decode("utf-8", "ignore")


def load_env_key(name, env_file=None):
    """Devolve o valor de ``name`` no ambiente ou no .env (UTF-8 ou UTF-16)."""
    if os.environ.get(name):
        return os.environ[name]
    path = Path(env_file) if env_file else ENV_FILE
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if not raw:
        return None
    for line in _decode(raw).splitlines():
        line = line.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == name:
            return v.strip().strip('"').strip("'")
    return None
