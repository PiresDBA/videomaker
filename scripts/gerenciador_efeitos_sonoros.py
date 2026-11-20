"""
================================================================================
MANUAL DE USO - GERENCIADOR HÍBRIDO DE EFEITOS SONOROS (EARSHOT + FREESOUND)
================================================================================
Objetivo:
    Fornecer uma interface única para obter efeitos sonoros em um pipeline de
    vídeo Python. Combina geração procedural instantânea via CPU (Earshot) com
    busca em banco massivo de áudios reais (Freesound API v2, licença CC0).

Pré-requisitos:
    1. pip install earshot requests
    2. Definir a variável de ambiente FREESOUND_API_KEY (chave gratuita em
       https://freesound.org)

Exemplo de uso no terminal ou importado em outro script:
    from gerenciador_efeitos_sonoros import obter_efeito_sonoro

    # 1. Som de ritmo/transição gerado localmente pelo Earshot
    som_corte = obter_efeito_sonoro("whoosh_fast/crisp", origem="earshot", duracao=0.6)

    # 2. Som realista de cena buscado e cacheado do Freesound
    som_cena = obter_efeito_sonoro("steam train whistle", origem="freesound", max_duracao=5.0)
================================================================================
"""
import os
import re
import subprocess
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
from typing import Literal
import requests

PASTA_CACHE = Path(__file__).resolve().parent / "cache_sfx"
PASTA_CACHE.mkdir(parents=True, exist_ok=True)


def _limpar_nome_arquivo(texto: str) -> str:
    """Remove caracteres especiais para criar nomes de arquivo seguros."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", texto.strip().lower())


def gerar_som_earshot(
    efeito_id: str,
    duracao: float | None = None,
    pitch: str | None = None,
) -> Path:
    """Renderiza um efeito Earshot (ID completo familia/variante) em WAV.

    Regra 2026-11-20: usar SEMPRE ID completo do `earshot sfx list`
    (ex: whoosh_fast/crisp, swipe/paper, swish/bright). So passar --pitch/--dur
    se a coluna knobs do list mostrar esse ajuste.

    Fallback: quando nao ha CLI `earshot` instalada (caso deste PC), renderiza
    via `earshot.forge.bank` — mesmo banco de 252 sons, sem caminho ficticio.
    """
    import shutil as _shutil
    sufixo = f"_{duracao}s" if duracao else ""
    sufixo += f"_{pitch}" if pitch else ""
    nome_arquivo = f"earshot_{_limpar_nome_arquivo(efeito_id)}{sufixo}.wav"
    caminho_saida = PASTA_CACHE / nome_arquivo
    if caminho_saida.exists() and caminho_saida.stat().st_size > 0:
        return caminho_saida

    cli = _shutil.which("earshot")
    if cli:
        comando = [cli, "sfx", "render", efeito_id, "-o", str(caminho_saida)]
        if duracao is not None:
            comando.extend(["--dur", str(duracao)])
        if pitch is not None:
            comando.extend(["--pitch", pitch])
        env = os.environ.copy()
        for k in ("PYTHONHOME", "PYTHONPATH", "PYTHONEXECUTABLE"):
            env.pop(k, None)
        r = subprocess.run(comando, capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise RuntimeError(f"Earshot CLI falhou para '{efeito_id}': {r.stderr or r.stdout}")
        return caminho_saida

    # Fallback local: earshot.forge.bank (252 sons), sem depender da CLI.
    import sys as _sys
    import numpy as _np
    import soundfile as _sf
    _sfx = r"C:\videomaker\earshot-sfx"
    if _sfx not in _sys.path:
        _sys.path.insert(0, _sfx)
    # Conflito: earshot pip (VAD) e earshot-sfx (banco) têm o mesmo nome.
    _sys.modules.pop("earshot", None)
    _sys.modules.pop("earshot.forge", None)
    from earshot.forge import bank as _bank
    y, meta = _bank.render(efeito_id)
    if getattr(y, "ndim", 1) == 2:
        y = y.mean(axis=1)
    sr = int(meta.get("sr", 44100))
    if duracao is not None and duracao > 0:
        n = int(duracao * sr)
        if len(y) < n:
            y = _np.pad(y, (0, n - len(y)))
        else:
            y = y[:n]
    if pitch:
        print(f"AVISO: --pitch '{pitch}' ignorado no fallback (so usar se knobs)", flush=True)
    _sf.write(caminho_saida, _np.asarray(y, dtype="float32"), sr)
    return caminho_saida


def buscar_som_local(nome_arquivo: str) -> Path:
    """SFX domestico real (nunca caminho ficticio): so aceita arquivo existente."""
    candidatos = [
        Path("assets/audio/sons") / nome_arquivo,
        Path(__file__).resolve().parent.parent / "assets" / "audio" / "sons" / nome_arquivo,
    ]
    from pathlib import Path as _P
    for projeto in (_P(r"C:\videomaker\projects")).glob("*"):
        candidatos.append(projeto / "assets" / "audio" / "sons" / nome_arquivo)
    for c in candidatos:
        if c.is_file() and c.stat().st_size > 0:
            return c
    raise FileNotFoundError(f"Som local nao encontrado (caminho ficticio proibido): {nome_arquivo}")


def buscar_som_freesound(
    consulta: str,
    max_duracao: float = 8.0,
    api_key: str | None = None,
) -> Path:
    """
    Busca um efeito sonoro com licença Creative Commons 0 (domínio público)
    na API do Freesound e salva o preview MP3 em alta qualidade no cache local.
    """
    chave = api_key or os.getenv("FREESOUND_API_KEY")
    if not chave:
        raise ValueError(
            "FREESOUND_API_KEY não encontrada. Configure no ambiente ou passe via parâmetro."
        )

    nome_arquivo = f"freesound_{_limpar_nome_arquivo(consulta)}_max{int(max_duracao)}s.mp3"
    caminho_saida = PASTA_CACHE / nome_arquivo

    if caminho_saida.exists() and caminho_saida.stat().st_size > 0:
        return caminho_saida

    url_busca = "https://freesound.org/apiv2/search/text/"
    filtros = f'license:"Creative Commons 0" duration:[0.1 TO {max_duracao}]'
    parametros = {
        "query": consulta,
        "filter": filtros,
        "sort": "rating_desc",
        "fields": "id,name,previews,duration",
        "page_size": 3,
        "token": chave,
    }

    resposta = requests.get(url_busca, params=parametros, timeout=15)
    resposta.raise_for_status()
    dados = resposta.json()

    resultados = dados.get("results", [])
    if not resultados:
        raise FileNotFoundError(f"Nenhum som CC0 encontrado no Freesound para: '{consulta}'")

    melhor_som = resultados[0]
    url_mp3 = melhor_som["previews"]["preview-hq-mp3"]

    download = requests.get(url_mp3, timeout=20)
    download.raise_for_status()
    caminho_saida.write_bytes(download.content)

    return caminho_saida


def obter_efeito_sonoro(
    identificador_ou_busca: str,
    origem: Literal["earshot", "freesound", "local"] = "earshot",
    duracao: float | None = None,
    pitch: str | None = None,
    max_duracao: float = 8.0,
) -> Path:
    """
    Ponto de entrada único para o pipeline de vídeo obter qualquer SFX.
    """
    if origem == "earshot":
        return gerar_som_earshot(identificador_ou_busca, duracao=duracao, pitch=pitch)
    if origem == "local":
        return buscar_som_local(identificador_ou_busca)
    return buscar_som_freesound(identificador_ou_busca, max_duracao=max_duracao)


if __name__ == "__main__":
    print("Testando geração Earshot...")
    wav = obter_efeito_sonoro("whoosh_fast/crisp", origem="earshot", duracao=0.7)
    print(f"Arquivo gerado: {wav}")

    if os.getenv("FREESOUND_API_KEY"):
        print("Testando busca Freesound...")
        mp3 = obter_efeito_sonoro("camera shutter", origem="freesound", max_duracao=3.0)
        print(f"Arquivo baixado: {mp3}")
